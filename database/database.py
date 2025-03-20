from functools import wraps
import asyncpg
from dotenv import load_dotenv
from passlib.context import CryptContext
import logging
import os

logger = logging.getLogger(__name__)

# Configuração para hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações do banco de dados a partir das variáveis de ambiente
DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

def with_db_connection(func):
    """
    Decorador para gerenciar a conexão com o banco de dados.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        conn = None
        try:
            conn = await asyncpg.connect(**DB_CONFIG)
            logger.info("Conexão com o banco de dados estabelecida com sucesso!")
            return await func(conn, *args, **kwargs)
        except Exception as e:
            logger.error(f"Erro ao executar a função: {e}", exc_info=True)
            raise
        finally:
            if conn:
                await conn.close()
                logger.info("Conexão com o banco de dados fechada com sucesso!")
    return wrapper

@with_db_connection
async def inserir_usuario(conn, nome: str, email: str, senha: str, role: str = "user"):
    hashed_password = get_password_hash(senha)
    await conn.execute("""
        INSERT INTO usuario (nome, email, senha, role)
        VALUES ($1, $2, $3, $4)
    """, nome, email, hashed_password, role)
    logger.info(f"Usuário {nome} inserido com sucesso!")

@with_db_connection
async def verificar_email_existente(conn, email: str) -> bool:
    resultado = await conn.fetchval("""
        SELECT EXISTS(SELECT 1 FROM usuario WHERE email = $1)
    """, email)
    return resultado

@with_db_connection
async def get_user_by_email(conn, email: str):
    user = await conn.fetchrow("SELECT * FROM usuario WHERE email = $1", email)
    logger.info(f"Usuário encontrado: {user}")
    return user

@with_db_connection
async def excluir_usuario_por_id(conn, id: int):
    await conn.execute("""
        DELETE FROM usuario WHERE id = $1
    """, id)
    logger.info(f"Usuário com id {id} excluído com sucesso!")

@with_db_connection
async def excluir_usuario_por_email(conn, email: str):
    await conn.execute("""
        DELETE FROM usuario WHERE email = $1
    """, email)
    logger.info(f"Usuário com email {email} excluído com sucesso!")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha fornecida corresponde ao hash armazenado.
    """
    result = pwd_context.verify(plain_password, hashed_password)
    logger.info(f"Resultado da verificação de senha: {result}")
    return result

def get_password_hash(password: str) -> str:
    """
    Gera um hash para a senha fornecida.
    """
    return pwd_context.hash(password)