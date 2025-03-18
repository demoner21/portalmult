from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
import httpx

# Configurações do Keycloak
KEYCLOAK_URL = "http://localhost:8080/realms/spin-realm"
CLIENT_ID = "spin-client"
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