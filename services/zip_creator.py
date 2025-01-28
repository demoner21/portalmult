# utils/zip_creator.py
import os
import zipfile
import logging
from io import BytesIO
import asyncio
from typing import List  # Adicione esta linha

logger = logging.getLogger(__name__)

class ZipCreator:
    async def create_zip_file(self, files: List[str]) -> BytesIO:
        """
        Cria um arquivo ZIP a partir de uma lista de arquivos.

        Args:
            files: Lista de caminhos dos arquivos a serem compactados.

        Returns:
            BytesIO: Buffer contendo o arquivo ZIP.
        """
        try:
            zip_buffer = BytesIO()
            seen_files = set()
    
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for root, _, file_list in os.walk("./"):
                    for file in file_list:
                        if file.endswith(".tif") and file not in seen_files:
                            file_path = os.path.join(root, file)
                            zip_file.write(
                                file_path, os.path.relpath(file_path, "./"))
                            seen_files.add(file)
    
            zip_buffer.seek(0)
            
            # Deletar os arquivos após 5 segundos
            await asyncio.sleep(5)
            for file in files:
                try:
                    os.remove(file)
                    logger.info(f"Arquivo {file} excluído.")
                except Exception as e:
                    logger.error(f"Erro ao excluir o arquivo {file}: {str(e)}")

            # Deletar quaisquer outros arquivos remanescentes
            for root, dirs, remaining_files in os.walk("./"):
                for file in remaining_files:
                    if file.endswith(".tif"):
                        file_path = os.path.join(root, file)
                        try:
                            os.remove(file_path)
                            logger.info(f"Arquivo {file_path} excluído.")
                        except Exception as e:
                            logger.error(f"Erro ao excluir o arquivo {file_path}: {str(e)}")

            return zip_buffer

        except Exception as e:
            logger.error(
                f"Erro ao criar o arquivo ZIP: {str(e)}", exc_info=True)
            raise