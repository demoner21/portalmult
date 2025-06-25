from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path
import json
import logging
from services.shapefile_processor import ShapefileProcessor
from database.roi_queries import criar_roi, listar_rois_usuario, obter_roi_por_id, atualizar_roi, deletar_roi
from utils.jwt_utils import get_current_user
from utils.geometry_utils import validate_geometry_wkt
from utils.upload_utils import save_uploaded_files, cleanup_temp_files
from pydantic import BaseModel, Field, validator

router = APIRouter(
    prefix="/roi",
    tags=["Regiões de Interesse"],
    responses={404: {"description": "Não encontrado"}}
)
logger = logging.getLogger(__name__)

ALLOWED_FILE_TYPES = {
    'shp': 'application/octet-stream',
    'shx': 'application/octet-stream', 
    'dbf': 'application/octet-stream',
    'prj': 'text/plain',
    'cpg': 'text/plain'
}
MAX_FILE_SIZE_MB = 20
MAX_VERTICES = 10000

class ROIBase(BaseModel):
    nome: str
    descricao: Optional[str] = "ROI criada via upload de shapefile"
    geometria: Dict[str, Any]
    tipo_origem: str
    status: Optional[str] = "ativo"
    nome_arquivo_original: Optional[str] = None
    metadata: Optional[Dict] = None

VALID_STATUS_VALUES = ["ativo", "inativo", "processando", "erro"]

class ROIResponse(ROIBase):
    roi_id: int
    data_criacao: Optional[datetime] = None
    data_modificacao: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ShapefileUploadResponse(ROIResponse):
    arquivos_processados: Dict[str, str] = Field(..., description="Arquivos processados")
    avisos: Optional[List[str]] = Field(None, description="Avisos opcionais do processamento")

class ROICreate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None


def validate_shapefile_files(files: Dict[str, UploadFile]):
    """Valida os arquivos do shapefile antes do processamento"""
    errors = []
    
    required_files = ['shp', 'shx', 'dbf']
    for req in required_files:
        if req not in files or files[req] is None:
            errors.append(f"Arquivo .{req} é obrigatório")
    
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

def process_roi_data(roi_dict: dict) -> dict:
    """Processa os dados da ROI para garantir o formato correto dos campos JSON"""
    processed = dict(roi_dict)
    
    if isinstance(processed.get('geometria'), str):
        try:
            processed['geometria'] = json.loads(processed['geometria'])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Erro ao decodificar geometria para ROI {processed.get('roi_id')}")
    
    if isinstance(processed.get('metadata'), str):
        try:
            processed['metadata'] = json.loads(processed['metadata'])
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Erro ao decodificar metadata para ROI {processed.get('roi_id')}")
            processed['metadata'] = {}
    
    return processed

def validate_feature_collection_geometry(feature_collection: Dict[str, Any]) -> bool:
    """Valida se a FeatureCollection possui geometrias válidas"""
    try:
        if feature_collection.get('type') != 'FeatureCollection':
            return False
        
        features = feature_collection.get('features', [])
        if not features:
            return False
        
        # Validar pelo menos a primeira feature
        first_feature = features[0]
        if not isinstance(first_feature.get('geometry'), dict):
            return False
        
        geometry = first_feature['geometry']
        if not geometry.get('type') or not geometry.get('coordinates'):
            return False
        
        return True
    except Exception as e:
        logger.error(f"Erro na validação da geometria: {e}")
        return False

