from datetime import datetime
from fastapi import HTTPException, status
from auth.config import settings
from auth.security import create_access_token, create_refresh_token
from auth.models import TokenResponse
from database.database import get_user_by_email, verify_password

class AuthService:
    def __init__(self):
        self.login_attempts = {}  # Em produção, use Redis

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await get_user_by_email(email)
        if not user or not verify_password(password, user["senha"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciais inválidas"
            )

        scopes = ["user"]
        if user["role"] == "admin":
            scopes.append("admin")

        return TokenResponse(
            access_token=create_access_token(email, scopes),
            refresh_token=create_refresh_token(email)
        )