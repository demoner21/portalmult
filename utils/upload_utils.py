import uuid
from pathlib import Path
import shutil
from fastapi import HTTPException, UploadFile
from typing import List

def save_uploaded_files(files: List[UploadFile]) -> Path:
    """
    Salva todos os arquivos do shapefile (.shp, .shx, .dbf, etc.) em um diretório temporário único.
    
    Args:
        files: Lista de arquivos do tipo UploadFile.
    
    Returns:
        Path: Caminho do diretório temporário.
    """
    try:
        # Criar diretório temporário com nome único
        temp_dir = Path(f"temp_shapefile_{uuid.uuid4().hex}")
        temp_dir.mkdir(exist_ok=True, parents=True)

        # Salvar todos os arquivos
        for file in files:
            if file is not None:  # Verifica se o arquivo foi fornecido
                file_path = temp_dir / file.filename
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

        return temp_dir

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar os arquivos: {str(e)}")

def cleanup_temp_files(temp_dir: Path):
    """
    Remove os arquivos temporários após o processamento.
    """
    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
    except Exception as e:
        # Logar o erro mas não interromper o fluxo principal
        import logging
        logging.error(f"Erro ao limpar arquivos temporários: {str(e)}")