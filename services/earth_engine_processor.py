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

logger = logging.getLogger(__name__)

initialize_earth_engine()


class EarthEngineProcessor:
    async def process_data(
        self,
        parameters: Dict,
        geometry: Optional[ee.Geometry] = None
    ) -> Tuple[list[str], Any]:
        """
        Processa dados do Earth Engine com base nos parâmetros fornecidos.
        Aceita uma geometria personalizada ou cria uma região retangular com base em latitude e longitude.
        """
        # Gerar nome do arquivo
        nome_arquivo = f"sentinel_{parameters['latitude']}_{parameters['longitude']}_{parameters['data'][0]}_{parameters['data'][1]}"

        # Validar parâmetros
        if not isinstance(parameters.get('data'), (tuple, list)):
            logger.error("Parâmetro 'data' não está no formato correto.")
            return [], {"status": "erro", "mensagem": "Formato inválido para o parâmetro 'data'."}

        logger.info(f"Iniciando processamento com parâmetros: {parameters}")
        logger.info(f"Nome do arquivo: {nome_arquivo}")

        # Validar filtro de nuvens
        if isinstance(parameters.get('filter'), list):
            parameters['filter'] = parameters['filter'][0]
        elif not isinstance(parameters.get('filter'), str):
            logger.error("Formato inválido para o parâmetro 'filter'.")
            return [], {"status": "erro", "mensagem": "Formato inválido para o parâmetro 'filter'."}

        # Verificar parâmetros obrigatórios
        for key in ['latitude', 'longitude', 'data']:
            if key not in parameters:
                logger.error(f"Parâmetro ausente: {key}")
                return [], {"status": "erro", "mensagem": f"Parâmetro ausente: {key}"}

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

        logger.info(f"Região definida: {region.getInfo()}")

        # Validar datas
        try:
            data_inicio, data_fim = [datetime.strptime(d, '%Y-%m-%d') for d in parameters['data']]
        except ValueError:
            logger.error("Erro ao converter as datas.")
            return [], {
                "status": "erro", "mensagem": "Formato de data inválido. Utilize o formato 'YYYY-MM-DD'."
            }

        # Validar percentual de nuvens
        cloud_filter = 100
        if parameters.get('filter'):
            try:
                _, valor = parameters['filter'].split(',')
                cloud_filter = float(valor)
            except ValueError:
                logger.error("Erro ao processar o filtro de nuvens.")
                return [], {
                    "status": "erro", "mensagem": "Filtro de nuvens mal formatado. Exemplo: 'cloud_percentage,10'."
                }

        # Filtrar imagens
        image_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        filtered_collection = (image_collection
                               .filterBounds(region)
                               .filterDate(data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d'))
                               .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_filter)))

        count = filtered_collection.size().getInfo()
        logger.info(f"Número de imagens encontradas: {count}")

        if count == 0:
            logger.warning("Nenhuma imagem encontrada para os parâmetros fornecidos.")
            return [], {
                "status": 404,
                "mensagem": "Nenhuma imagem encontrada para os parâmetros fornecidos.",
                "detalhes": {
                    "latitude": parameters["latitude"],
                    "longitude": parameters["longitude"],
                    "data": parameters["data"],
                    "filtro_nuvens": cloud_filter
                }
            }

        # Selecionar a primeira imagem
        image = filtered_collection.sort('system:time_start', False).first()
        logger.info("Primeira imagem selecionada")

        # Baixar bandas e processar
        bands_files, _ = await self._process_bands(image, region, nome_arquivo)
        
        # Adicionar processamento do slope
        slope_file = await self._process_slope(image, region, nome_arquivo)
        
        # Combinar arquivos
        all_files = bands_files
        if slope_file:
            all_files.append(slope_file)

        return all_files, None

    async def _process_bands(self, image, region, nome_arquivo):
        download_tasks = []
        for band in bandas.keys():
            task = download_band(image, band, region, nome_arquivo)
            download_tasks.append(task)

        logger.info("Iniciando downloads das bandas")
        await asyncio.gather(*download_tasks)

        S_sentinel_bands = natsort.natsorted(glob.glob("./*B?*.tif"))

        with ThreadPoolExecutor() as executor:
            arr_st = np.stack(
                list(executor.map(read_and_normalize, S_sentinel_bands))).astype(np.float32)

        indices = {
            'NDVI': (arr_st[8] - arr_st[4]) / (arr_st[8] + arr_st[4]),
            'NDWI': (arr_st[3] - arr_st[8]) / (arr_st[3] + arr_st[8]),
            'BSI': ((arr_st[11] + arr_st[4]) - (arr_st[8] + arr_st[3])) / ((arr_st[11] + arr_st[4]) + (arr_st[8] + arr_st[3])),
            'SAVI': (arr_st[8] - arr_st[4]) / (arr_st[8] + arr_st[4]) * (1 + 0.5)
        }

        for name, index in indices.items():
            calculate_and_save(index, f'{name}.tif', S_sentinel_bands[0])

        all_files = S_sentinel_bands + \
            [f'{name}.tif' for name in indices.keys()]
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
