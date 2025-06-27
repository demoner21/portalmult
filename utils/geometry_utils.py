from shapely import wkt
from shapely.geometry import shape
from fastapi import HTTPException
from pyproj import Transformer
import logging
from shapely.ops import transform
import json

logger = logging.getLogger(__name__)


def remove_z_from_coordinates(coordinates):
    """
    Remove Z coordinates from geometry coordinates recursively
    """
    if not coordinates:
        return coordinates
    
    # Handle different nesting levels based on geometry type
    if isinstance(coordinates[0], (int, float)):
        # Single coordinate pair/triple - return only x,y
        return coordinates[:2]
    elif isinstance(coordinates[0], list):
        if isinstance(coordinates[0][0], (int, float)):
            # Array of coordinate pairs/triples - remove z from each
            return [coord[:2] for coord in coordinates]
        else:
            # Nested arrays (like Polygon with holes or MultiPolygon)
            return [remove_z_from_coordinates(coord_array) for coord_array in coordinates]
    else:
        return coordinates


def normalize_geometry_for_area_calculation(geojson_geometry):
    """
    Normalize geometry and remove Z coordinates before area calculation
    """
    if isinstance(geojson_geometry, str):
        try:
            geojson_geometry = json.loads(geojson_geometry)
        except json.JSONDecodeError:
            # If it's a WKT string, convert to GeoJSON first
            try:
                geom = wkt.loads(geojson_geometry)
                geojson_geometry = geom.__geo_interface__
            except Exception as e:
                raise ValueError(f"Invalid geometry format: {str(e)}")
    
    # Remove Z coordinates if present
    geom_copy = json.loads(json.dumps(geojson_geometry))  # Deep copy
    
    if geom_copy.get('coordinates'):
        geom_copy['coordinates'] = remove_z_from_coordinates(geom_copy['coordinates'])
    
    # Handle nested geometries in features
    if geom_copy.get('type') == 'FeatureCollection':
        for feature in geom_copy.get('features', []):
            if feature.get('geometry', {}).get('coordinates'):
                feature['geometry']['coordinates'] = remove_z_from_coordinates(
                    feature['geometry']['coordinates']
                )
    elif geom_copy.get('type') == 'Feature' and geom_copy.get('geometry', {}).get('coordinates'):
        geom_copy['geometry']['coordinates'] = remove_z_from_coordinates(
            geom_copy['geometry']['coordinates']
        )
    
    return geom_copy


def calculate_area_ha(geojson_geometry):
    """
    Calcula a área em hectares de uma geometria GeoJSON.
    Suporta FeatureCollection, Feature, Polygon e MultiPolygon.
    Automaticamente remove coordenadas Z se presentes.
    """
    def project_geom(geom):
        # Updated to use the new pyproj Transformer API
        transformer = Transformer.from_crs('EPSG:4326', 'EPSG:3857', always_xy=True)
        return transform(transformer.transform, shape(geom))

    # Normalize geometry and remove Z coordinates
    try:
        normalized_geom = normalize_geometry_for_area_calculation(geojson_geometry)
    except Exception as e:
        logger.error(f"Error normalizing geometry: {str(e)}")
        raise ValueError(f"Cannot normalize geometry for area calculation: {str(e)}")

    geom_type = normalized_geom.get("type", "").lower()

    if geom_type == "featurecollection":
        features = normalized_geom.get("features", [])
        total_area = 0
        for feature in features:
            geom = feature.get("geometry")
            if geom:
                projected = project_geom(geom)
                total_area += projected.area
        return total_area / 10000.0

    elif geom_type == "feature":
        geom = normalized_geom.get("geometry")
        if geom:
            projected = project_geom(geom)
            return projected.area / 10000.0
        else:
            raise ValueError("Feature has no geometry")

    elif geom_type in ["polygon", "multipolygon"]:
        projected = project_geom(normalized_geom)
        return projected.area / 10000.0

    else:
        raise ValueError(f"Unknown geometry type: '{normalized_geom.get('type')}'")


