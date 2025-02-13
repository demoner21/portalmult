import ee
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware import Middleware
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi_structlog.middleware import AccessLogMiddleware, CurrentScopeSetMiddleware, StructlogMiddleware
from routes import map_router, predict_router, visualize_router, shp_routes
from utils.logging import setup_logging
import structlog
from middleware import add_logging_middleware, add_cors_middleware
from services.earth_engine_initializer import initialize_earth_engine

# Configuração do structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,  # Filtra logs por nível
        structlog.processors.TimeStamper(fmt="iso"),  # Adiciona timestamp
        structlog.processors.JSONRenderer()  # Formata logs como JSON
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Configuração do logging
logger = setup_logging()

# Inicializa o Earth Engine
initialize_earth_engine()

# Configuração do FastAPI
app = FastAPI(
    title="Spin Mining Susano",
    version="0.1.0",
    middleware=[
        Middleware(CurrentScopeSetMiddleware),
        Middleware(CorrelationIdMiddleware),
        Middleware(StructlogMiddleware),
        Middleware(AccessLogMiddleware),
    ],
)

add_logging_middleware(app)
add_cors_middleware(app)

# Montagem de arquivos estáticos (frontend de exemplo)
app.mount("/example", StaticFiles(directory="static", html=True), name="static")

# Inclusão das rotas
app.include_router(map_router)
app.include_router(shp_routes)
app.include_router(predict_router)
app.include_router(visualize_router)

# Mensagem de inicialização
logger.info("Servidor iniciado com sucesso!")