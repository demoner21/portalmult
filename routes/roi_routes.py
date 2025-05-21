from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
import json
import logging
from services.shapefile_processor import ShapefileProcessor
from models.roi_models import ROIResponse, ROICreate
from database.roi_queries import criar_roi, listar_rois_usuario, obter_roi_por_id, atualizar_roi, deletar_roi
from utils.jwt_utils import get_current_user
from utils.geometry_utils import validate_geometry_wkt
from utils.upload_utils import save_uploaded_files, cleanup_temp_files

router = APIRouter(
    prefix="/roi",
    tags=["Regiões de Interesse"],
    responses={404: {"description": "Não encontrado"}}
)
logger = logging.getLogger(__name__)

# Configurações
ALLOWED_FILE_TYPES = {
    'shp': 'application/octet-stream',
    'shx': 'application/octet-stream', 
    'dbf': 'application/octet-stream',
    'prj': 'text/plain',
    'cpg': 'text/plain'
}
MAX_FILE_SIZE_MB = 10
MAX_VERTICES = 10000

class ShapefileUploadResponse(ROIResponse):
    arquivos_processados: Dict[str, str]
    avisos: Optional[List[str]] = None

def validate_shapefile_files(files: Dict[str, UploadFile]):
    """Valida os arquivos do shapefile antes do processamento"""
    errors = []
    
    # Verifica arquivos obrigatórios
    required_files = ['shp', 'shx', 'dbf']
    for req in required_files:
        if req not in files or files[req] is None:
            errors.append(f"Arquivo .{req} é obrigatório")
    
    # Valida tipos e tamanhos
    for file_type, file in files.items():
        if file is None:
            continue
            
        if file_type not in ALLOWED_FILE_TYPES:
            errors.append(f"Tipo de arquivo não suportado: {file_type}")
            continue
            
        file_size = file.size / (1024 * 1024)  # MB
        if file_size > MAX_FILE_SIZE_MB:
            errors.append(f"Arquivo {file.filename} excede o tamanho máximo de {MAX_FILE_SIZE_MB}MB")
    
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors}
        )

def generate_roi_name(user_id: int, original_name: str) -> str:
    """Gera um nome padronizado para a ROI"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_name = Path(original_name).stem.replace(" ", "_")
    return f"ROI_{user_id}_{clean_name}_{timestamp}"

@router.post(
    "/upload-shapefile", 
    response_model=ShapefileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de shapefile para criação de ROI",
    description="""Cria uma Região de Interesse (ROI) a partir de um shapefile.
    Arquivos obrigatórios: .shp, .shx e .dbf
    Sistema de referência: WGS84 (EPSG:4326)""",
    responses={
        400: {
            "description": "Erro na validação dos arquivos",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "errors": [
                                "Arquivo .shp é obrigatório",
                                "Arquivo excede o tamanho máximo"
                            ]
                        }
                    }
                }
            }
        },
        500: {
            "description": "Erro interno no processamento",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Erro ao processar shapefile"
                    }
                }
            }
        }
    }
)
async def create_roi_from_shapefile(
    shp: UploadFile = File(..., description="Arquivo principal .shp"),
    shx: UploadFile = File(..., description="Arquivo de índice .shx"),
    dbf: UploadFile = File(..., description="Arquivo de atributos .dbf"),
    prj: UploadFile = File(None, description="Arquivo de projeção .prj (opcional)"),
    cpg: UploadFile = File(None, description="Arquivo de codificação .cpg (opcional)"),
    current_user: dict = Depends(get_current_user)
):
    """Endpoint para upload de shapefile e criação de ROI"""
    files = {
        'shp': shp,
        'shx': shx,
        'dbf': dbf,
        'prj': prj,
        'cpg': cpg
    }
    
    # 1. Validação inicial dos arquivos
    validate_shapefile_files(files)
    
    temp_dir = None
    try:
        # 2. Salvar arquivos temporariamente
        temp_dir = save_uploaded_files([f for f in files.values() if f is not None])
        
        # 3. Processar shapefile
        processor = ShapefileProcessor()
        processing_result = await processor.process(temp_dir)
        
        # 4. Validar geometria
        if not validate_geometry_wkt(processing_result['wkt']):
            raise HTTPException(
                status_code=400,
                detail="Geometria inválida no shapefile"
            )
        
        # 5. Preparar dados para criação da ROI
        roi_name = generate_roi_name(current_user['id'], files['shp'].filename)
        
        roi_data = {
            "nome": roi_name,
            "descricao": f"Upload via shapefile em {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "geometria": processing_result['geojson'],
            "tipo_origem": "shapefile",
            "metadata": {
                "sistema_referencia": "EPSG:4326",
                "tipo_geometria": processing_result['type'],
                "area_ha": processing_result['area'],
                "bbox": processing_result['bbox'],
                "arquivos_originais": {
                    "shp": files['shp'].filename,
                    "shx": files['shx'].filename,
                    "dbf": files['dbf'].filename,
                    "prj": files['prj'].filename if files['prj'] else None,
                    "cpg": files['cpg'].filename if files['cpg'] else None
                },
                "propriedades": processing_result.get('properties', {})
            },
            "nome_arquivo_original": files['shp'].filename
        }
        
        # 6. Criar ROI no banco de dados
        created_roi = await criar_roi(
            user_id=current_user['id'],
            roi_data=roi_data
        )
        
        # 7. Montar resposta
        response = ShapefileUploadResponse(
            **created_roi,
            arquivos_processados={
                file_type: file.filename 
                for file_type, file in files.items() 
                if file is not None
            }
        )
        
        return response
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro no processamento do shapefile: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao processar shapefile"
        )
    finally:
        if temp_dir:
            cleanup_temp_files(temp_dir)

# Rotas CRUD básicas para ROIs
@router.get("/", response_model=List[ROIResponse])
async def listar_minhas_rois(
    current_user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """Lista todas as ROIs do usuário"""
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
    """Obtém uma ROI específica do usuário"""
    roi = await obter_roi_por_id(roi_id, current_user['id'])
    if not roi:
        raise HTTPException(status_code=404, detail="ROI não encontrada")
    return roi

@router.put("/{roi_id}", response_model=ROIResponse)
async def atualizar_roi_route(
    roi_id: int,
    update_data: ROICreate,
    current_user: dict = Depends(get_current_user)
):
    """Atualiza metadados de uma ROI"""
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
    """Remove uma ROI do usuário"""
    roi = await obter_roi_por_id(roi_id, current_user['id'])
    if not roi:
        raise HTTPException(status_code=404, detail="ROI não encontrada")
    
    await deletar_roi(roi_id, current_user['id'])
    return {"message": "ROI removida com sucesso"}