def validate_geometry_wkt(wkt_string: str) -> bool:
    """
    Valida se a string WKT representa uma geometria válida
    """
    try:
        geom = wkt.loads(wkt_string)
        if not geom.is_valid:
            logger.warning(f"Geometria inválida")
            return False
        return True
    except Exception as e:
        logger.error(f"Erro na validação WKT: {str(e)}")
        return False


def geojson_to_wkt(geojson: dict) -> str:
    """
    Converte GeoJSON para WKT
    """
    try:
        geom = shape(geojson)
        return geom.wkt
    except Exception as e:
        logger.error(f"Erro ao converter GeoJSON para WKT: {str(e)}")
        raise HTTPException(status_code=400, detail="GeoJSON inválido")


def wkt_to_geojson(wkt_string: str) -> dict:
    """
    Converte WKT para GeoJSON
    """
    try:
        geom = wkt.loads(wkt_string)
        return geom.__geo_interface__
    except Exception as e:
        logger.error(f"Erro ao converter WKT para GeoJSON: {str(e)}")
        raise HTTPException(status_code=400, detail="WKT inválido")


def calculate_area_ha_alternative(geojson_geometry):
    """
    Alternative method using geodesic calculations for more accuracy
    """
    try:
        from pyproj import Geod
        
        # Handle different input types
        if isinstance(geojson_geometry, str):
            try:
                geojson_geometry = json.loads(geojson_geometry)
            except json.JSONDecodeError:
                try:
                    geom = wkt.loads(geojson_geometry)
                    geojson_geometry = geom.__geo_interface__
                except Exception as e:
                    raise ValueError(f"Invalid geometry format: {str(e)}")
        
        geod = Geod(ellps="WGS84")
        
        def calculate_polygon_area(coords):
            """Calculate area of a polygon using geodesic calculations"""
            if len(coords) == 0:
                return 0
            
            # Extract exterior ring coordinates
            exterior_coords = coords[0] if isinstance(coords[0], list) else coords
            
            # Flatten coordinates if needed
            if len(exterior_coords) > 0 and len(exterior_coords[0]) > 2:
                lons = [coord[0] for coord in exterior_coords]
                lats = [coord[1] for coord in exterior_coords]
            else:
                lons, lats = zip(*exterior_coords) if exterior_coords else ([], [])
            
            if len(lons) < 3:
                return 0
                
            area, _ = geod.polygon_area_perimeter(lons, lats)
            return abs(area)
        
        geom_type = geojson_geometry.get("type", "").lower()
        
        if geom_type == "featurecollection":
            total_area = 0
            for feature in geojson_geometry.get("features", []):
                geom = feature.get("geometry")
                if geom and geom.get("type", "").lower() == "polygon":
                    coords = geom.get("coordinates", [])
                    total_area += calculate_polygon_area(coords)
            return total_area / 10000.0
            
        elif geom_type == "feature":
            geom = geojson_geometry.get("geometry")
            if geom and geom.get("type", "").lower() == "polygon":
                coords = geom.get("coordinates", [])
                area = calculate_polygon_area(coords)
                return area / 10000.0
            return 0
            
        elif geom_type == "polygon":
            coords = geojson_geometry.get("coordinates", [])
            area = calculate_polygon_area(coords)
            return area / 10000.0
            
        elif geom_type == "multipolygon":
            total_area = 0
            for polygon_coords in geojson_geometry.get("coordinates", []):
                total_area += calculate_polygon_area(polygon_coords)
            return total_area / 10000.0
            
        else:
            raise ValueError(f"Unsupported geometry type: {geom_type}")
            
    except Exception as e:
        logger.error(f"Error calculating area with geodesic method: {str(e)}")
        # Fallback to original method
        return calculate_area_ha(geojson_geometry)