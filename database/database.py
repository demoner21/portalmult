import os
import asyncpg
from dotenv import load_dotenv
from passlib.context import CryptContext
import logging

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

async def get_db_connection():
    """
    Cria e retorna uma conexão com o banco de dados.
    """
    try:
        connection = await asyncpg.connect(**DB_CONFIG)
        print("Conexão com o banco de dados estabelecida com sucesso!")
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        raise

async def close_db_connection(connection):
    """
    Fecha a conexão com o banco de dados.
    """
    try:
        await connection.close()
        print("Conexão com o banco de dados fechada com sucesso!")
    except Exception as e:
        print(f"Erro ao fechar a conexão com o banco de dados: {e}")
        raise

async def inserir_usuario(nome: str, email: str, senha: str, role: str = "user"):
    conn = await get_db_connection()
    try:
        hashed_password = get_password_hash(senha)  # Remova o await
        await conn.execute("""
            INSERT INTO usuario (nome, email, senha, role)
            VALUES ($1, $2, $3, $4)
        """, nome, email, hashed_password, role)
        print(f"Usuário {nome} inserido com sucesso!")
    except Exception as e:
        print(f"Erro ao inserir usuário: {e}")
        raise
    finally:
        await close_db_connection(conn)

async def verificar_email_existente(email: str) -> bool:
    conn = await get_db_connection()
    try:
        resultado = await conn.fetchval("""
            SELECT EXISTS(SELECT 1 FROM usuario WHERE email = $1)
        """, email)
        return resultado
    except Exception as e:
        print(f"Erro ao verificar email: {e}")
        raise
    finally:
        await close_db_connection(conn)

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

async def get_user_by_email(email: str):
    """
    Busca um usuário no banco de dados pelo email.
    
    Args:
        email (str): Email do usuário a ser buscado.
    
    Returns:
        dict: Dados do usuário se encontrado, None caso contrário.
    """
    conn = await get_db_connection()
    try:
        user = await conn.fetchrow("SELECT * FROM usuario WHERE email = $1", email)
        logger.info(f"Usuário encontrado: {user}")
        return user
    except Exception as e:
        logger.error(f"Erro ao buscar usuário por email: {e}")
        raise
    finally:
        await close_db_connection(conn)

async def excluir_usuario_por_id(id: int):
    conn = await get_db_connection()
    try:
        await conn.execute("""
            DELETE FROM usuario WHERE id = $1
        """, id)
        print(f"Usuário com id {id} excluído com sucesso!")
    except Exception as e:
        print(f"Erro ao excluir usuário: {e}")
        raise
    finally:
        await close_db_connection(conn)

async def excluir_usuario_por_email(email: str):
    conn = await get_db_connection()
    try:
        await conn.execute("""
            DELETE FROM usuario WHERE email = $1
        """, email)
        print(f"Usuário com email {email} excluído com sucesso!")
    except Exception as e:
        print(f"Erro ao excluir usuário: {e}")
        raise
    finally:
        await close_db_connection(conn)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())