import asyncpg

from fastapi import APIRouter, HTTPException
from database.database import (
    inserir_usuario,
    verificar_email_existente,
    excluir_usuario_por_id,
    excluir_usuario_por_email
)

router = APIRouter()

@router.post("/usuario/")
async def cadastrar_usuario(
    nome: str, 
    email: str, 
    confirmar_email: str,  # Novo campo para confirmação de e-mail
    senha: str, 
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

        # Insere o usuário
        await inserir_usuario(nome, email, senha, role)
        return {"mensagem": "Usuário cadastrado com sucesso!"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao cadastrar usuário: {str(e)}")

@router.delete("/usuario/{id}")
async def deletar_usuario_por_id(id: int):
    try:
        await excluir_usuario_por_id(id)
        return {"mensagem": f"Usuário com id {id} excluído com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao excluir usuário: {str(e)}")

@router.delete("/usuario/")
async def deletar_usuario_por_email(email: str):
    try:
        await excluir_usuario_por_email(email)
        return {"mensagem": f"Usuário com email {email} excluído com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao excluir usuário: {str(e)}")