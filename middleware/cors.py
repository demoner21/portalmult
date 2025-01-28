from fastapi.middleware.cors import CORSMiddleware

def add_cors_middleware(app):
    """
    Adiciona o middleware de CORS ao aplicativo FastAPI.

    Args:
        app: Instância do FastAPI.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Permite todas as origens
        allow_credentials=True,
        allow_methods=["*"],  # Permite todos os métodos (GET, POST, etc.)
        allow_headers=["*"],  # Permite todos os cabeçalhos
    )