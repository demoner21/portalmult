from fastapi import APIRouter, HTTPException, Query, Body
from database.database import (
    inserir_usuario,
    verificar_email_existente,
    excluir_usuario_por_id,
    excluir_usuario_por_email
)
from utils.exception_utils import handle_exceptions

router = APIRouter()

@router.post("/usuario/")
@handle_exceptions
async def cadastrar_usuario(
    nome: str,
    email: str,
    confirmar_email: str,
    senha: str,
    confirmar_senha: str,
    role: str = "user",
#    nome: str = Query(..., description="Nome do usuário"),
#    email: str = Query(..., description="Email do usuário"),
#    confirmar_email: str = Query(..., description="Confirmação do email"),
#    senha: str = Query(..., description="Senha do usuário"),
#    confirmar_senha: str = Query(..., description="Confirmação da senha"),
#    role: str = Query("user", description="Papel do usuário (padrão: 'user')")
):
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
            detail="As senhas não coincidem."
        )

    # Insere o usuário
    await inserir_usuario(nome, email, senha, role)
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