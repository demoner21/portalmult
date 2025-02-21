import asyncio
import logging
from typing import List, Dict
from asyncio.streams import logger
from utils.async_utils import download_band

logger = logging.getLogger(__name__)

class BandDonwloader:
    """"
    Class resposavel por baixar as bandas de uma imagem do Earth Engine.
    """

    def __init__(self, image, region, nome_arquivo):
        self.image = image
        self.region = region
        self.nome_arquivo = nome_arquivo

    async def donwload_all_bands(self, bandas: Dict[str, float]) -> List[str]:
        """
        Faz o download de todas as bandas especificadas.

        Args:
            bandas: Dicionário com as bandas a serem baixadas (ex: {'B1': 0.443, 'B2': 0.490}).
        
        Returns:
            List[str]: Lista com os nomes dos arquivos baixados.
        """
        tasks = [donwload_band(self.image, band, self.region, self.nome_arquivo) for band in bandas.keys()]
        donwloaded_files = await asyncio.gather(*tasks)
        return [file for file in donwloaded if file is not None]
