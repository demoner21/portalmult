from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import load_routes
from utils.logging import setup_logging
from utils.logging import logger
from middleware import add_cors_middleware, get_middlewares
from services.earth_engine_initializer import initialize_earth_engine

from routes.auth_routes import router as auth_router

# Inicializa o Earth Engine
initialize_earth_engine()

app = FastAPI(
    title="Portal Multespectral",
    version="0.1.0",
    middleware=get_middlewares(),
)

setup_logging()

# Montagem de arquivos estáticos (frontend de exemplo)
app.mount("/example", StaticFiles(directory="static", html=True), name="static")

for router in load_routes():
    app.include_router(router)

app.include_router(auth_router)

add_cors_middleware(app)

# Adicione no final do app.py
for route in app.routes:
    print(f"{route.path} -> {route.name}")

# Mensagem de inicialização
logger.info("Servidor iniciado com sucesso!")