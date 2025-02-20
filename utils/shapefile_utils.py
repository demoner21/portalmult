import geopandas as gpd
import ee
from fastapi import HTTPException
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def extrair_geometria_shp(caminho_arquivo: str) -> Optional[ee.Geometry]:
    """
    Extrai a geometria de um arquivo shapefile e a converte para o formato do Earth Engine.
    
    Parâmetros:
    caminho_arquivo (str): Caminho para o arquivo .shp
    
    Retorna:
    ee.Geometry: Geometria no formato do Earth Engine
    """
    try:
        # Lê o arquivo shapefile
        gdf = gpd.read_file(caminho_arquivo)
        
        # Verifica se o GeoDataFrame não está vazio
        if gdf.empty:
            logger.error("Arquivo shapefile está vazio.")
            return None
            
        # Converte para WGS84 (EPSG:4326)
        gdf_wgs84 = gdf.to_crs('EPSG:4326')
        
        # Converte para GeoJSON
        geojson = gdf_wgs84.__geo_interface__
        
        # Converte diretamente para ee.Geometry
        geometria_ee = ee.Geometry(geojson['features'][0]['geometry'])
        
        return geometria_ee
        
    except Exception as e:
        logger.error(f"Erro ao processar o shapefile: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erro ao processar o shapefile: {str(e)}")