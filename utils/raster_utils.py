import rasterio as rio
import numpy as np
from io import BytesIO
import tempfile
import os
import logging

logger = logging.getLogger(__name__)

def read_and_normalize(band_file: str) -> np.ndarray:
    """
    Lê e normaliza uma banda de um arquivo raster.

    Args:
        band_file: Caminho do arquivo raster.

    Returns:
        np.ndarray: Banda normalizada.
    """
    with rio.open(band_file) as f:
        band = f.read(1)
        return (band - band.min()) / (band.max() - band.min())

def calculate_and_save(index: np.ndarray, output_path: str, base_file: str):
    """
    Calcula um índice e salva o resultado em um arquivo raster.

    Args:
        index: Índice calculado.
        output_path: Caminho de saída do arquivo.
        base_file: Arquivo base para o perfil de metadados.
    """
    with rio.open(base_file) as src:
        profile = src.profile
        profile.update(dtype=rio.float32, count=1)
        with rio.open(output_path, 'w', **profile) as dst:
            dst.write(index.astype(np.float32), 1)

def get_raster_center_coords(file_path: BytesIO) -> tuple[float, float]:
    """
    Extrai coordenadas centrais de um arquivo raster em memória.

    Args:
        file_path: Arquivo raster em memória.

    Returns:
        Tuple[float, float]: Coordenadas (longitude, latitude).
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tif') as temp_file:
            temp_file.write(file_path.getvalue())
            temp_file_path = temp_file.name

        with rio.open(temp_file_path) as dataset:
            bounds = dataset.bounds
            center_x = (bounds.left + bounds.right) / 2
            center_y = (bounds.bottom + bounds.top) / 2

            return (round(center_x, 6), round(center_y, 6))

    except Exception as e:
        logger.error(f"Erro ao processar arquivo raster: {e}")
        return (0, 0)
    
    finally:
        if 'temp_file_path' in locals():
            os.unlink(temp_file_path)