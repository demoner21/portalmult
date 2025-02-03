import pytest
import httpx
import os

PREDICTION_URL = "http://localhost:8000/predict/"

@pytest.mark.asyncio
async def test_process_directory_successful():
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        # Diretório com dados presentes
        present_data_dir = "./present_data"

        # Verifica se o diretório existe e não está vazio
        if not os.path.isdir(present_data_dir):
            pytest.fail(f"Erro: O diretório {present_data_dir} não existe")
        if not os.listdir(present_data_dir):
            pytest.fail(f"Aviso: O diretório {present_data_dir} está vazio")

        # Prepara os arquivos para enviar
        files = [
            ("files", open(os.path.join(present_data_dir, f"Sentinel_B{i}.tif"), "rb"))
            for i in range(1, 13)
        ]
        files.extend([
            ("files", open(os.path.join(present_data_dir, "NDVI.tif"), "rb")),
            ("files", open(os.path.join(present_data_dir, "NDWI.tif"), "rb")),
            ("files", open(os.path.join(present_data_dir, "SAVI.tif"), "rb")),
            ("files", open(os.path.join(present_data_dir, "BSI.tif"), "rb")),
        ])

        # Faz a requisição POST
        response = await client.post(PREDICTION_URL, files=files)

        # Verifica a resposta
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        # Fecha os arquivos abertos
        for _, file in files:
            file.close()

@pytest.mark.asyncio
async def test_process_directory_empty():
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        # Diretório vazio
        empty_data_dir = "./absent_data"

        # Verifica se o diretório existe
        if not os.path.isdir(empty_data_dir):
            pytest.fail(f"Erro: O diretório {empty_data_dir} não existe")

        # Tenta processar o diretório vazio
        response = await client.post(PREDICTION_URL, files=[])

        # Verifica a resposta
        assert response.status_code == 400  # Ou outro código de erro apropriado
