from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, Dict  
from middleware.request_queue import RequestQueue
from utils.validators import *
from services.earth_engine_processor import EarthEngineProcessor
from services.zip_creator import ZipCreator
import logging

router = APIRouter()

logger = logging.getLogger(__name__)


class ImprovedEarthEngineProcessor:
    def __init__(self):
        self.request_queue = RequestQueue()

    async def process_data_with_queue(self, parameters: Dict):
        """
        Processa dados do Earth Engine com controle de fila
        
        :param parameters: Dicionário com parâmetros da requisição
        :return: Resultado do processamento ou resposta de erro
        """
        # Gera uma chave única baseada nos parâmetros principais
        request_key = f"{parameters['latitude']}_{parameters['longitude']}_{parameters['data'][0]}_{parameters['data'][1]}"
        
        # Verifica se pode processar a requisição
        if not await self.request_queue.can_process_request(request_key):
            return {
                "status": 429,  # Too Many Requests
                "mensagem": "Muitas requisições para o mesmo ponto em um curto intervalo",
                "detalhes": parameters
            }
        
        # Processa os dados do Earth Engine (similar ao método original)
        earth_engine_processor = EarthEngineProcessor()
        return await earth_engine_processor.process_data(parameters)

@router.get("/get_map")
async def get_map(
    latitude: float = Query(..., description="Latitude (-90 a 90)", ge=-90, le=90),
    longitude: float = Query(..., description="Longitude (-180 a 180)", ge=-180, le=180),
    data: str = Query(..., description="Duas datas no formato YYYY-MM-DD, separadas por vírgula"),
    filter: Optional[str] = Query(None, description="Filtro no formato CLOUDY_PIXEL_PERCENTAGE,valor")
):
    """
    Obtém dados de imagens de satélite para uma localização específica com controle de taxa.
    
        Args:
        latitude: Latitude do ponto central (-90 a 90)
        longitude: Longitude do ponto central (-180 a 180)
        data: Duas datas no formato YYYY-MM-DD, separadas por vírgula
        filter: Filtro opcional no formato CLOUDY_PIXEL_PERCENTAGE,valor

    Returns:
        Arquivo ZIP contendo as bandas processadas ou mensagem de erro apropriada
    """
    try:
        # Validar formato das datas
        data_lista = data.split(',')
        if len(data_lista) != 2:
            raise HTTPException(
                status_code=400,
                detail="O parâmetro 'data' deve conter exatamente duas datas separadas por vírgula"
            )

        # Validar formato do filtro
        if filter and not filter.startswith("CLOUDY_PIXEL_PERCENTAGE,"):
            raise HTTPException(
                status_code=400,
                detail="O filtro deve estar no formato 'CLOUDY_PIXEL_PERCENTAGE,valor'"
            )

        # Log sem argumentos nomeados
        logger.info(
            f"Recebendo requisição: lat={latitude}, lon={longitude}, data={data}, filter={filter}"
        )

        parameters = {
            "latitude": latitude,
            "longitude": longitude,
            "data": data_lista,
            "filter": filter
        }

        # Processar os dados do Earth Engine com controle de fila
        improved_processor = ImprovedEarthEngineProcessor()
        processing_result = await improved_processor.process_data_with_queue(parameters)

        # Tratamento de resultado com controle de fila
        if isinstance(processing_result, dict) and processing_result.get("status") == 429:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": processing_result["mensagem"],
                    "parameters": processing_result["detalhes"]
                }
            )

        # Processamento similar ao método original
        s3_bands, prediction_result = processing_result

        # Verificar se não encontrou imagens
        if s3_bands is None and isinstance(prediction_result, dict) and prediction_result.get("status") == 404:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": prediction_result["mensagem"],
                    "parameters": prediction_result["detalhes"]
                }
            )

        # Verificar se s3_bands está vazio por outras razões
        if not s3_bands:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": "Nenhuma imagem encontrada ou erro no processamento.",
                    "parameters": parameters
                }
            )

        try:
            # Criar o arquivo ZIP
            zip_creator = ZipCreator()
            zip_buffer = await zip_creator.create_zip_file(s3_bands)

            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={
                    'Content-Disposition': f'attachment; filename="sentinel_{parameters["latitude"]}_{parameters["longitude"]}.zip"'
                }
            )

        except Exception as zip_error:
            # Log sem argumentos nomeados
            logger.error(f"Erro ao criar arquivo ZIP: {str(zip_error)}")
            raise HTTPException(
                status_code=500,
                detail="Erro ao criar arquivo ZIP com os resultados"
            )

    except HTTPException as he:
        raise he
    except Exception as e:
        # Log sem argumentos nomeados
        logger.error(f"Erro interno: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Erro interno do servidor",
                "error": str(e)
            }
        )