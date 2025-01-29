from fastapi.middleware.cors import CORSMiddleware

def add_cors_middleware(app):
    """
    Adiciona o middleware de CORS ao aplicativo FastAPI.

    Args:
        app: Instância do FastAPI.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )