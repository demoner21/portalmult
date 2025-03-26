from enum import Enum
from pydantic import BaseModel

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    ANALYST = "analyst"

class TokenData(BaseModel):
    email: str
    scopes: list[str] = []

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"