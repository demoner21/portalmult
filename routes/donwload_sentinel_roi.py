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

        # Process metadata
        metadata = roi.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        
        area_ha = metadata.get("area_ha", None)
        # Add this to the download_sentinel_images function
        if area_ha is None:
            try:
                from utils.geometry_utils import calculate_area_ha
                area_ha = calculate_area_ha(roi['geometria'])
                logger.warning(f"Calculated area on-the-fly for ROI {roi_id}: {area_ha} ha")
            except Exception as e:
                logger.error(f"Failed to calculate area for ROI {roi_id}: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Não foi possível calcular a área da ROI. Erro: {str(e)}"
                    )
            
        """area_ha = metadata.get("area_ha", None)
        if area_ha is None:
            raise HTTPException(
                status_code=400,
                detail="Metadados de área não disponíveis na ROI. Recrie a ROI com shapefile válido."
            )"
        """

        # Limite de área (ajuste conforme necessário)
        MAX_AREA_HA = 10000
        if area_ha > MAX_AREA_HA:
            raise HTTPException(
                status_code=400,
                detail=f"A área da ROI é muito grande ({area_ha:.2f} ha). Limite permitido: {MAX_AREA_HA} ha"
            )

        # Convert geometry to proper format for Earth Engine
        try:
            geometry = None
            geom_data = roi['geometria']
            
            logger.debug(f"Geometry type: {type(geom_data)}")
            logger.debug(f"Geometry content sample: {str(geom_data)[:200]}")

            # Case 1: Already a FeatureCollection (from shapefile upload)
            if isinstance(geom_data, dict) and geom_data.get('type') == 'FeatureCollection':
                features = geom_data.get('features', [])
                if features:
                    # Take first feature's geometry
                    first_geom = features[0].get('geometry')
                    if first_geom:
                        geometry = ee.Geometry(first_geom)
            
            # Case 2: WKT string
            elif isinstance(geom_data, str) and geom_data.upper().startswith(('POLYGON', 'MULTIPOLYGON')):
                from shapely.wkt import loads as wkt_loads
                shapely_geom = wkt_loads(geom_data)
                geometry = ee.Geometry(shapely_geom.__geo_interface__)
            
            # Case 3: GeoJSON string
            elif isinstance(geom_data, str):
                try:
                    geojson = json.loads(geom_data)
                    geometry = ee.Geometry(geojson)
                except json.JSONDecodeError:
                    pass
            
            # Case 4: Direct GeoJSON dict
            elif isinstance(geom_data, dict) and geom_data.get('type') in ['Polygon', 'MultiPolygon']:
                geometry = ee.Geometry(geom_data)
            
            if geometry is None:
                raise ValueError("Formato de geometria não suportado ou inválido")

        except Exception as geom_error:
            logger.error(f"Erro na conversão da geometria (ROI {roi_id}): {str(geom_error)}")
            raise HTTPException(
                status_code=400,
                detail=f"Geometria da ROI em formato inválido. Recrie a ROI com shapefile válido. Erro: {str(geom_error)}"
            )

        # Processa as imagens usando o EarthEngineProcessor
        processor = EarthEngineProcessor()
        parameters = {
            "data": [start_date, end_date],
            "filter": f"CLOUDY_PIXEL_PERCENTAGE,{cloud_pixel_percentage}",
            "geometry": geometry  # Pass the geometry directly
        }

        try:
            result_files, _ = await processor.process_data(parameters)
        except Exception as ee_error:
            logger.error(f"Erro no Earth Engine (ROI {roi_id}): {str(ee_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao processar imagens no Earth Engine: {str(ee_error)}"
            )

        if not result_files:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma imagem encontrada para os critérios especificados"
            )

        # Cria o arquivo ZIP
        zip_creator = ZipCreator()
        zip_buffer = await zip_creator.create_zip_file(result_files)

        # Log successful download
        logger.info(
            f"Download realizado com sucesso para ROI {roi_id}. "
            f"Período: {start_date} a {end_date}, "
            f"Nuvens: {cloud_pixel_percentage}%, "
            f"Área: {area_ha:.2f} ha"
        )

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                'Content-Disposition': f'attachment; filename="sentinel_roi_{roi_id}_{start_date}_{end_date}.zip"'
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro geral no download das imagens (ROI {roi_id}): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao processar o download: {str(e)}"
        )