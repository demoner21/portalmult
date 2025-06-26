import logging
import geopandas as gpd
import pandas as pd
from shapely.geometry import shape, Polygon, MultiPolygon, mapping
from shapely.validation import explain_validity
from shapely.ops import transform
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)

class ShapefileProcessor:
    """Processador avançado de shapefiles com detecção automática de tipo de geometria"""
    
    async def process(self, temp_dir: Path) -> Dict[str, Any]:
        """
        Processa shapefile e retorna dados estruturados para ROI
        
        Args:
            temp_dir: Diretório temporário com arquivos do shapefile
            
        Returns:
            Dicionário no formato:
            {
                "features": [lista de features GeoJSON],
                "metadata": {
                    "total_features": int,
                    "area_total_ha": float,
                    "bbox": [minx, miny, maxx, maxy],
                    "geometry_types": [tipos encontrados],
                    "crs_original": str,
                    "sistema_referencia": "EPSG:4326"
                }
            }
        """
        try:
            # 1. Ler o shapefile
            gdf = await self._read_shapefile(temp_dir)
            logger.info(f"Shapefile lido com {len(gdf)} features")
            
            # 2. Converter para WGS84 se necessário
            crs_original = str(gdf.crs) if gdf.crs else "Não definido"
            gdf = await self._ensure_wgs84(gdf)
            
            # 3. Processar cada feature
            processed_features = []
            total_area_ha = 0
            geometry_types = set()
            
            for idx, row in gdf.iterrows():
                try:
                    # Processar geometria
                    geom_geojson = await self._process_geometry(row.geometry)
                    geometry_types.add(row.geometry.geom_type)
                    
                    # Calcular área em hectares (assumindo WGS84)
                    area_ha = await self._calculate_area_hectares(row.geometry)
                    total_area_ha += area_ha
                    
                    # Processar atributos do DBF
                    properties = await self._process_attributes(row, idx, area_ha)
                    
                    # Criar feature GeoJSON
                    feature = {
                        "type": "Feature",
                        "geometry": geom_geojson,
                        "properties": properties
                    }
                    
                    processed_features.append(feature)
                    
                except Exception as feature_error:
                    logger.error(f"Erro processando feature {idx}: {feature_error}")
                    # Não interrompe o processamento, apenas pula esta feature
                    continue
            
            if not processed_features:
                raise ValueError("Nenhuma feature válida foi processada do shapefile")
            
            # 4. Calcular bounding box geral
            bbox = await self._calculate_bbox(gdf)
            
            # 5. Preparar metadados
            metadata = {
                "total_features": len(processed_features),
                "area_total_ha": round(total_area_ha, 2),
                "bbox": bbox,
                "geometry_types": list(geometry_types),
                "crs_original": crs_original,
                "sistema_referencia": "EPSG:4326"
            }
            
            return {
                "features": processed_features,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento do shapefile: {str(e)}", exc_info=True)
            raise

    async def _read_shapefile(self, temp_dir: Path) -> gpd.GeoDataFrame:
        """Lê o shapefile e verifica se não está vazio"""
        shp_files = list(temp_dir.glob("*.shp"))
        if not shp_files:
            raise ValueError("Nenhum arquivo .shp encontrado no diretório")
            
        gdf = gpd.read_file(shp_files[0])
        if gdf.empty:
            raise ValueError("Shapefile não contém features")
            
        logger.info(f"Shapefile carregado: {len(gdf)} features, CRS: {gdf.crs}")
        return gdf

    async def _ensure_wgs84(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Converte para WGS84 (EPSG:4326) se necessário"""
        if gdf.crs is None:
            logger.warning("CRS não definido, assumindo EPSG:4326")
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            logger.info(f"Convertendo CRS de {gdf.crs} para EPSG:4326")
            gdf = gdf.to_crs("EPSG:4326")
        return gdf

    async def _process_geometry(self, geometry) -> Dict[str, Any]:
        """Processa e valida a geometria, convertendo para GeoJSON"""
        def add_z(x, y, z=None):
            return x, y, 0 if z is None else z
        geometry = transform(add_z, geometry)
        
        # Validar topologia
        if not geometry.is_valid:
            logger.warning(f"Geometria inválida encontrada: {explain_validity(geometry)}")
            geometry = geometry.buffer(0)
            if not geometry.is_valid:
                raise ValueError(f"Geometria não pôde ser corrigida: {explain_validity(geometry)}")
        
        return mapping(geometry)

    async def _calculate_area_hectares(self, geometry) -> float:
        """
        Calcula área em hectares
        Para WGS84, usa aproximação simples (adequada para áreas pequenas)
        """
        try:
            # Para WGS84, convertemos para um CRS métrico temporariamente
            from pyproj import CRS, Transformer
            
            # Usar UTM apropriado baseado no centróide
            centroid = geometry.centroid
            utm_crs = f"EPSG:{32600 + int((centroid.x + 180) / 6) + 1}"
            
            # Transformar para UTM
            transformer = Transformer.from_crs("EPSG:4326", utm_crs, always_xy=True)
            geom_utm = transform(transformer.transform, geometry)
            
            # Área em metros quadrados, converter para hectares
            area_m2 = geom_utm.area
            area_ha = area_m2 / 10000
            
            return area_ha
            
        except Exception as e:
            logger.warning(f"Erro no cálculo de área: {e}. Usando aproximação simples.")
            # Fallback: aproximação grosseira para WGS84
            return geometry.area * 111000 * 111000 / 10000

    async def _process_attributes(self, row: Any, feature_idx: int, area_ha: float) -> Dict[str, Any]:
        """Processa os atributos do DBF para a feature"""
        properties = {
            "feature_id": int(feature_idx),
            "area_ha": round(area_ha, 2)
        }
        
        for col_name, value in row.items():
            if col_name == 'geometry':
                continue
                
            if pd.isna(value):
                properties[col_name] = None
            elif isinstance(value, (int, float, str, bool)):
                properties[col_name] = value
            else:
                properties[col_name] = str(value)
        
        return properties

    async def _calculate_bbox(self, gdf: gpd.GeoDataFrame) -> List[float]:
        """Calcula o bounding box geral do shapefile"""
        bounds = gdf.total_bounds
        return [float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])]

    def _identify_geometry_type(self, gdf: gpd.GeoDataFrame) -> str:
        """Identifica se o shapefile contém geometrias individuais ou múltiplas"""
        geom_types = set(gdf.geometry.geom_type)
        
        if len(geom_types) == 1:
            return "single" if "Multi" not in next(iter(geom_types)) else "multi"
        
        return "multi"