import ee
import io
import logging
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Tuple, Any, Optional, List
from dotenv import load_dotenv
from utils.validators import bandas
from utils.async_utils import download_band, download_slope
from services.earth_engine_initializer import initialize_earth_engine
from utils.raster_utils import read_and_normalize, calculate_and_save
from services.band_downloader import BandDownloader
from services.band_calculator import BandCalculator
from services.tiff_processor import TiffProcessor
from utils.data_range import validate_date_range
from services.model_loader import create_model_binary, create_model_classification, run_prediction
from spin.inference import extract_layer

logger = logging.getLogger(__name__)

load_dotenv()

initialize_earth_engine()

class EarthEngineProcessor:
    def __init__(self):
        self.tiff_processor = TiffProcessor()
        self.request_cache = {}

    async def process_data(
        self,
        parameters: Dict,
        geometry: Optional[ee.Geometry] = None
    ) -> Tuple[List[str], Any]:
        """
        Processa dados do Earth Engine com cache e armazenamento de geometria
        
        Args:
            parameters: Dicionário com parâmetros da requisição
            geometry: Geometria opcional do Earth Engine
            
        Returns:
            Tuple (lista de arquivos resultantes, resultado da predição)
        """
        # Gera chave única para o cache
        cache_key = f"{parameters['latitude']}_{parameters['longitude']}_{parameters['data'][0]}_{parameters['data'][1]}"
        
        if cache_key in self.request_cache:
            logger.info(f"Retornando dados do cache para chave: {cache_key}")
            return self.request_cache[cache_key]['result_path'], self.request_cache[cache_key]['prediction_result']

        # Validação de parâmetros
        self._validate_parameters(parameters)
        
        # Gera nome do arquivo base
        nome_arquivo = self._generate_filename(parameters)
        
        # Cria região de interesse
        region = await self._create_region(parameters, geometry)
        
        # Filtra coleção de imagens
        filtered_collection = await self._filter_image_collection(parameters, region)
        
        # Processa a imagem
        result_files, prediction_result = await self._process_image(
            filtered_collection, region, nome_arquivo, parameters
        )
        
        # Armazena no cache e no banco de dados
        if result_files and isinstance(prediction_result, dict) and 'predicted_class' in prediction_result:
            self.request_cache[cache_key] = {
                'result_path': result_files,
                'prediction_result': prediction_result
            }

        return result_files, prediction_result

    async def _process_prediction(self, band_files: List[str]) -> Dict:
        """
        Process the prediction using the downloaded band files.
        
        Args:
            band_files: List of paths to the downloaded band files
            
        Returns:
            Dictionary with prediction results
        """
        try:
            # Load the binary model first
            binary_model = create_model_binary()
            if not binary_model:
                raise ValueError("Failed to load binary model")
            
            # Process the files for prediction
            data = []
            for file in band_files:
                with open(file, 'rb') as f:
                    data.append({
                        "data": io.BytesIO(f.read()),
                        "layer": extract_layer(file)
                    })
            
            raster_data = [d["data"] for d in data]
            
            # Run binary prediction
            binary_result = run_prediction("binary", raster_data)
            
            # If erosion is detected, run classification
            if binary_result["predicted_class"] == "presente":
                classification_model = create_model_classification()
                if not classification_model:
                    raise ValueError("Failed to load classification model")
                
                classification_result = run_prediction("classification", raster_data)
                classification_result["probabilities"].update(binary_result["probabilities"])
                return classification_result
            
            return binary_result
            
        except Exception as e:
            logger.error(f"Error in prediction processing: {str(e)}", exc_info=True)
            return {
                "status": 500,
                "mensagem": "Erro durante o processamento da predição",
                "error": str(e)
            }

    def _validate_parameters(self, parameters: Dict):
        """Valida os parâmetros da requisição"""
        validate_date_range(parameters['data'][0], parameters['data'][1])
        
        if not -90 <= parameters['latitude'] <= 90:
            raise ValueError("Latitude deve estar entre -90 e 90")
            
        if not -180 <= parameters['longitude'] <= 180:
            raise ValueError("Longitude deve estar entre -180 e 180")

    def _generate_filename(self, parameters: Dict) -> str:
        """Gera um nome de arquivo baseado nos parâmetros"""
        return (
            f"sentinel_{parameters['latitude']}_{parameters['longitude']}_"
            f"{parameters['data'][0]}_{parameters['data'][1]}"
        )

    async def _create_region(self, parameters: Dict, geometry: Optional[ee.Geometry]) -> ee.Geometry:
        """Cria a região de interesse"""
        if geometry is None:
            bbox = self._create_bbox(
                float(parameters['latitude']),
                float(parameters['longitude'])
            )
            return ee.Geometry.Rectangle([
                bbox["longitude_min"],
                bbox["latitude_min"],
                bbox["longitude_max"],
                bbox["latitude_max"]
            ])
        return geometry

    def _create_bbox(self, latitude: float, longitude: float, 
                    delta_width: float = 0.011, delta_height: float = 0.011) -> Dict:
        """Cria um bounding box ao redor do ponto central"""
        return {
            "longitude_min": longitude - delta_width / 2,
            "latitude_min": latitude - delta_height / 2,
            "longitude_max": longitude + delta_width / 2,
            "latitude_max": latitude + delta_height / 2
        }

    async def _filter_image_collection(self, parameters: Dict, region: ee.Geometry) -> ee.Image:
        """Filtra a coleção de imagens do Sentinel-2"""
        image_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        
        # Extrai o valor do filtro de nuvens
        cloud_filter = float(parameters['filter'].split(',')[1]) if parameters.get('filter') else 100
        
        filtered_collection = (
            image_collection
            .filterBounds(region)
            .filterDate(parameters['data'][0], parameters['data'][1])
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_filter))
        )  # Added closing parenthesis here
    
        count = filtered_collection.size().getInfo()
        if count == 0:
            logger.warning("Nenhuma imagem encontrada para os parâmetros fornecidos.")
            return None
    
        return filtered_collection.sort('system:time_start', False).first()


    async def _process_image(
        self,
        image: ee.Image,
        region: ee.Geometry,
        nome_arquivo: str,
        parameters: Dict
    ) -> Tuple[List[str], Any]:
        """Processa a imagem e gera os resultados"""
        if image is None:
            return [], {
                "status": 404,
                "mensagem": "Nenhuma imagem encontrada para os parâmetros fornecidos.",
                "detalhes": parameters
            }

        # Baixa as bandas
        band_downloader = BandDownloader(image, region, nome_arquivo)
        band_files = await band_downloader.download_all_bands(bandas)

        if not band_files:
            return [], {
                "status": 500,
                "mensagem": "Falha ao baixar as bandas.",
                "detalhes": parameters
            }

        # Calcula índices
        band_calculator = BandCalculator(band_files)
        all_files = band_calculator.calculate_indices()

        # Processa a predição
        prediction_result = await self._process_prediction(all_files)

        return all_files, prediction_result

    def calculate_erosion_risk(bare_soil_data, slope_data):
        """
        Calcula o risco de erosão com base nos dados de solo exposto e inclinação.

        Args:
            bare_soil_data: Dados de solo exposto (array numpy).
            slope_data: Dados de inclinação (array numpy).

        Returns:
            relative_erosion_risk: Array numpy com o risco de erosão.
        """
        # Evitar divisão por zero
        total_clear = bare_soil_data[:, :, 1] + bare_soil_data[:, :, 0]
        total_clear[total_clear == 0] = 1e-10  # Substituir zeros por um valor pequeno
        bare_ratio = bare_soil_data[:, :, 0] / total_clear

        # Pesos para o cálculo do risco
        WEIGHT_BARE_SOIL = 1
        WEIGHT_SLOPE = 1

        # Cálculo do risco de erosão
        relative_erosion_risk = (slope_data / 90) * WEIGHT_SLOPE * bare_ratio * WEIGHT_BARE_SOIL

        return relative_erosion_risk
    
    async def _process_slope(self, image, region, nome_arquivo):
        """
        Processa e baixa dados de inclinação (slope) a partir de um modelo digital de elevação (DEM).
        """
        try:
            # Carregar o Modelo Digital de Elevação (DEM)
            dem = ee.Image("USGS/SRTMGL1_003")

            # Calcular a inclinação
            slope = ee.Terrain.slope(dem).clip(region)

            # Baixar a imagem de slope
            slope_file = await download_slope(slope, region, nome_arquivo)

            return slope_file

        except Exception as e:
            logger.error(f"Erro ao processar slope: {e}")
            return None

    @staticmethod
    def create_bbox(latitude: float, longitude: float, delta_width: float = 0.011, delta_height: float = 0.011) -> Dict:
        return {
            "longitude_min": longitude - delta_width / 2,
            "latitude_min": latitude - delta_height / 2,
            "longitude_max": longitude + delta_width / 2,
            "latitude_max": latitude + delta_height / 2
        }