from datetime import datetime
from fastapi import APIRouter, Query, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, Dict, List
import geopandas as gpd
import ee
import tempfile
import os
import aiofiles
import logging
from io import BytesIO
import zipfile

router = APIRouter()
logger = logging.getLogger(__name__)

class ShapefileProcessor:
    def __init__(self):
        ee.Initialize()
        
    async def validate_files(self, files: List[UploadFile]) -> bool:
        """
        Valida se todos os arquivos necessários do shapefile foram enviados
        
        :param files: Lista de arquivos enviados
        :return: True se válido, False caso contrário
        """
        required_extensions = {".shp", ".shx", ".dbf"}
        uploaded_extensions = {os.path.splitext(file.filename)[1].lower() for file in files}
        return required_extensions.issubset(uploaded_extensions)

    async def process_shapefile(self, files: List[UploadFile], start_date: str, end_date: str, cloud_filter: float) -> Dict:
        """
        Processa o shapefile e obtém imagem do Earth Engine
        
        :param files: Lista de arquivos do shapefile
        :param start_date: Data inicial
        :param end_date: Data final
        :param cloud_filter: Valor do filtro de nuvens
        :return: Dicionário com resultado do processamento
        """
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Salvar arquivos
                for file in files:
                    temp_file_path = os.path.join(temp_dir, file.filename)
                    async with aiofiles.open(temp_file_path, 'wb') as out_file:
                        content = await file.read()
                        await out_file.write(content)

                # Processar shapefile
                shp_file = next(f for f in files if f.filename.endswith('.shp'))
                shp_path = os.path.join(temp_dir, shp_file.filename)
                
                logger.info(f"Processando shapefile: {shp_file.filename}")
                gdf = gpd.read_file(shp_path)

                # Verificar e converter CRS se necessário
                if gdf.crs and gdf.crs != "EPSG:4326":
                    logger.info(f"Convertendo CRS de {gdf.crs} para EPSG:4326")
                    gdf = gdf.to_crs("EPSG:4326")

                bounds = gdf.total_bounds
                logger.info(f"Bounds do shapefile: {bounds}")

                # Criar região para Earth Engine
                region = ee.Geometry.Rectangle(
                    coords=[
                        float(bounds[0]),  # oeste
                        float(bounds[1]),  # sul
                        float(bounds[2]),  # leste
                        float(bounds[3])   # norte
                    ],
                    proj="EPSG:4326",
                    geodesic=False
                )

                # Obter imagem do Sentinel-2
                image_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                    .filterBounds(region) \
                    .filterDate(start_date, end_date) \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_filter)) \
                    .sort('CLOUDY_PIXEL_PERCENTAGE') \
                    .first()

                if image_collection is None:
                    return {
                        "status": 404,
                        "mensagem": "Nenhuma imagem encontrada para os parâmetros fornecidos",
                        "detalhes": {
                            "start_date": start_date,
                            "end_date": end_date,
                            "cloud_filter": cloud_filter,
                            "bounds": bounds.tolist()
                        }
                    }

                # Preparar download
                download_id = ee.data.getDownloadId({
                    'image': image_collection,
                    'region': region,
                    'scale': 10,
                    'format': 'GEO_TIFF',
                    'crs': 'EPSG:4326'
                })

                url = ee.data.makeDownloadUrl(download_id)
                return {"status": 200, "url": url}

        except Exception as e:
            logger.error(f"Erro no processamento do shapefile: {str(e)}")
            return {
                "status": 500,
                "mensagem": "Erro no processamento do shapefile",
                "detalhes": str(e)
            }

@router.post("/download_image/")
async def download_image(
    files: List[UploadFile] = File(...),
    data: str = Query(..., description="Duas datas no formato YYYY-MM-DD, separadas por vírgula"),
    filter: str = Query(..., description="Filtro no formato CLOUDY_PIXEL_PERCENTAGE,valor")
):
    """
    Endpoint para processar shapefile e baixar imagem do Earth Engine
    
    Args:
        files: Arquivos do shapefile (.shp, .shx, .dbf, etc)
        data: Duas datas no formato YYYY-MM-DD, separadas por vírgula
        filter: Filtro no formato CLOUDY_PIXEL_PERCENTAGE,valor
    
    Returns:
        Arquivo ZIP contendo a imagem processada ou mensagem de erro apropriada
    """
    try:
        # Validar datas
        data_lista = data.split(',')
        if len(data_lista) != 2:
            raise HTTPException(
                status_code=400,
                detail="O parâmetro 'data' deve conter exatamente duas datas separadas por vírgula"
            )

        start_date, end_date = data_lista

        # Validar filtro
        if not filter.startswith("CLOUDY_PIXEL_PERCENTAGE,"):
            raise HTTPException(
                status_code=400,
                detail="O filtro deve estar no formato 'CLOUDY_PIXEL_PERCENTAGE,valor'"
            )
        
        try:
            _, cloud_filter_value = filter.split(',')
            cloud_filter_value = float(cloud_filter_value)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="O valor do filtro de nuvens deve ser um número"
            )

        # Processar shapefile
        processor = ShapefileProcessor()
        
        # Validar arquivos
        if not await processor.validate_files(files):
            raise HTTPException(
                status_code=400,
                detail="Arquivos do shapefile incompletos. Necessário .shp, .shx e .dbf"
            )

        # Processar dados
        result = await processor.process_shapefile(files, start_date, end_date, cloud_filter_value)

        if result["status"] != 200:
            return JSONResponse(
                status_code=result["status"],
                content={"detail": result["mensagem"], "parameters": result["detalhes"]}
            )

        # Download e empacotamento da imagem
        async with aiohttp.ClientSession() as session:
            async with session.get(result["url"]) as response:
                if response.status == 200:
                    image_data = await response.read()
                    
                    # Criar ZIP
                    zip_buffer = BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        zip_file.writestr("image.tif", image_data)

                    zip_buffer.seek(0)
                    
                    return StreamingResponse(
                        zip_buffer,
                        media_type="application/zip",
                        headers={
                            "Content-Disposition": f"attachment; filename=image_{start_date}_{end_date}.zip"
                        }
                    )
                else:
                    raise HTTPException(status_code=500, detail="Erro ao baixar a imagem")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Erro interno: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"message": "Erro interno do servidor", "error": str(e)}
        )