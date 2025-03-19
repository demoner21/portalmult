import ee
from fastapi import FastAPI, HTTPException, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.middleware import Middleware
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi_structlog.middleware import AccessLogMiddleware, CurrentScopeSetMiddleware, StructlogMiddleware
from routes import map_router, predict_router, visualize_router, shp_routes
from utils.logging import setup_logging
import structlog
from middleware import add_logging_middleware, add_cors_middleware
from services.earth_engine_initializer import initialize_earth_engine
from routes.usuario_routes import router as usuario_router


from jose import JWTError, jwt
from pydantic import BaseModel
import httpx

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

# Configurações do Keycloak
KEYCLOAK_URL = "http://localhost:8080/realms/FastAPI-realm-real"
CLIENT_ID = "FastAPI-realm-realm"
CLIENT_SECRET = "your-client-secret"
ALGORITHM = "RS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class TokenData(BaseModel):
    sub: str
    email: str
    roles: list[str]

async def get_public_key():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{KEYCLOAK_URL}/protocol/openid-connect/certs")
        response.raise_for_status()
        jwks = response.json()
        return jwks["keys"][0]

async def decode_token(token: str):
    public_key = await get_public_key()
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[ALGORITHM],
            audience=CLIENT_ID,
        )
        return TokenData(
            sub=payload.get("sub"),
            email=payload.get("email"),
            roles=payload.get("realm_access", {}).get("roles", []),
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    return await decode_token(token)

@app.get("/protected")
async def protected_route(current_user: TokenData = Depends(get_current_user)):
    return {"message": f"Hello, {current_user.email}!"}

@app.get("/login")
async def login():
    return RedirectResponse(
        url=f"{KEYCLOAK_URL}/protocol/openid-connect/auth?client_id={CLIENT_ID}&response_type=code&redirect_uri=http://localhost:3000/callback"
    )

@app.get("/callback")
async def callback(code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{KEYCLOAK_URL}/protocol/openid-connect/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": "http://localhost:3000/callback",
            },
        )
        response.raise_for_status()
        token_data = response.json()
        return {"access_token": token_data["access_token"]}

add_logging_middleware(app)
add_cors_middleware(app)

# Montagem de arquivos estáticos (frontend de exemplo)
app.mount("/example", StaticFiles(directory="static", html=True), name="static")

# Inclusão das rotas
app.include_router(map_router)
app.include_router(shp_routes)
app.include_router(predict_router)
app.include_router(visualize_router)
app.include_router(usuario_router)

# Mensagem de inicialização
logger.info("Servidor iniciado com sucesso!")