@router.post(
    "/upload-shapefile", 
    response_model=ShapefileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de shapefile para criação de ROI",
    description="""Cria uma Região de Interesse (ROI) a partir de um shapefile.
    Arquivos obrigatórios: .shp, .shx e .dbf
    Sistema de referência: WGS84 (EPSG:4326)
    A ROI será criada com status 'ativo' por padrão.
    
    IMPORTANTE: Preserva todas as features do shapefile como FeatureCollection.""",
    responses={
        400: {"description": "Erro na validação dos arquivos"},
        500: {"description": "Erro interno no processamento"}
    }
)
async def create_roi_from_shapefile(
    descricao: str = Form(..., description="Descrição da ROI fornecida pelo usuário"),
    shp: UploadFile = File(..., description="Arquivo principal .shp"),
    shx: UploadFile = File(..., description="Arquivo de índice .shx"),
    dbf: UploadFile = File(..., description="Arquivo de atributos .dbf"),
    prj: UploadFile = File(None, description="Arquivo de projeção .prj (opcional)"),
    cpg: UploadFile = File(None, description="Arquivo de codificação .cpg (opcional)"),
    current_user: dict = Depends(get_current_user)
):
    """Endpoint para upload de shapefile e criação de ROI com múltiplas features"""
    files = {
        'shp': shp,
        'shx': shx,
        'dbf': dbf,
        'prj': prj,
        'cpg': cpg
    }
    
    validate_shapefile_files(files)
    
    temp_dir = None
    try:
        # 1. Salvar arquivos temporários
        temp_dir = save_uploaded_files([f for f in files.values() if f is not None])
        logger.info(f"Arquivos salvos em diretório temporário: {temp_dir}")
        
        # 2. Processar shapefile
        processor = ShapefileProcessor()
        processing_result = await processor.process(temp_dir)
        
        logger.info(f"Shapefile processado: {len(processing_result['features'])} features encontradas")
        
        # 3. Criar FeatureCollection completa
        feature_collection = {
            "type": "FeatureCollection",
            "features": processing_result['features']
        }
        
        # 4. Validar geometria da FeatureCollection
        if not validate_feature_collection_geometry(feature_collection):
            raise HTTPException(
                status_code=400,
                detail="FeatureCollection inválida gerada do shapefile"
            )
        
        # 5. Preparar dados para criação da ROI
        roi_name = generate_roi_name(current_user['id'], files['shp'].filename)
        
        # Extrair metadados do processamento
        processing_metadata = processing_result.get('metadata', {})
        
        roi_data = {
            "nome": roi_name,
            "descricao": descricao,
            "geometria": feature_collection,  # FeatureCollection completa
            "tipo_origem": "shapefile",
            "metadata": {
                **processing_metadata,  # Inclui todos os metadados do processamento
                "arquivos_originais": {
                    "shp": files['shp'].filename,
                    "shx": files['shx'].filename,
                    "dbf": files['dbf'].filename,
                    "prj": files['prj'].filename if files['prj'] else None,
                    "cpg": files['cpg'].filename if files['cpg'] else None
                },
                # Incluir propriedades da primeira feature como exemplo
                "propriedades_exemplo": (
                    processing_result['features'][0]['properties'] 
                    if processing_result['features'] else {}
                )
            },
            "nome_arquivo_original": files['shp'].filename,
            "status": "ativo"
        }
        
        # 6. Criar ROI no banco de dados
        created_roi = await criar_roi(
            user_id=current_user['id'],
            roi_data=roi_data
        )
        
        processed_roi = process_roi_data(created_roi)
        
        # 7. Preparar resposta
        response_data = {
            **processed_roi,
            "arquivos_processados": {
                file_type: file.filename 
                for file_type, file in files.items() 
                if file is not None
            },
            "avisos": [
                f"Processadas {len(processing_result['features'])} features do shapefile",
                f"Área total: {processing_metadata.get('area_total_ha', 0):.2f} hectares"
            ] if len(processing_result['features']) > 1 else None
        }
        
        logger.info(f"ROI criada com sucesso: {created_roi.get('roi_id')}")
        return ShapefileUploadResponse(**response_data)
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro no processamento do shapefile: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar shapefile: {str(e)}"
        )
    finally:
        if temp_dir:
            cleanup_temp_files(temp_dir)

@router.get("/status/options")
async def get_status_options():
    """Lista os valores de status válidos para ROIs"""
    return {
        "status_options": VALID_STATUS_VALUES,
        "description": "Valores válidos para o campo status de uma ROI"
    }

@router.get("/", response_model=List[ROIResponse])
async def listar_minhas_rois(
    current_user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """Lista todas as ROIs do usuário"""
    try:
        rois = await listar_rois_usuario(
            user_id=current_user['id'],
            limit=limit,
            offset=offset
        )
        
        processed_rois = []
        for roi in rois:
            processed_roi = process_roi_data(roi)
            processed_rois.append(processed_roi)
        
        return processed_rois
    except Exception as e:
        logger.error(f"Erro ao listar ROIs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao listar regiões de interesse"
        )

@router.get("/{roi_id}", response_model=ROIResponse)
async def obter_roi(
    roi_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Obtém uma ROI específica do usuário"""
    try:
        roi = await obter_roi_por_id(roi_id, current_user['id'])
        if not roi:
            raise HTTPException(status_code=404, detail="ROI não encontrada")
        
        processed_roi = process_roi_data(roi)
            
        return ROIResponse(**processed_roi)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro ao obter ROI: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao obter região de interesse"
        )

@router.put(
    "/{roi_id}", 
    response_model=ROIResponse,
    summary="Atualizar ROI",
    description="""Atualiza metadados de uma Região de Interesse.
    
    Campos atualizáveis: nome e descrição
    """
)
async def atualizar_roi_route(
    roi_id: int,
    update_data: ROICreate,
    current_user: dict = Depends(get_current_user)
):
    """Atualiza metadados de uma ROI"""
    try:
        roi = await obter_roi_por_id(roi_id, current_user['id'])
        if not roi:
            raise HTTPException(status_code=404, detail="ROI não encontrada")
        
        update_dict = update_data.dict(exclude_unset=True)
        
        await atualizar_roi(
            roi_id=roi_id,
            user_id=current_user['id'],
            update_data=update_dict
        )
        
        updated_roi = await obter_roi_por_id(roi_id, current_user['id'])
        if not updated_roi:
            raise HTTPException(status_code=404, detail="ROI não encontrada após atualização")
        
        processed_roi = process_roi_data(updated_roi)
            
        return ROIResponse(**processed_roi)
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro ao atualizar ROI: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{roi_id}")
async def deletar_roi_route(
    roi_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Remove uma ROI do usuário"""
    try:
        roi = await obter_roi_por_id(roi_id, current_user['id'])
        if not roi:
            raise HTTPException(status_code=404, detail="ROI não encontrada")
        
        await deletar_roi(roi_id, current_user['id'])
        return {"message": "ROI removida com sucesso"}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro ao deletar ROI: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao remover região de interesse"
        )