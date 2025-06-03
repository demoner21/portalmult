from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse

import ee
import json
import logging
from database.roi_queries import obter_roi_por_id
from services.earth_engine_processor import EarthEngineProcessor
from utils.jwt_utils import get_current_user
from utils.zip_creator import ZipCreator
from utils.data_range import validate_date_range
from services.shapefile_processor import ShapefileProcessor

router = APIRouter()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sentinel", tags=["Sentinel"])


@router.get("/{roi_id}/download-sentinel")
async def download_sentinel_images(
    roi_id: int,
    start_date: str = Query(..., description="Data de início no formato YYYY-MM-DD"),
    end_date: str = Query(..., description="Data de término no formato YYYY-MM-DD"),
    cloud_pixel_percentage: float = Query(..., description="Percentual máximo de nuvens permitido (0 a 100)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint para download de imagens do Sentinel-2 com base no roi_id,
    levando em consideração o tamanho do shapefile.
    """
    try:
        # Busca a ROI no banco de dados
        roi = await obter_roi_por_id(roi_id, current_user['id'])
        if not roi:
            raise HTTPException(status_code=404, detail="ROI não encontrada")

        # Validação de datas e parâmetros
        validate_date_range(start_date, end_date)
        if not 0 <= cloud_pixel_percentage <= 100:
            raise HTTPException(status_code=400, detail="Percentual de nuvens inválido")

        metadata = roi.get("metadata", {})
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        area_ha = metadata.get("area_ha", None)
        if area_ha is None:
            raise HTTPException(status_code=400, detail="Metadados de área não disponíveis na ROI")

        # Limite de área (ajuste conforme necessário)
        MAX_AREA_HA = 10000
        if area_ha > MAX_AREA_HA:
            raise HTTPException(
                status_code=400,
                detail=f"A área da ROI é muito grande ({area_ha:.2f} ha). Limite permitido: {MAX_AREA_HA} ha"
            )

        # Convert geometry to proper format for Earth Engine
        try:
            # First try to parse as WKT if needed
            if roi['geometria'].startswith("POLYGON") or roi['geometria'].startswith("MULTIPOLYGON"):
                from shapely.wkt import loads as wkt_loads
                shapely_geom = wkt_loads(roi['geometria'])
                geometry = ee.Geometry(shapely_geom.__geo_interface__)
            else:
                # Try to load as GeoJSON
                if isinstance(roi['geometria'], str):
                    geojson = json.loads(roi['geometria'])
                else:
                    geojson = roi['geometria']
                geometry = ee.Geometry(geojson)
        except Exception as geom_error:
            logger.error(f"Erro na conversão da geometria: {str(geom_error)}")
            raise HTTPException(
                status_code=400,
                detail=f"Geometria da ROI em formato inválido: {str(geom_error)}"
            )

        # Processa as imagens usando o EarthEngineProcessor
        processor = EarthEngineProcessor()
        parameters = {
            "data": [start_date, end_date],
            "filter": f"CLOUDY_PIXEL_PERCENTAGE,{cloud_pixel_percentage}",
            "latitude": 0,
            "longitude": 0
        }
        result_files, _ = await processor.process_data(parameters, geometry)

        if not result_files:
            raise HTTPException(status_code=404, detail="Nenhuma imagem encontrada")

        # Cria o arquivo ZIP
        zip_creator = ZipCreator()
        zip_buffer = await zip_creator.create_zip_file(result_files)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                'Content-Disposition': f'attachment; filename="sentinel_roi_{roi_id}.zip"'
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro no download das imagens: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar o download das imagens: {str(e)}"
        )
