from fastapi.middleware.cors import CORSMiddleware

def add_cors_middleware(app):
    """
    Adiciona o middleware de CORS ao aplicativo FastAPI.

    Args:
        app: Instância do FastAPI.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8000",
            "http://localhost:3000",
            "http://192.168.0.127:8000",
            "http://172.20.141.26:8000",
            "http://172.20.128.1:8000",
            "*"  # Para testes - remova em produção
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )