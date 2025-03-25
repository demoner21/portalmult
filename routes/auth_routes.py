from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from database.database import get_user_by_email, verify_password
from security.auth import (
    create_access_token, 
    create_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from datetime import timedelta
from pydantic import BaseModel

router = APIRouter(tags=["autenticação"])

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["senha"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    return {
        "access_token": create_access_token(
            data={"sub": user["email"]}, 
            expires_delta=access_token_expires
        ),
        "refresh_token": create_refresh_token(
            data={"sub": user["email"]},
            expires_delta=refresh_token_expires
        ),
        "token_type": "bearer"
    }

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    return await refresh_access_token(refresh_token)