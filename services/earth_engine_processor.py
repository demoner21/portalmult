import ee
import logging
import asyncio
import natsort
import glob
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Tuple, Any, Optional
from utils.validators import bandas
from utils.async_utils import download_band, download_slope
from services.earth_engine_initializer import initialize_earth_engine
from utils.raster_utils import read_and_normalize, calculate_and_save
from services.band_downloader import BandDownloader
from services.band_calculator import BandCalculator

logger = logging.getLogger(__name__)

initialize_earth_engine()

class EarthEngineProcessor:
    async def process_data(
        self,
        parameters: Dict,
        geometry: Optional[ee.Geometry] = None
    ) -> Tuple[List[str], Any]:
        """
        Processa dados do Earth Engine com base nos parâmetros fornecidos.
        """
        # Gerar nome do arquivo
        nome_arquivo = f"sentinel_{parameters['latitude']}_{parameters['longitude']}_{parameters['data'][0]}_{parameters['data'][1]}"

        # Criar região (bbox ou usar geometria personalizada)
        if geometry is None:
            bbox = self.create_bbox(float(parameters['latitude']), float(parameters['longitude']))
            region = ee.Geometry.Rectangle([
                bbox["longitude_min"],
                bbox["latitude_min"],
                bbox["longitude_max"],
                bbox["latitude_max"]
            ])
        else:
            region = geometry

        # Filtrar imagens
        image_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        filtered_collection = (image_collection
                               .filterBounds(region)
                               .filterDate(parameters['data'][0], parameters['data'][1])
                               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', float(parameters['filter'].split(',')[1]))))

        count = filtered_collection.size().getInfo()
        if count == 0:
            logger.warning("Nenhuma imagem encontrada para os parâmetros fornecidos.")
            return [], {
                "status": 404,
                "mensagem": "Nenhuma imagem encontrada para os parâmetros fornecidos.",
                "detalhes": parameters
            }

        # Selecionar a primeira imagem
        image = filtered_collection.sort('system:time_start', False).first()

        # Baixar bandas usando o BandDownloader
        band_downloader = BandDownloader(image, region, nome_arquivo)
        band_files = await band_downloader.download_all_bands(bandas)

        # Calcular índices usando o BandCalculator
        band_calculator = BandCalculator(band_files)
        all_files = band_calculator.calculate_indices()

        return all_files, None

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
