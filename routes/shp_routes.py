from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import List
from datetime import datetime
from pathlib import Path
from utils.upload_utils import save_uploaded_files, cleanup_temp_files
from utils.shapefile_utils import extrair_geometria_shp
from services.earth_engine_processor import EarthEngineProcessor
import logging
import ee

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
    cloud_pixel_percentage: float = Query(..., description="Percentual máximo de nuvens permitido (0 a 100)")
):
    """
    Faz o upload de todos os arquivos do shapefile (.shp, .shx, .dbf, .cpg, .prj, etc.)
    e baixa imagens referentes à geometria do shapefile.
    """
    try:
        # Lista de arquivos obrigatórios
        arquivos_obrigatorios = [shapefile, shxfile, dbffile]

        # Verifica se os arquivos obrigatórios estão presentes
        for arquivo in arquivos_obrigatorios:
            if arquivo is None:
                raise HTTPException(status_code=400, detail=f"Arquivo {arquivo.filename} é obrigatório.")

        # Salvar todos os arquivos no diretório temporário
        temp_dir = save_uploaded_files([shapefile, shxfile, dbffile, cpgfile, prjfile])

        # Carregar o shapefile como uma geometria do Earth Engine
        shapefile_path = temp_dir / shapefile.filename
        ee_geometry = extrair_geometria_shp(shapefile_path)

        if ee_geometry is None:
            raise HTTPException(status_code=400, detail="Shapefile inválido ou vazio.")

        # Validar datas
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido. Use 'YYYY-MM-DD'.")

        # Validar percentual de nuvens
        if not 0 <= cloud_pixel_percentage <= 100:
            raise HTTPException(status_code=400, detail="O percentual de nuvens deve estar entre 0 e 100.")

        # Processar e baixar as imagens
        processor = EarthEngineProcessor()
        result, _ = await processor.process_data(
            parameters={
                "latitude": 0,  # Ajuste conforme necessário
                "longitude": 0,  # Ajuste conforme necessário
                "data": [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')],
                "filter": f"cloud_percentage,{cloud_pixel_percentage}"
            },
            geometry=ee_geometry
        )

        return {"message": "Imagens baixadas com sucesso.", "files": result}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar o shapefile: {str(e)}")
    finally:
        # Limpar os arquivos temporários
        cleanup_temp_files(temp_dir)