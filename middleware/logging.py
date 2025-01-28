import logging
from fastapi_structlog.middleware import AccessLogMiddleware, CurrentScopeSetMiddleware, StructlogMiddleware
from asgi_correlation_id import CorrelationIdMiddleware

def add_logging_middleware(app):
    """
    Adiciona middlewares de logging ao aplicativo FastAPI.

    Args:
        app: Instância do FastAPI.
    """
    # Configuração básica do logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Adiciona middlewares de logging
    app.add_middleware(CurrentScopeSetMiddleware)
    app.add_middleware(CorrelationIdMiddleware)
    app.add_middleware(StructlogMiddleware)
    app.add_middleware(AccessLogMiddleware)