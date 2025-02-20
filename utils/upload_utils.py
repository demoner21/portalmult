from pathlib import Path
import shutil
from fastapi import HTTPException, UploadFile

def save_uploaded_files(shapefile: UploadFile, shxfile: UploadFile, dbffile: UploadFile) -> Path:
    """
    Salva os arquivos .shp, .shx e .dbf em um diretório temporário e retorna o caminho do diretório.
    """
    try:
        # Criar diretório temporário
        temp_dir = Path("temp_shapefile")
        temp_dir.mkdir(exist_ok=True)

        # Salvar os arquivos
        shapefile_path = temp_dir / shapefile.filename
        shxfile_path = temp_dir / shxfile.filename
        dbffile_path = temp_dir / dbffile.filename

        with open(shapefile_path, "wb") as buffer:
            shutil.copyfileobj(shapefile.file, buffer)
        with open(shxfile_path, "wb") as buffer:
            shutil.copyfileobj(shxfile.file, buffer)
        with open(dbffile_path, "wb") as buffer:
            shutil.copyfileobj(dbffile.file, buffer)

        return temp_dir

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar os arquivos: {str(e)}")

def cleanup_temp_files(temp_dir: Path):
    """
    Remove os arquivos temporários após o processamento.
    """
    if temp_dir.exists():
        shutil.rmtree(temp_dir)