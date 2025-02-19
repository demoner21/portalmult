from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import List
import os
import shutil
from datetime import datetime
from pathlib import Path

router = APIRouter()

@router.post("/download_image/")
async def upload_shapefile(
    shapefile: UploadFile = File(..., description="Arquivo .shp"),
    shxfile: UploadFile = File(..., description="Arquivo .shx"),
    dbffile: UploadFile = File(..., description="Arquivo .dbf"),
    start_date: str = Query(..., description="Data de início no formato YYYY-MM-DD"),
    end_date: str = Query(..., description="Data de término no formato YYYY-MM-DD"),
    cloud_pixel_percentage: float = Query(..., description="Percentual máximo de nuvens permitido (0 a 100)")
):
    """
    Faz o upload de arquivos .shp, .shx e .dbf, valida o intervalo de datas e aplica o filtro de nuvens.
    """
    try:
        # Validar o intervalo de datas
        validate_date_range(start_date, end_date)

        # Validar o percentual de nuvens
        if not 0 <= cloud_pixel_percentage <= 100:
            raise HTTPException(
                status_code=400,
                detail="O percentual de nuvens deve estar entre 0 e 100."
            )

        # Salvar os arquivos temporariamente
        temp_dir = Path("temp_shapefile")
        temp_dir.mkdir(exist_ok=True)

        shapefile_path = temp_dir / shapefile.filename
        shxfile_path = temp_dir / shxfile.filename
        dbffile_path = temp_dir / dbffile.filename

        with open(shapefile_path, "wb") as buffer:
            shutil.copyfileobj(shapefile.file, buffer)
        with open(shxfile_path, "wb") as buffer:
            shutil.copyfileobj(shxfile.file, buffer)
        with open(dbffile_path, "wb") as buffer:
            shutil.copyfileobj(dbffile.file, buffer)

        # Aqui você pode adicionar a lógica para processar os arquivos .shp, .shx e .dbf
        # e aplicar o filtro de nuvens usando o Earth Engine.

        # Exemplo de retorno (substitua pela lógica real)
        return {
            "message": "Arquivos recebidos e validados com sucesso.",
            "start_date": start_date,
            "end_date": end_date,
            "cloud_pixel_percentage": cloud_pixel_percentage,
            "shapefile": shapefile.filename,
            "shxfile": shxfile.filename,
            "dbffile": dbffile.filename
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao processar os arquivos: {str(e)}"
        )
    finally:
        # Limpar os arquivos temporários após o processamento
        if temp_dir.exists():
            shutil.rmtree(temp_dir)