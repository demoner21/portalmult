from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from auth.services import AuthService
from auth.models import TokenResponse
from auth.dependencies import oauth2_scheme
from database.database import get_user_by_email, verify_password
from auth.security import create_access_token, create_refresh_token
from auth.config import settings
import logging

router = APIRouter(prefix="/auth", tags=["Auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
auth_service = AuthService()
logger = logging.getLogger(__name__)

@router.post("/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint para autenticação de usuários e geração de tokens JWT.
    
    Args:
        form_data: Dados do formulário de login (username, password)
        
    Returns:
        TokenResponse: Access token e refresh token
    """
    # Verifica as credenciais
    user = await get_user_by_email(form_data.username)
    
    if not user:
        logger.error(f"Usuário não encontrado: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Debug: Log para verificar os valores (remover em produção)
    logger.info(f"Senha recebida: {form_data.password}")
    logger.info(f"Hash armazenado: {user['senha']}")
    
    if not verify_password(form_data.password, user["senha"]):
        logger.error(f"Falha na verificação de senha para {user['email']}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Cria os tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": user["email"]},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user["email"]},
        expires_delta=refresh_token_expires
    )
    
    logger.info(f"Login bem-sucedido para {user['email']}")
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.get("/me")
async def read_current_user(token: str = Depends(oauth2_scheme)):
    return {"user": token}