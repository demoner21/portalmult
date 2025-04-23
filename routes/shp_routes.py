from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from typing import List
from datetime import datetime
from pathlib import Path
import json
import logging
import ee
from utils.upload_utils import save_uploaded_files, cleanup_temp_files
from utils.shapefile_utils import extrair_geometria_shp
from services.earth_engine_processor import EarthEngineProcessor
from utils.zip_creator import ZipCreator
from utils.jwt_utils import get_current_user
from database.roi_queries import criar_roi

logger = logging.getLogger(__name__)

router = APIRouter()

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
    """
    Faz o upload de shapefile, processa imagens e cria uma ROI associada ao usuário.
    Retorna um ZIP com as imagens processadas.
    """
    temp_dir = None
    try:
        # Validação dos arquivos obrigatórios
        arquivos_obrigatorios = [shapefile, shxfile, dbffile]
        for arquivo in arquivos_obrigatorios:
            if arquivo is None:
                raise HTTPException(status_code=400, detail=f"Arquivo {arquivo.filename} é obrigatório.")

        # Salva arquivos temporariamente
        temp_dir = save_uploaded_files([shapefile, shxfile, dbffile, cpgfile, prjfile])
        shapefile_path = temp_dir / shapefile.filename

        # Extrai geometria do shapefile
        ee_geometry = extrair_geometria_shp(shapefile_path)
        if ee_geometry is None:
            raise HTTPException(status_code=400, detail="Shapefile inválido ou vazio.")

        # Validação dos parâmetros
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido. Use 'YYYY-MM-DD'.")

        if not 0 <= cloud_pixel_percentage <= 100:
            raise HTTPException(status_code=400, detail="O percentual de nuvens deve estar entre 0 e 100.")

        # Processa as imagens
        processor = EarthEngineProcessor()
        result, _ = await processor.process_data(
            parameters={
                "latitude": 0,  # Não usado quando geometry é fornecido
                "longitude": 0,
                "data": [start_date, end_date],
                "filter": f"CLOUDY_PIXEL_PERCENTAGE,{cloud_pixel_percentage}"
            },
            geometry=ee_geometry
        )

        if not result:
            raise HTTPException(status_code=404, detail="Nenhuma imagem encontrada para os parâmetros fornecidos.")

        # Cria a ROI no banco de dados
        roi_data = {
            "nome": Path(shapefile.filename).stem,
            "descricao": f"Shapefile processado em {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "geometria": json.dumps(ee_geometry.toGeoJSON()),
            "tipo_origem": "shapefile",
            "metadata": {
                "start_date": start_date,
                "end_date": end_date,
                "cloud_cover": cloud_pixel_percentage,
                "files": [f.filename for f in result]
            }
        }

        roi_criada = await criar_roi(
            user_id=current_user['id'],
            roi_data=roi_data
        )
        logger.info(f"ROI criada: {roi_criada['roi_id']}")

        # Cria e retorna o ZIP
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
        raise HTTPException(status_code=500, detail=f"Erro ao processar shapefile: {str(e)}")
    finally:
        if temp_dir:
            cleanup_temp_files(temp_dir)