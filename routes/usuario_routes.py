from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
from database.database import (
    inserir_usuario,
    verificar_email_existente,
    excluir_usuario_por_id,
    excluir_usuario_por_email
)
from utils.exception_utils import handle_exceptions

router = APIRouter()

class UsuarioCreateRequest(BaseModel):
    nome: str
    email: str
    confirmar_email: str
    senha: str
    confirmar_senha: str
    role: str = "user"

@router.post("/usuario/")
@handle_exceptions
async def cadastrar_usuario(usuario: UsuarioCreateRequest = Body(...)):
    print("Dados recebidos:", usuario.dict())
    
    if usuario.email != usuario.confirmar_email:
        raise HTTPException(status_code=400, detail="Os e-mails não coincidem.")
    
    # Validação de senha
    if usuario.senha != usuario.confirmar_senha:
        raise HTTPException(status_code=400, detail="As senhas não coincidem.")
    
    # Verifica se o e-mail já existe
    if await verificar_email_existente(usuario.email):
        raise HTTPException(status_code=400, detail="Email já cadastrado.")
    
    # Insere o usuário (senha será hasheada no database.py)
    await inserir_usuario(usuario.nome, usuario.email, usuario.senha, usuario.role)
    return {"mensagem": "Usuário cadastrado com sucesso!"}

@router.delete("/usuario/{id}")
@handle_exceptions
async def deletar_usuario_por_id(id: int):
    await excluir_usuario_por_id(id)
    return {"mensagem": f"Usuário com id {id} excluído com sucesso!"}

@router.delete("/usuario/")
@handle_exceptions
async def deletar_usuario_por_email(email: str):
    await excluir_usuario_por_email(email)
    return {"mensagem": f"Usuário com email {email} excluído com sucesso!"}