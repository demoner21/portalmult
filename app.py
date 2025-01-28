import ee
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware import Middleware
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi_structlog.middleware import AccessLogMiddleware, CurrentScopeSetMiddleware, StructlogMiddleware
from routes import map_router, predict_router, visualize_router
from utils.logging import setup_logging
import structlog
import logging

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
try:
    ee.Initialize()
except Exception as e:
    logger.error(f"Erro ao inicializar o Earth Engine: {str(e)}")
    logger.info("Autenticando no Earth Engine...")
    try:
        ee.Authenticate()
        ee.Initialize()
        logger.info("Autenticação e inicialização do Earth Engine concluídas com sucesso.")
    except Exception as auth_error:
        logger.error(f"Falha na autenticação do Earth Engine: {str(auth_error)}")
        raise RuntimeError("Não foi possível inicializar o Earth Engine. Verifique a autenticação.")

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

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montagem de arquivos estáticos (frontend de exemplo)
app.mount("/example", StaticFiles(directory="static", html=True), name="static")

# Inclusão das rotas
app.include_router(map_router)
app.include_router(predict_router)
app.include_router(visualize_router)

# Mensagem de inicialização
logger.info("Servidor iniciado com sucesso!")