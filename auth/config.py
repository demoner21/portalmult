from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional

class AuthSettings(BaseSettings):
    # Configurações JWT
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCK_TIME_MINUTES: int = 15
    
    # Configurações do Banco de Dados (adicione se necessário)
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_NAME: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[str] = None
    
    # Configurações adicionais JWT (se necessário)
    JWT_ISSUER: Optional[str] = None
    JWT_AUDIENCE: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"  # Isso ignora variáveis extras no .env

settings = AuthSettings()