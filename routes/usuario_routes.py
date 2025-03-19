import asyncpg

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from database.database import get_user_by_email, verify_password
from utils.jwt_utils import create_access_token, get_current_user
from datetime import timedelta

from fastapi import APIRouter, HTTPException
from database.database import (
    inserir_usuario,
    verificar_email_existente,
    excluir_usuario_por_id,
    excluir_usuario_por_email
)

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user_by_email(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user["senha"]):  # Remova o await
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/usuario/")
async def cadastrar_usuario(
    nome: str,
    email: str,
    confirmar_email: str,  # Novo campo para confirmação de e-mail
    senha: str,
    confirmar_senha: str,
    role: str = "user"
):
    try:
        # Verifica se os e-mails são iguais
        if email != confirmar_email:
            raise HTTPException(
                status_code=400,
                detail="Os e-mails não coincidem."
            )

        # Verifica se o email já existe
        if await verificar_email_existente(email):
            raise HTTPException(
                status_code=400,
                detail="Email já cadastrado."
            )

                # Verifica se as senhas são iguais
        if senha != confirmar_senha:
            raise HTTPException(
                status_code=400,
                detail="As Senhas não coincidem."
            )

        # Insere o usuário
        await inserir_usuario(nome, email, senha, role)
        return {"mensagem": "Usuário cadastrado com sucesso!"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Erro ao cadastrar usuário: {str(e)}")


@router.delete("/usuario/{id}")
async def deletar_usuario_por_id(id: int):
    try:
        await excluir_usuario_por_id(id)
        return {"mensagem": f"Usuário com id {id} excluído com sucesso!"}
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Erro ao excluir usuário: {str(e)}")

@router.get("/usuario/")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return current_user

@router.delete("/usuario/")
async def deletar_usuario_por_email(email: str):
    try:
        await excluir_usuario_por_email(email)
        return {"mensagem": f"Usuário com email {email} excluído com sucesso!"}
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Erro ao excluir usuário: {str(e)}")
