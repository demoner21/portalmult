from datetime import timedelta, datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.orm import status
from database import SessionLocal
from models import Users
from passlib.context import CryptContext
from fastapi.secusity import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
import os

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

SECRECT_KEY='testanto'
ALGORITHM='HS256'

PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class CreateUserRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency,
                      create_user_request:CreateUserRequest):
    create_user_model = Users(
        username=create_user_request.username,
        hashed_password=bcrypt_context.hash(create_user_request.password),
    )

    db.add(create_user_model)
    db.commit()


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
                                 db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail='Could not validade user.')
    token = create_access_token(user.username, user.id, timedelta(minutes=20))

    return {'access_token': token, 'token_type': 'bearer'}


def authenticate_user(username: str, password: str, db):
    user = db.query(Users.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.now() + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRECT_KEY, algorithm=ALGORITHM)
    
async def get_current_user(token: Annotated[]str, Depends(oauth2_bearer)):
    try:
        payload = jwt.decode(token, SECRECT_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: payload.get('id')
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                               detail='Could not validade user.')
        return {'username': username, 'id': user_id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                           detail='Could not validade user.')

#from fastapi import APIRouter, Depends, HTTPException, status
#from fastapi.security import OAuth2PasswordRequestForm
#from database.database import get_user_by_email
#from auth.security import (
#    verify_password,
#    create_access_token,
#    create_refresh_token,
#    oauth2_scheme
#)
#from auth.models import TokenResponse  # Importação adicionada
#import logging
#
## Configure logger
#auth_logger = logging.getLogger('auth_routes')
#auth_logger.setLevel(logging.DEBUG)
#
#router = APIRouter(prefix="/auth", tags=["Auth"])
#
#@router.post("/token", response_model=TokenResponse)
#async def login(form_data: OAuth2PasswordRequestForm = Depends()):
#    auth_logger.info(f"Login attempt for: {form_data.username}")
#    
#    try:
#        # Get user from database
#        user = await get_user_by_email(form_data.username)
#        
#        if not user:
#            auth_logger.warning(f"User not found: {form_data.username}")
#            raise HTTPException(
#                status_code=status.HTTP_401_UNAUTHORIZED,
#                detail="Invalid credentials",
#                headers={"WWW-Authenticate": "Bearer"},
#            )
#
#        # Enhanced logging
#        auth_logger.debug(f"User found - ID: {user.get('id')}, Email: {user.get('email')}")
#        auth_logger.debug(f"Stored hash: {user.get('senha')[:10]}...")
#
#        # Password verification with cleaned inputs
#        password_match = verify_password(
#            plain_password=form_data.password,
#            hashed_password=user['senha']
#        )
#        
#        auth_logger.info(f"Password verification result: {password_match}")
#        
#        if not password_match:
#            auth_logger.warning("Password verification failed")
#            raise HTTPException(
#                status_code=status.HTTP_401_UNAUTHORIZED,
#                detail="Invalid credentials",
#                headers={"WWW-Authenticate": "Bearer"},
#            )
#
#        # Determine scopes based on role
#        scopes = ["user"]
#        if user.get("role") == "admin":
#            scopes.append("admin")
#
#        # Generate tokens
#        tokens = TokenResponse(
#            access_token=create_access_token(user["email"], scopes=scopes),
#            refresh_token=create_refresh_token(user["email"]),
#            token_type="bearer"
#        )
#        
#        auth_logger.info(f"Successful login for: {user['email']}")
#        return tokens
#
#    except HTTPException:
#        raise
#    except Exception as e:
#        auth_logger.error(f"Login error: {str(e)}", exc_info=True)
#        raise HTTPException(
#            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#            detail="Internal server error"
#        )
#
#@router.get("/me")
#async def read_current_user(token: str = Depends(oauth2_scheme)):
#    return {"user": token}