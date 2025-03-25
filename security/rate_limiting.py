from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter
from slowapi.util import get_remote_address
import time

limiter = Limiter(key_func=get_remote_address)
token_bucket = {}

class RateLimitingBearer(HTTPBearer):
    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials.scheme != "Bearer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esquema de autenticação inválido"
            )
        
        # Implementação simples de token bucket
        ip = get_remote_address(request)
        now = time.time()
        
        if ip not in token_bucket:
            token_bucket[ip] = {"tokens": 10, "last_check": now}
        else:
            elapsed = now - token_bucket[ip]["last_check"]
            token_bucket[ip]["tokens"] += elapsed * 2  # 2 tokens por segundo
            token_bucket[ip]["last_check"] = now
            if token_bucket[ip]["tokens"] > 10:
                token_bucket[ip]["tokens"] = 10
        
        if token_bucket[ip]["tokens"] < 1:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas requisições"
            )
        
        token_bucket[ip]["tokens"] -= 1
        return credentials.credentials