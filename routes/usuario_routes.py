from fastapi import APIRouter, HTTPException, Body, Depends, status
from pydantic import BaseModel, EmailStr, field_validator
from typing import Annotated
from database.database import (
    inserir_usuario,
    verificar_email_existente,
    excluir_usuario_por_id,
    excluir_usuario_por_email,
    get_user_by_email
)
from auth.dependencies import get_current_user, require_role
from auth.models import Role
from auth.security import get_password_hash, verify_password
from utils.exception_utils import handle_exceptions


router = APIRouter(prefix="/usuarios", tags=["Usuários"])

# Modelos Pydantic com validações
class UsuarioBase(BaseModel):
    nome: str
    email: EmailStr

class UsuarioCreate(UsuarioBase):
    confirmar_email: EmailStr
    senha: str
    confirmar_senha: str
    role: Role = Role.USER

    @field_validator('senha')
    def validar_senha(cls, v):
        if len(v) < 8:
            raise ValueError("A senha deve ter pelo menos 8 caracteres")
        return v

    @field_validator('confirmar_email')
    def emails_coincidem(cls, v, values):
        if 'email' in values.data and v != values.data['email']:
            raise ValueError("Os e-mails não coincidem")
        return v

    @field_validator('confirmar_senha')
    def senhas_coincidem(cls, v, values):
        if 'senha' in values.data and v != values.data['senha']:
            raise ValueError("As senhas não coincidem")
        return v

class UsuarioResponse(UsuarioBase):
    role: Role

# Rotas
@router.get("/me", response_model=UsuarioResponse)
async def obter_usuario_atual(
    current_user: Annotated[dict, Depends(get_current_user)]
):
    """Obtém os dados do usuário logado"""
    return {
        "nome": current_user["nome"],
        "email": current_user["email"],
        "role": current_user["role"]
    }

@router.post(
    "/",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    # dependencies=[Depends(require_role(Role.ADMIN))]  # Apenas admin pode criar usuários
)
@handle_exceptions
async def criar_usuario(usuario: UsuarioCreate):
    """
    Cria um novo usuário no sistema.
    
    Requer privilégios de administrador.
    """
    if await verificar_email_existente(usuario.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )

    hashed_password = get_password_hash(usuario.senha)
    
    await inserir_usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha=hashed_password,
        role=usuario.role
    )
    
    return UsuarioResponse(
        nome=usuario.nome,
        email=usuario.email,
        role=usuario.role
    )

@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(Role.ADMIN))]
)
@handle_exceptions
async def deletar_usuario(id: int):
    """
    Remove um usuário pelo ID.
    
    Requer privilégios de administrador.
    """
    await excluir_usuario_por_id(id)

@router.delete(
    "/",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(Role.ADMIN))]
)
@handle_exceptions
async def deletar_usuario_por_email(email: EmailStr):
    """
    Remove um usuário pelo email.
    
    Requer privilégios de administrador.
    """
    await excluir_usuario_por_email(email)