import geopandas as gpd
from shapely.geometry import shape
from typing import Dict, Tuple
import json
import logging
from pathlib import Path
import pyproj
from functools import partial
from shapely.ops import transform

logger = logging.getLogger(__name__)

class ShapefileProcessor:
    async def process(self, temp_dir: Path) -> Dict:
        """Processa os arquivos do shapefile e retorna dados padronizados"""
        try:
            # Encontrar arquivo .shp no diretório temporário
            shp_files = list(temp_dir.glob('*.shp'))
            if not shp_files:
                raise ValueError("Nenhum arquivo .shp encontrado")
            
            shp_path = shp_files[0]
            
            # Ler shapefile com geopandas
            gdf = gpd.read_file(shp_path)
            if gdf.empty:
                raise ValueError("Shapefile não contém geometrias")
            
            # Verificar e converter CRS para WGS84 se necessário
            gdf = self.ensure_wgs84(gdf)
            
            # Pegar a primeira geometria (podemos expandir para múltiplas depois)
            geometry = gdf.geometry.iloc[0]
            
            # Calcular área em hectares
            area_ha = self.calculate_area(geometry)
            
            # Converter para formatos padrão
                    # Converter para formatos padrão
            geojson = json.loads(gdf.iloc[[0]].to_json())['features'][0]['geometry']
            
            # Garantir que as coordenadas são listas, não arrays numpy
            if 'coordinates' in geojson:
                geojson['coordinates'] = [list(map(list, ring)) for ring in geojson['coordinates']]
            
            wkt = geometry.wkt
            
            return {
                'type': geometry.geom_type,
                'geojson': geojson,  # Já é um dict válido
                'wkt': wkt,
                'area': area_ha,
                'bbox': list(map(float, geometry.bounds)),  # Garante floats simples
                'properties': self.extract_properties(gdf),
                'crs': 'EPSG:4326'
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento: {str(e)}", exc_info=True)
            raise

    def ensure_wgs84(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Garante que o GeoDataFrame está em WGS84"""
        if gdf.crs is None:
            raise ValueError("Shapefile não possui sistema de referência definido")
            
        if gdf.crs != 'EPSG:4326':
            logger.info(f"Convertendo CRS de {gdf.crs} para EPSG:4326")
            return gdf.to_crs('EPSG:4326')
            
        return gdf

    def calculate_area(self, geometry) -> float:
        """Calcula área aproximada em hectares"""
        # Usando projeção para cálculo de área mais preciso
        project = partial(
            pyproj.transform,
            pyproj.Proj('EPSG:4326'),
            pyproj.Proj(
                proj='aea',
                lat_1=geometry.bounds[1],
                lat_2=geometry.bounds[3]
            )
        )
        
        transformed_geom = transform(project, geometry)
        return transformed_geom.area / 10000  # m² para hectares

    def extract_properties(self, gdf: gpd.GeoDataFrame) -> Dict:
        """Extrai propriedades do dbf para metadados"""
        if len(gdf.columns) > 1:  # Tem atributos além da geometria
            return gdf.iloc[0].drop('geometry').to_dict()
        return {}