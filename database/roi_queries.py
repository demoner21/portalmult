from database.database import with_db_connection
from utils.jwt_utils import get_current_user
from typing import List, Optional, Dict
import json

@with_db_connection
async def criar_roi(conn, user_id: int, roi_data: Dict):
    """
    Cria uma nova ROI no banco de dados
    """
    return await conn.fetchrow(
        """
        INSERT INTO regiao_de_interesse 
        (user_id, nome, descricao, geometria, tipo_origem, metadata, sistema_referencia)
        VALUES ($1, $2, $3, ST_GeomFromText($4, 4326), $5, $6, 'EPSG:4326')
        RETURNING roi_id, nome, ST_AsGeoJSON(geometria)::json as geometria, 
                  tipo_origem, status, data_criacao
        """,
        user_id,
        roi_data['nome'],
        roi_data.get('descricao'),
        roi_data['geometria'],
        roi_data['tipo_origem'],
        json.dumps(roi_data.get('metadata', {}))
    )

@with_db_connection
async def listar_rois_usuario(conn, user_id: int, limit: int = 100, offset: int = 0):
    """
    Lista todas as ROIs de um usuário com paginação
    """
    return await conn.fetch(
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

@with_db_connection
async def obter_roi_por_id(conn, roi_id: int, user_id: int):
    """
    Obtém uma ROI específica verificando o proprietário
    """
    return await conn.fetchrow(
        """
        SELECT roi_id, nome, descricao, ST_AsGeoJSON(geometria)::json as geometria,
               tipo_origem, status, data_criacao, data_modificacao, metadata
        FROM regiao_de_interesse
        WHERE roi_id = $1 AND user_id = $2
        """,
        roi_id, user_id
    )

@with_db_connection
async def atualizar_roi(conn, roi_id: int, user_id: int, update_data: Dict):
    """
    Atualiza os metadados de uma ROI
    """
    query = """
        UPDATE regiao_de_interesse
        SET nome = COALESCE($3, nome),
            descricao = COALESCE($4, descricao),
            status = COALESCE($5, status),
            data_modificacao = CURRENT_TIMESTAMP
        WHERE roi_id = $1 AND user_id = $2
        RETURNING roi_id, nome, descricao, status, data_modificacao
    """
    return await conn.fetchrow(
        query,
        roi_id,
        user_id,
        update_data.get('nome'),
        update_data.get('descricao'),
        update_data.get('status')
    )

@with_db_connection
async def deletar_roi(conn, roi_id: int, user_id: int):
    """
    Remove uma ROI do banco de dados
    """
    await conn.execute(
        "DELETE FROM regiao_de_interesse WHERE roi_id = $1 AND user_id = $2",
        roi_id, user_id
    )