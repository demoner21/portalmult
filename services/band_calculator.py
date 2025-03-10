import numpy as np
import logging
from typing import List
from utils.raster_utils import read_and_normalize, calculate_and_save

logger = logging.getLogger(__name__)

class BandCalculator:
    """
    Classe responsável por calcular índices a partir das bandas baixadas.
    """

    def __init__(self, band_files: List[str]):
        self.band_files = band_files
        logger.info(f"Band files to process: {self.band_files}")

    def calculate_indices(self) -> List[str]:
        """
        Calcula os índices NDVI, NDWI, BSI e SAVI a partir das bandas baixadas.
    
        Returns:
            List[str]: Lista com os nomes dos arquivos gerados (bandas + índices).
        """
        try:
            # Verificar se há bandas para processar
            if not self.band_files:
                logger.error("Nenhuma banda foi baixada ou fornecida.")
                raise ValueError("Nenhuma banda foi baixada ou fornecida.")
    
            # Ler e normalizar as bandas
            arr_st = np.stack([read_and_normalize(file) for file in self.band_files]).astype(np.float32)
    
            # Calcular índices
            indices = {
                'NDVI': (arr_st[8] - arr_st[4]) / (arr_st[8] + arr_st[4]),
                'NDWI': (arr_st[3] - arr_st[8]) / (arr_st[3] + arr_st[8]),
                'BSI': ((arr_st[11] + arr_st[4]) - (arr_st[8] + arr_st[3])) / ((arr_st[11] + arr_st[4]) + (arr_st[8] + arr_st[3])),
                'SAVI': (arr_st[8] - arr_st[4]) / (arr_st[8] + arr_st[4]) * (1 + 0.5)
            }
    
            # Salvar os índices em arquivos
            index_files = []
            for name, index in indices.items():
                output_path = f'{name}.tif'
                calculate_and_save(index, output_path, self.band_files[0])
                index_files.append(output_path)
    
            return self.band_files + index_files
    
        except Exception as e:
            logger.error(f"Erro ao calcular índices: {e}", exc_info=True)
            raise