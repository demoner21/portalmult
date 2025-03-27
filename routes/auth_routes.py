from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from auth.models import TokenResponse
from database.database import get_user_by_email
from auth.security import (
    create_access_token,
    create_refresh_token,
    PWD_CONTEXT
)
from auth.config import settings
import logging
from passlib.exc import UnknownHashError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

def verify_password_debug(plain_password: str, hashed_password: str) -> bool:
    """Função de verificação com logs detalhados"""
    try:
        logger.debug(f"Verificando senha: {plain_password[:2]}...")
        logger.debug(f"Hash recebido: {hashed_password[:10]}...")
        
        result = PWD_CONTEXT.verify(plain_password.strip(), hashed_password)
        
        logger.debug(f"Resultado verificação: {result}")
        return result
        
    except UnknownHashError:
        logger.error("Formato de hash desconhecido!")
        return False
    except Exception as e:
        logger.error(f"Erro na verificação: {str(e)}", exc_info=True)
        return False

@router.post("/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint de login com tratamento completo de erros"""
    try:
        # 1. Obter usuário
        user = await get_user_by_email(form_data.username)
        if not user:
            logger.error(f"Usuário não encontrado: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 2. Logs detalhados
        logger.info(f"Tentativa login: {user['email']}")
        logger.debug(f"Hash completo: {user['senha']}")
        logger.debug(f"Config PWD_CONTEXT: {PWD_CONTEXT.to_dict()}")

        # 3. Verificação de senha
        if not verify_password_debug(form_data.password, user["senha"]):
            # Debug avançado
            from passlib.hash import bcrypt
            logger.error("FALHA NA VERIFICAÇÃO - TESTE MANUAL:")
            logger.error(f"Senha testada: {form_data.password}")
            logger.error(f"Hash no banco: {user['senha']}")
            logger.error(f"Teste manual: {bcrypt.verify(form_data.password, user['senha'])}")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 4. Geração de tokens
        tokens = TokenResponse(
            access_token=create_access_token(user["email"]),
            refresh_token=create_refresh_token(user["email"]),
            token_type="bearer"
        )
        
        logger.info(f"Login OK: {user['email']}")
        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ERRO: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno no servidor"
        )

@router.get("/me")
async def read_current_user(token: str = Depends(oauth2_scheme)):
    return {"user": token}