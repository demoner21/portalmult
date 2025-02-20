import os
import asyncpg
from dotenv import load_dotenv

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

# Exemplo de uso
async def main():
    # Conecta ao banco de dados
    conn = await get_db_connection()

    # Executa uma consulta de exemplo
    try:
        result = await conn.fetch("SELECT * FROM usuario;")
        print("Resultado da consulta:", result)
    finally:
        # Fecha a conexão
        await close_db_connection(conn)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
