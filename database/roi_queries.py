import logging
from database.database import with_db_connection
from typing import List, Optional, Dict
import json

logger = logging.getLogger(__name__)

@with_db_connection
async def criar_roi(
    conn,  # Conexão injetada pelo decorador
    *,  # Força os próximos argumentos a serem keyword-only
    user_id: int,
    roi_data: Dict
):
    """
    Cria uma nova ROI no banco de dados
    
    Args:
        conn: Conexão com o banco (injetada pelo decorador)
        user_id: ID do usuário proprietário
        roi_data: Dicionário com os dados da ROI
    """
    try:
        # Converte metadata para JSON string se for um dicionário
        metadata = roi_data.get('metadata', {})
        if isinstance(metadata, dict):
            metadata = json.dumps(metadata)
            
        # Converte geometria para string JSON se for dict
        geometria = roi_data['geometria']
        if isinstance(geometria, dict):
            geometria = json.dumps(geometria)

        result = await conn.fetchrow(
            """
            INSERT INTO regiao_de_interesse 
            (user_id, nome, descricao, geometria, tipo_origem, metadata, sistema_referencia,
             nome_arquivo_original, arquivos_relacionados)
            VALUES ($1, $2, $3, ST_GeomFromGeoJSON($4), $5, $6::jsonb, 'EPSG:4326', $7, $8::jsonb)
            RETURNING roi_id, nome, ST_AsGeoJSON(geometria)::json as geometria, 
                      tipo_origem, status, data_criacao, nome_arquivo_original
            """,
            user_id,  # $1
            roi_data['nome'],  # $2
            roi_data.get('descricao', ''),  # $3
            geometria,  # $4
            roi_data['tipo_origem'],  # $5
            metadata,  # $6
            roi_data.get('nome_arquivo_original'),  # $7
            json.dumps(roi_data.get('arquivos_relacionados', {}))  # $8
        )
        return dict(result)
    except Exception as e:
        logger.error(f"Erro ao criar ROI: {str(e)}", exc_info=True)
        raise

@with_db_connection
async def listar_rois_usuario(conn, user_id: int, limit: int = 100, offset: int = 0) -> List[Dict]:
    """
    Lista todas as ROIs de um usuário com paginação
    
    Args:
        conn: Conexão com o banco de dados
        user_id: ID do usuário
        limit: Limite de resultados
        offset: Deslocamento
        
    Returns:
        Lista de dicionários com as ROIs do usuário
    """
    try:
        results = await conn.fetch(
            """
            SELECT roi_id, nome, descricao, ST_AsGeoJSON(geometria)::json as geometria,
                   tipo_origem, status, data_criacao, data_modificacao
            FROM regiao_de_interesse
            WHERE user_id = $1
            ORDER BY data_criacao DESC
            LIMIT $2 OFFSET $3
            """,
            user_id, limit, offset
        )
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Erro ao listar ROIs: {str(e)}", exc_info=True)
        raise

@with_db_connection
async def obter_roi_por_id(conn, roi_id: int, user_id: int) -> Optional[Dict]:
    """
    Obtém uma ROI específica verificando o proprietário
    
    Args:
        conn: Conexão com o banco de dados
        roi_id: ID da ROI
        user_id: ID do usuário (para verificação de propriedade)
        
    Returns:
        Dicionário com os dados da ROI ou None se não encontrada
    """
    try:
        result = await conn.fetchrow(
            """
            SELECT roi_id, nome, descricao, ST_AsGeoJSON(geometria)::json as geometria,
                   tipo_origem, status, data_criacao, data_modificacao, metadata
            FROM regiao_de_interesse
            WHERE roi_id = $1 AND user_id = $2
            """,
            roi_id, user_id
        )
        return dict(result) if result else None
    except Exception as e:
        logger.error(f"Erro ao obter ROI: {str(e)}", exc_info=True)
        raise

@with_db_connection
async def atualizar_roi(conn, roi_id: int, user_id: int, update_data: Dict) -> Optional[Dict]:
    """
    Atualiza os metadados de uma ROI
    
    Args:
        conn: Conexão com o banco de dados
        roi_id: ID da ROI
        user_id: ID do usuário (para verificação)
        update_data: Dados para atualização:
            - nome: Novo nome (opcional)
            - descricao: Nova descrição (opcional)
            - status: Novo status (opcional)
            
    Returns:
        Dicionário com os dados atualizados ou None se não encontrada
    """
    try:
        result = await conn.fetchrow(
            """
            UPDATE regiao_de_interesse
            SET nome = COALESCE($3, nome),
                descricao = COALESCE($4, descricao),
                status = COALESCE($5, status),
                data_modificacao = CURRENT_TIMESTAMP
            WHERE roi_id = $1 AND user_id = $2
            RETURNING roi_id, nome, descricao, status, data_modificacao
            """,
            roi_id,
            user_id,
            update_data.get('nome'),
            update_data.get('descricao'),
            update_data.get('status')
        )
        return dict(result) if result else None
    except Exception as e:
        logger.error(f"Erro ao atualizar ROI: {str(e)}", exc_info=True)
        raise

@with_db_connection
async def deletar_roi(conn, roi_id: int, user_id: int) -> bool:
    """
    Remove uma ROI do banco de dados
    
    Args:
        conn: Conexão com o banco de dados
        roi_id: ID da ROI
        user_id: ID do usuário (para verificação)
        
    Returns:
        True se a ROI foi deletada, False caso contrário
    """
    try:
        result = await conn.execute(
            "DELETE FROM regiao_de_interesse WHERE roi_id = $1 AND user_id = $2",
            roi_id, user_id
        )
        return result == "DELETE 1"
    except Exception as e:
        logger.error(f"Erro ao deletar ROI: {str(e)}", exc_info=True)
        raise