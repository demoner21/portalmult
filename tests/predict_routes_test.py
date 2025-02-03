import os
import requests
import pytest
from unittest import mock
from io import BytesIO


# Função que envia os arquivos para o endpoint de predição
def process_directory(dir_path, output_file):
    prediction_url = "http://localhost:8000/predict/"
    files = {
        "files": [
            (f"{band}.tif", open(os.path.join(dir_path, f"{band}.tif"), "rb"))
            for band in [
                "Sentinel_B1", "Sentinel_B2", "Sentinel_B3", "Sentinel_B4",
                "Sentinel_B5", "Sentinel_B6", "Sentinel_B7", "Sentinel_B8",
                "Sentinel_B8A", "Sentinel_B9", "Sentinel_B11", "Sentinel_B12",
                "NDVI", "NDWI", "SAVI", "BSI"
            ]
        ]
    }

    response = requests.post(prediction_url, files=files)
    
    if response.status_code == 200:
        with open(output_file, "w") as f:
            f.write(response.text)


# Teste utilizando pytest
@pytest.fixture
def mock_response():
    """Mocka a resposta do servidor para a requisição POST"""
    mock_resp = mock.Mock()
    mock_resp.status_code = 200
    mock_resp.text = '{"result": "success"}'
    return mock_resp


def test_process_directory(mock_response):
    """Teste da função de processamento de diretório"""
    with mock.patch("requests.post", return_value=mock_response):
        # Diretório fictício para testes
        test_dir = "test_data"
        os.makedirs(test_dir, exist_ok=True)
        
        # Criação de arquivos de teste
        for band in [
            "Sentinel_B1", "Sentinel_B2", "Sentinel_B3", "Sentinel_B4",
            "Sentinel_B5", "Sentinel_B6", "Sentinel_B7", "Sentinel_B8",
            "Sentinel_B8A", "Sentinel_B9", "Sentinel_B11", "Sentinel_B12",
            "NDVI", "NDWI", "SAVI", "BSI"
        ]:
            with open(os.path.join(test_dir, f"{band}.tif"), "wb") as f:
                f.write(b"fake_data")

        output_file = "test_output.json"
        
        # Chamando a função que processa o diretório
        process_directory(test_dir, output_file)
        
        # Verifica se o arquivo de saída foi criado com o conteúdo esperado
        with open(output_file, "r") as f:
            content = f.read()
            assert content == '{"result": "success"}'
        
        # Limpeza dos arquivos de teste
        for band in [
            "Sentinel_B1", "Sentinel_B2", "Sentinel_B3", "Sentinel_B4",
            "Sentinel_B5", "Sentinel_B6", "Sentinel_B7", "Sentinel_B8",
            "Sentinel_B8A", "Sentinel_B9", "Sentinel_B11", "Sentinel_B12",
            "NDVI", "NDWI", "SAVI", "BSI"
        ]:
            os.remove(os.path.join(test_dir, f"{band}.tif"))
        os.remove(output_file)
        os.rmdir(test_dir)

