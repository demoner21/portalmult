from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from typing import List
from datetime import datetime
from pathlib import Path
import json
import logging
from services.shapefile_processor import ShapefileProcessor
from services.earth_engine_processor import EarthEngineProcessor
from utils.jwt_utils import get_current_user
from database.roi_queries import criar_roi
from utils.zip_creator import ZipCreator
from models.roi_models import ROICreate  # Modelo Pydantic existente

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/download_image/")
async def download_image_from_shapefile(
    shapefile: UploadFile = File(..., description="Arquivo .shp"),
    shxfile: UploadFile = File(..., description="Arquivo .shx"),
    dbffile: UploadFile = File(..., description="Arquivo .dbf"),
    cpgfile: UploadFile = File(None, description="Arquivo .cpg (opcional)"),
    prjfile: UploadFile = File(None, description="Arquivo .prj (opcional)"),
    start_date: str = Query(..., description="Data de início no formato YYYY-MM-DD"),
    end_date: str = Query(..., description="Data de término no formato YYYY-MM-DD"),
    cloud_pixel_percentage: float = Query(..., description="Percentual máximo de nuvens permitido (0 a 100)"),
    current_user: dict = Depends(get_current_user)
):
    """Endpoint original completo, agora usando ShapefileProcessor."""
    try:
        # 1. Processa o shapefile (parte refatorada)
        geometry, metadados = await ShapefileProcessor.process_uploaded_files({
            "shp": shapefile,
            "shx": shxfile,
            "dbf": dbffile,
            "cpg": cpgfile,
            "prj": prjfile
        })

        # 2. Validação de datas e parâmetros (mantido da versão original)
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
            if not 0 <= cloud_pixel_percentage <= 100:
                raise HTTPException(status_code=400, detail="Percentual de nuvens inválido")
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido")

        # 3. Processa imagens no Earth Engine (mantido original)
        processor = EarthEngineProcessor()
        result, _ = await processor.process_data(
            parameters={
                "data": [start_date, end_date],
                "filter": f"CLOUDY_PIXEL_PERCENTAGE,{cloud_pixel_percentage}"
            },
            geometry=geometry
        )

        if not result:
            raise HTTPException(status_code=404, detail="Nenhuma imagem encontrada")

        # 4. Cria ROI no banco (com metadados completos)
        roi_data = {
            "nome": Path(shapefile.filename).stem,
            "descricao": f"Shapefile processado em {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "geometria": json.dumps(geometry.toGeoJSON()),
            "tipo_origem": "shapefile",
            "metadata": {
                "start_date": start_date,
                "end_date": end_date,
                "cloud_cover": cloud_pixel_percentage,
                "files": [f.filename for f in result]
            },
            "nome_arquivo_original": shapefile.filename,
            "arquivos_relacionados": metadados["arquivos_enviados"]
        }

        roi_criada = await criar_roi(
            user_id=current_user['id'],
            roi_data=roi_data
        )
        logger.info(f"ROI criada: {roi_criada['roi_id']}")

        # 5. Gera ZIP (mantido original)
        zip_creator = ZipCreator()
        zip_buffer = await zip_creator.create_zip_file(result)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={'Content-Disposition': 'attachment; filename="shapefile_images.zip"'}
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))