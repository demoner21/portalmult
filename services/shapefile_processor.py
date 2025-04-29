import ee
import uuid
from pathlib import Path
import geopandas as gpd
from pathlib import Path
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, UploadFile
import logging
from tempfile import TemporaryDirectory
import shutil
from shapely.geometry import shape
import json

logger = logging.getLogger(__name__)

class ShapefileProcessor:
    @staticmethod
    async def process_uploaded_files(files: Dict[str, UploadFile]) -> Tuple[ee.Geometry, Dict]:
        """
        Processa arquivos de shapefile enviados e retorna uma geometria do Earth Engine e metadados.
        
        Args:
            files: Dicionário com os arquivos do shapefile (ex: {"shp": UploadFile, "shx": UploadFile})
        
        Returns:
            Tuple[ee.Geometry, Dict]: Geometria no formato EE e metadados dos arquivos.
        """
        temp_dir = Path(f"temp_shapefile_{uuid.uuid4().hex}")
        try:
            temp_dir.mkdir(exist_ok=True)
            
            # Salva os arquivos temporariamente
            saved_files = {}
            for file_type, file in files.items():
                if file is not None:
                    file_path = temp_dir / file.filename
                    with open(file_path, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)
                    saved_files[file_type] = file.filename
            
            # Valida arquivos mínimos (.shp, .shx, .dbf)
            required_files = ["shp", "shx", "dbf"]
            if not all(f in saved_files for f in required_files):
                raise HTTPException(
                    status_code=400,
                    detail="Arquivos obrigatórios faltando: .shp, .shx, .dbf"
                )
            
            # Extrai geometria
            shp_path = temp_dir / saved_files["shp"]
            geometry = await ShapefileProcessor.extract_geometry(shp_path)
            
            return geometry, {
                "arquivos_enviados": saved_files,
                "nome_arquivo_original": saved_files["shp"]
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @staticmethod
    async def extract_geometry(shp_path: Path) -> ee.Geometry:
        """Extrai geometria e converte para formato compatível."""
        try:
            gdf = gpd.read_file(shp_path)
            if gdf.empty:
                raise ValueError("Shapefile está vazio")

            gdf_wgs84 = gdf.to_crs('EPSG:4326')
            geojson = gdf_wgs84.__geo_interface__

            # Convertemos para Shapely primeiro para validação
            shapely_geom = shape(geojson['features'][0]['geometry'])

            # Retorna tanto a geometria do EE quanto WKT para validação
            return {
                "ee_geometry": ee_geom,
                "wkt": wkt_geom,
                "type": geom_type
            }, {
                "arquivos_enviados": {
                    "shp": files["shp"].filename,
                    "shx": files["shx"].filename,
                    "dbf": files["dbf"].filename,
                    "cpg": files.get("cpg", "").filename if files.get("cpg") else None,
                    "prj": files.get("prj", "").filename if files.get("prj") else None
                },
                "nome_arquivo_original": files["shp"].filename
            }

        except Exception as e:
            logger.error(f"Erro ao extrair geometria: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Geometria inválida: {str(e)}")