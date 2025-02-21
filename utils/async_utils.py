from fastapi import UploadFile, HTTPException
from typing import List
import io
from spin.inference import extract_layer, expected_layers
import aiohttp
import aiofiles
import asyncio
import ee
import logging

logger = logging.getLogger(__name__)

async def download_band(image, band, region, nome_arquivo, scale=10, crs='EPSG:4326'):
    """
    Faz o download de uma banda de uma imagem do Earth Engine.

    Args:
        image: Imagem do Earth Engine.
        band: Banda a ser baixada.
        region: Região de interesse.
        nome_arquivo: Nome base do arquivo.
        scale: Escala do download.
        crs: Sistema de coordenadas de referência.

    Returns:
        str: Nome do arquivo baixado.
    """
    try:
        single_band_image = image.select(band)
        filename = f"Sentinel_{band}.tif"
        logger.info(f"Preparando download para banda {band}")

        download_id = ee.data.getDownloadId({
            'image': single_band_image,
            'scale': scale,
            'region': region,
            'format': 'GEO_TIFF',
            'crs': crs
        })

        url = ee.data.makeDownloadUrl(download_id)
        logger.info(f"URL de download gerada para banda {band}")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(filename, 'wb') as f:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            await f.write(chunk)
                    logger.info(f"Banda {band} baixada com sucesso: {filename}")
                else:
                    logger.error(f"Falha ao baixar a banda {band}. Status: {response.status}")

    except Exception as e:
        logger.error(f"Erro ao baixar a banda {band}: {e}", exc_info=True)

async def download_slope(image, region, nome_arquivo, scale=10, crs='EPSG:4326'):
    """
    Faz o download da imagem de inclinação (slope) do Earth Engine.
    """
    try:
        filename = f"slope_{nome_arquivo}.tif"
        logger.info(f"Preparando download da imagem de inclinação (slope)")

        download_id = ee.data.getDownloadId({
            'image': image,
            'scale': scale,
            'region': region,
            'format': 'GEO_TIFF',
            'crs': crs
        })

        url = ee.data.makeDownloadUrl(download_id)
        logger.info(f"URL de download gerada para slope")

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(filename, 'wb') as f:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            await f.write(chunk)
                    logger.info(f"Slope baixado com sucesso: {filename}")
                    return filename
                else:
                    logger.error(f"Falha ao baixar a imagem de slope. Status: {response.status}")
                    return None

    except Exception as e:
        logger.error(f"Erro ao baixar a imagem de slope: {e}", exc_info=True)
        return None

async def process_request_files(files: List[UploadFile]):
    """
    Processa os arquivos enviados na requisição.

    Args:
        files: Lista de arquivos do tipo UploadFile.

    Returns:
        Lista de dicionários contendo os dados dos arquivos e suas camadas.
    """
    if len(files) == 1 and files[0].size == 0:
        raise HTTPException(
            status_code=400, detail="Parece que você esqueceu de escolher os dados"
        )

    sorted_files = sorted(files, key=lambda f: extract_layer(f.filename))
    out = []
    for file in sorted_files:
        raw_data = await file.read()
        out.append(
            {"data": io.BytesIO(raw_data), "layer": extract_layer(file.filename)}
        )
    return out
