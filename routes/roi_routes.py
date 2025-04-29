from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import json
import logging
from services.shapefile_processor import ShapefileProcessor
from models.roi_models import ROICreate, ROIUpdate, ROIResponse
from database.roi_queries import (
    criar_roi,
    listar_rois_usuario,
    obter_roi_por_id,
    atualizar_roi,
    deletar_roi
)
from utils.jwt_utils import get_current_user
from utils.geometry_utils import validate_geometry_wkt

router = APIRouter(
    prefix="/roi",
    tags=["Regiões de Interesse"],
    responses={404: {"description": "Não encontrado"}}
)
logger = logging.getLogger(__name__)

def gerar_nome_automatico(user_id: int) -> str:
    """Gera um nome no formato 'ROI_<user_id>_<timestamp>'"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"ROI_{user_id}_{timestamp}"

# --- CRUD Base ---
@router.get("/", response_model=List[ROIResponse])
async def listar_minhas_rois(
    current_user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """Lista todas as ROIs do usuário."""
    return await listar_rois_usuario(
        user_id=current_user['id'],
        limit=limit,
        offset=offset
    )

@router.get("/{roi_id}", response_model=ROIResponse)
async def obter_roi(
    roi_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Obtém uma ROI específica."""
    roi = await obter_roi_por_id(roi_id, current_user['id'])
    if not roi:
        raise HTTPException(status_code=404, detail="ROI não encontrada")
    return roi

@router.put("/{roi_id}", response_model=ROIResponse)
async def atualizar_roi_route(
    roi_id: int,
    update_data: ROIUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Atualiza metadados de uma ROI."""
    roi = await obter_roi_por_id(roi_id, current_user['id'])
    if not roi:
        raise HTTPException(status_code=404, detail="ROI não encontrada")
    
    try:
        updated = await atualizar_roi(
            roi_id=roi_id,
            user_id=current_user['id'],
            update_data=update_data.dict(exclude_unset=True)
        )
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{roi_id}")
async def deletar_roi_route(
    roi_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Remove uma ROI."""
    roi = await obter_roi_por_id(roi_id, current_user['id'])
    if not roi:
        raise HTTPException(status_code=404, detail="ROI não encontrada")
    await deletar_roi(roi_id, current_user['id'])
    return {"message": "ROI removida com sucesso"}

# --- Rotas para Shapefiles ---
@router.post("/upload-shapefile", response_model=ROIResponse)
async def create_roi_from_shapefile(
    shp: UploadFile = File(..., description="Arquivo .shp"),
    shx: UploadFile = File(..., description="Arquivo .shx"),
    dbf: UploadFile = File(..., description="Arquivo .dbf"),
    cpgfile: UploadFile = File(None, description="Arquivo .cpg (opcional)"),
    prjfile: UploadFile = File(None, description="Arquivo .prj (opcional)"),
    current_user: dict = Depends(get_current_user)
):
    """Cria ROI com nome automático a partir de shapefile."""
    try:
        # Prepara arquivos a serem processados
        files_dict = {
            "shp": shp,
            "shx": shx,
            "dbf": dbf
        }
        
        # Adiciona arquivos opcionais se fornecidos
        if cpgfile:
            files_dict["cpg"] = cpgfile
        if prjfile:
            files_dict["prj"] = prjfile
            
        # Processa o shapefile
        geometry, metadados = await ShapefileProcessor.process_uploaded_files(files_dict)
        
        # Validação adicional da geometria
        if not validate_geometry_wkt(geometry["wkt"]):
            raise HTTPException(status_code=400, detail="Geometria inválida")

        # Cria ROI
        roi_data = {
            "nome": gerar_nome_automatico(current_user['id']),
            "descricao": f"Upload via shapefile em {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "geometria": geometry["wkt"],
            "tipo_origem": "shapefile",
            "metadata": {
                "arquivos_originais": {
                    "shp": shp.filename,
                    "shx": shx.filename,
                    "dbf": dbf.filename,
                    "cpg": cpgfile.filename if cpgfile else None,
                    "prj": prjfile.filename if prjfile else None
                },
                "nome_original": Path(shp.filename).stem,
                "tipo_geometria": geometry.get("type", "POLYGON")
            }
        }

        return await criar_roi(
            user_id=current_user['id'],
            roi_data=roi_data
        )

    except HTTPException as he:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar ROI: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Rotas Adicionais ---
@router.put("/{roi_id}/rename", response_model=ROIResponse)
async def renomear_roi(
    roi_id: int,
    novo_nome: str,
    current_user: dict = Depends(get_current_user)
):
    """Endpoint específico para renomear ROIs."""
    if not novo_nome or len(novo_nome) > 255:
        raise HTTPException(status_code=400, detail="Nome inválido (máx. 255 caracteres)")
    
    roi = await obter_roi_por_id(roi_id, current_user['id'])
    if not roi:
        raise HTTPException(status_code=404, detail="ROI não encontrada")
    return await atualizar_roi(
        roi_id=roi_id,
        user_id=current_user['id'],
        update_data={"nome": novo_nome}
    )