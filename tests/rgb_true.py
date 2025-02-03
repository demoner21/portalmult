import pytest
import httpx

VISUALIZE_URL = "http://127.0.0.1:8000/visualize/?rgb_image=True"

@pytest.mark.asyncio
async def test_visualize_rgb_image_successful():
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        # Prepara os arquivos para enviar
        files = [
            ("files", open("Sentinel_B4.tif", "rb")),
            ("files", open("Sentinel_B3.tif", "rb")),
            ("files", open("Sentinel_B2.tif", "rb")),
        ]

        # Faz a requisição POST
        response = await client.post(VISUALIZE_URL, files=files)

        # Verifica a resposta
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        # Salva a imagem de saída
        with open("output_image.png", "wb") as f:
            f.write(response.content)

        # Fecha os arquivos abertos
        for _, file in files:
            file.close()

@pytest.mark.asyncio
async def test_visualize_rgb_image_missing_files():
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        # Tenta enviar sem arquivos
        response = await client.post(VISUALIZE_URL, files=[])

        # Verifica a resposta
        assert response.status_code == 422  # Código esperado para entidade não processável