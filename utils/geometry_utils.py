from shapely import wkt
from shapely.geometry import shape
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

def validate_geometry_wkt(wkt_string: str) -> bool:
    """
    Valida se a string WKT representa uma geometria válida
    """
    try:
        geom = wkt.loads(wkt_string)
        if geom.is_empty:
            return False
        return True
    except Exception as e:
        logger.error(f"Erro ao validar geometria WKT: {str(e)}")
        return False

def geojson_to_wkt(geojson: dict) -> str:
    """
    Converte GeoJSON para WKT
    """
    try:
        geom = shape(geojson)
        return geom.wkt
    except Exception as e:
        logger.error(f"Erro ao converter GeoJSON para WKT: {str(e)}")
        raise HTTPException(status_code=400, detail="GeoJSON inválido")