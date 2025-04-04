import asyncio
import logging
from typing import List, Dict
from asyncio.streams import logger
from utils.async_utils import download_band

logger = logging.getLogger(__name__)

class BandDownloader:
    """"
    Class resposavel por baixar as bandas de uma imagem do Earth Engine.
    """

    def __init__(self, image, region, nome_arquivo):
        self.image = image
        self.region = region
        self.nome_arquivo = nome_arquivo

    @staticmethod
    async def download_band_wrapper(image, band, region, nome_arquivo):
        return await download_band(image, band, region, nome_arquivo)

    async def download_all_bands(self, bandas: Dict[str, float]) -> List[str]:
        """
        Faz o download de todas as bandas especificadas.

        Args:
            bandas: Dicionário com as bandas a serem baixadas (ex: {'B1': 0.443, 'B2': 0.490}).

        Returns:
            List[str]: Lista com os nomes dos arquivos baixados.
        """
        tasks = [
            BandDownloader.download_band_wrapper(self.image, band, self.region, self.nome_arquivo)
            for band in bandas.keys()
        ]
        downloaded_files = await asyncio.gather(*tasks)
        return [file for file in downloaded_files if file is not None]
