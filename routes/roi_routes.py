from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import List, Optional
from models.roi_models import ROICreate, ROIUpdate, ROIResponse
from database.roi_queries import (
    criar_roi,
    listar_rois_usuario,
    obter_roi_por_id,
    atualizar_roi,
    deletar_roi
)
from database.database import get_current_user
from utils.geometry_utils import validate_geometry_wkt
import json

router = APIRouter(
    prefix="/roi",
    tags=["Regiões de Interesse"],
    responses={404: {"description": "Não encontrado"}}
)

@router.post("/", response_model=ROIResponse)
async def criar_nova_roi(
    roi_data: ROICreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Cria uma nova região de interesse (ROI)
    
    - **geometria**: Deve ser uma string WKT (Well-Known Text) válida
    - **tipo_origem**: manual, shapefile, geojson ou kml
    """
    if not validate_geometry_wkt(roi_data.geometria):
        raise HTTPException(status_code=400, detail="Geometria inválida")
    
    try:
        roi = await criar_roi(
            user_id=current_user['id'],
            roi_data=roi_data.dict()
        )
        return roi
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[ROIResponse])
async def listar_minhas_rois(
    current_user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """
    Lista todas as regiões de interesse do usuário atual
    """
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
    """
    Obtém detalhes de uma região de interesse específica
    """
    roi = await obter_roi_por_id(roi_id, current_user['id'])
    if not roi:
        raise HTTPException(status_code=404, detail="ROI não encontrada")
    return roi

@router.put("/{roi_id}", response_model=ROIResponse)
async def atualizar_roi(
    roi_id: int,
    update_data: ROIUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Atualiza os metadados de uma região de interesse
    
    - Apenas nome, descrição e status podem ser atualizados
    - A geometria não pode ser alterada (crie uma nova ROI se necessário)
    """
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
async def deletar_roi(
    roi_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove uma região de interesse
    
    - Esta ação é irreversível
    - Todos os dados associados serão removidos em cascata
    """
    roi = await obter_roi_por_id(roi_id, current_user['id'])
    if not roi:
        raise HTTPException(status_code=404, detail="ROI não encontrada")
    
    await deletar_roi(roi_id, current_user['id'])
    return {"message": "ROI removida com sucesso"}