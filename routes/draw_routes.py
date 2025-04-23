# routes/draw_routes.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import ee
import logging
from services.earth_engine_processor import EarthEngineProcessor
from utils.zip_creator import ZipCreator
from utils.data_range import validate_date_range

router = APIRouter(prefix="/draw", tags=["Draw"])
logger = logging.getLogger(__name__)

class PolygonRequest(BaseModel):
    coordinates: List[List[List[float]]]
    start_date: str
    end_date: str
    cloud_filter: float

@router.post("/process_polygon")
async def process_polygon(request: PolygonRequest):
    """
    Processa uma área desenhada no mapa como um polígono.
    
    Args:
        coordinates: Lista de coordenadas do polígono no formato [[[lon, lat], [lon, lat], ...]]
        start_date: Data de início no formato YYYY-MM-DD
        end_date: Data de término no formato YYYY-MM-DD
        cloud_filter: Percentual máximo de nuvens (0-100)
    """
    try:
        # Validar intervalo de datas
        validate_date_range(request.start_date, request.end_date)
        
        # Validar filtro de nuvens
        if not 0 <= request.cloud_filter <= 100:
            raise HTTPException(
                status_code=400,
                detail="O percentual de nuvens deve estar entre 0 e 100"
            )
        
        # Criar geometria do Earth Engine
        ee_geometry = ee.Geometry.Polygon(request.coordinates)
        
        # Processar os dados
        processor = EarthEngineProcessor()
        result, _ = await processor.process_data(
            parameters={
                "latitude": 0,
                "longitude": 0,
                "data": [request.start_date, request.end_date],
                "filter": f"CLOUDY_PIXEL_PERCENTAGE,{request.cloud_filter}"
            },
            geometry=ee_geometry
        )
        
        if not result:
            return JSONResponse(
                status_code=404,
                content={"detail": "Nenhuma imagem encontrada para os parâmetros fornecidos"}
            )
        
        # Criar arquivo ZIP
        zip_creator = ZipCreator()
        zip_buffer = await zip_creator.create_zip_file(result)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                'Content-Disposition': 'attachment; filename="polygon_images.zip"'
            }
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro ao processar polígono: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar polígono: {str(e)}"
        )