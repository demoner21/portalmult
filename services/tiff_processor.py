import rasterio
from rasterio.features import bounds as feature_bounds
from shapely.geometry import shape, Polygon
import json
import logging
from typing import Dict, Tuple
from database.database import with_db_connection

logger = logging.getLogger(__name__)

class TiffProcessor:
    @staticmethod
    def extract_geometry_from_tiff(tiff_path: str) -> Tuple[Dict, Dict]:
        """
        Extrai geometria e metadados de um arquivo TIFF
        
        Args:
            tiff_path: Caminho para o arquivo TIFF
            
        Returns:
            Tuple (geometria como GeoJSON, metadados)
        """
        try:
            with rasterio.open(tiff_path) as src:
                # Extrai bounding box
                bbox = feature_bounds(src)
                
                # Cria polígono a partir do bbox
                geom = Polygon([
                    [bbox[0], bbox[1]],
                    [bbox[2], bbox[1]],
                    [bbox[2], bbox[3]],
                    [bbox[0], bbox[3]],
                    [bbox[0], bbox[1]]
                ])
                
                # Converte para GeoJSON
                geojson_geom = json.loads(json.dumps(shape(geom).__geo_interface__))
                
                # Extrai metadados importantes
                metadata = {
                    "crs": str(src.crs),
                    "transform": list(src.transform),
                    "width": src.width,
                    "height": src.height,
                    "count": src.count,
                    "dtypes": [str(dtype) for dtype in src.dtypes],
                    "nodata": src.nodata,
                    "driver": src.driver
                }
                
                return geojson_geom, metadata
                
        except Exception as e:
            logger.error(f"Erro ao processar TIFF: {str(e)}")
            raise

    @with_db_connection
    async def store_raster_geometry(self, conn, image_id: int, tiff_path: str) -> bool:
        """
        Processa e armazena a geometria do TIFF no banco de dados
        
        Args:
            image_id: ID do registro em satellite_images
            tiff_path: Caminho para o arquivo TIFF
            
        Returns:
            bool: True se bem sucedido
        """
        try:
            geom, metadata = self.extract_geometry_from_tiff(tiff_path)
            
            # Converte GeoJSON para WKT (Well-Known Text) para o PostGIS
            geom_wkt = f"SRID=4326;{shape(geom).wkt}"
            
            await conn.execute("""
            UPDATE satellite_images 
            SET 
                raster_geom = ST_GeomFromText($1, 4326),
                raster_metadata = $2::jsonb
            WHERE id = $3
            """, geom_wkt, metadata, image_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao armazenar geometria: {str(e)}")
            return False