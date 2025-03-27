from database.database import get_password_hash, verify_password

senha = "Senhazero1!"
hash_novo = get_password_hash(senha)  # Agora deve funcionar
print(f"Hash gerado: {hash_novo}")
print(f"Verificação: {verify_password(senha, hash_novo)}")  # Deve retornar True