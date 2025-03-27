from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from auth.config import settings
import secrets

PWD_CONTEXT = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def get_password_hash(password: str) -> str:
    """Gera um hash seguro para a senha usando bcrypt"""
    return PWD_CONTEXT.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    return PWD_CONTEXT.verify(plain_password, hashed_password)

def create_token(
    data: dict,
    expires_delta: timedelta,
    token_type: str,
    scopes: list[str] = None
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    
    payload = {
        **to_encode,
        "exp": expire,
        "type": token_type,
        "jti": secrets.token_hex(16),  # Identificador único
        "iat": datetime.now(timezone.utc),
        "scopes": scopes or []
    }
    
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

def create_access_token(email: str, scopes: list[str] = None) -> str:
    return create_token(
        {"sub": email},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "access",
        scopes
    )

def create_refresh_token(email: str) -> str:
    return create_token(
        {"sub": email},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "refresh"
    )
