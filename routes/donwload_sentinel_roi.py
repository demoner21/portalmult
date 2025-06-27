from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
import ee
import json
import logging
from database.roi_queries import obter_roi_por_id
from services.earth_engine_processor import EarthEngineProcessor
from utils.jwt_utils import get_current_user
from utils.zip_creator import ZipCreator
from utils.data_range import validate_date_range
from utils.geometry_utils import calculate_area_ha

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sentinel", tags=["Sentinel"])


def remove_z_coordinates(coords):
    """
    Remove sistematicamente o terceiro elemento de todas as coordenadas
    Presume que a estrutura é sempre [lon, lat, z]
    """
    if isinstance(coords, list):
        if len(coords) >= 3 and all(isinstance(x, (int, float)) for x in coords[:3]):
            # Ponto individual: [lon, lat, z] → [lon, lat]
            return coords[:2]
        else:
            # Lista de coordenadas ou estrutura aninhada
            return [remove_z_coordinates(item) for item in coords]
    return coords


def validate_and_fix_geojson(geom_data):
    """
    Valida e corrige problemas comuns em geometrias GeoJSON
    """
    try:
        # Garante que temos um dicionário
        if isinstance(geom_data, str):
            geom_data = json.loads(geom_data)

        # Faz uma cópia profunda para não modificar o original
        geom_copy = json.loads(json.dumps(geom_data))

        # Log da geometria original para debug
        logger.info(f"Tipo de geometria: {geom_copy.get('type', 'UNKNOWN')}")

        # Remove Z coordinates recursivamente
        if 'coordinates' in geom_copy:
            geom_copy['coordinates'] = remove_z_coordinates(
                geom_copy['coordinates'])
            logger.info(
                f"Coordenadas após remoção Z: {len(str(geom_copy['coordinates']))} chars")

        # Validações específicas por tipo de geometria
        geom_type = geom_copy.get('type', '').lower()

        if geom_type == 'featurecollection':
            # Para FeatureCollection, valida cada feature
            features = geom_copy.get('features', [])
            logger.info(f"FeatureCollection com {len(features)} features")

            validated_features = []
            for i, feature in enumerate(features):
                try:
                    if 'geometry' in feature and feature['geometry']:
                        validated_geom = validate_and_fix_geojson(
                            feature['geometry'])
                        feature['geometry'] = validated_geom
                        validated_features.append(feature)
                except Exception as e:
                    logger.warning(f"Feature {i} inválida, pulando: {str(e)}")
                    continue

            geom_copy['features'] = validated_features
            logger.info(
                f"FeatureCollection validada com {len(validated_features)} features válidas")

        elif geom_type == 'polygon':
            # Valida estrutura do polígono
            coords = geom_copy.get('coordinates', [])
            if not coords or not isinstance(coords, list):
                raise ValueError("Polygon deve ter coordenadas")

            # Verifica se cada anel tem pelo menos 4 pontos (fechado)
            for ring_idx, ring in enumerate(coords):
                if len(ring) < 4:
                    raise ValueError(
                        f"Anel {ring_idx} deve ter pelo menos 4 pontos")

                # Garante que o polígono está fechado
                if ring[0] != ring[-1]:
                    ring.append(ring[0])
                    logger.info(
                        f"Polígono fechado automaticamente no anel {ring_idx}")

        elif geom_type == 'multipolygon':
            # Valida estrutura do multipolígono
            coords = geom_copy.get('coordinates', [])
            for poly_idx, polygon in enumerate(coords):
                for ring_idx, ring in enumerate(polygon):
                    if len(ring) < 4:
                        raise ValueError(
                            f"Polígono {poly_idx}, anel {ring_idx} deve ter pelo menos 4 pontos")

                    # Garante que o polígono está fechado
                    if ring[0] != ring[-1]:
                        ring.append(ring[0])
                        logger.info(
                            f"MultiPolygon fechado automaticamente em [{poly_idx}][{ring_idx}]")

        elif geom_type == 'point':
            coords = geom_copy.get('coordinates', [])
            if len(coords) < 2:
                raise ValueError("Point deve ter pelo menos 2 coordenadas")

        elif geom_type == 'linestring':
            coords = geom_copy.get('coordinates', [])
            if len(coords) < 2:
                raise ValueError("LineString deve ter pelo menos 2 pontos")

        # Validação final - tenta criar a geometria no Earth Engine
        if geom_type != 'featurecollection':
            test_geometry = ee.Geometry(geom_copy)
            logger.info(f"Geometria validada com sucesso: {geom_type}")

        return geom_copy

    except Exception as e:
        logger.error(f"Erro na validação da geometria: {str(e)}")
        logger.error(
            f"Geometria problemática: {json.dumps(geom_copy, indent=2)[:500]}...")
        raise ValueError(f"Falha na validação de geometria: {str(e)}")


def convert_geometry_to_ee(geom_data):
    """
    Converte geometria para formato Earth Engine com validação robusta
    """
    try:
        # Valida e corrige a geometria
        validated_geom = validate_and_fix_geojson(geom_data)

        # Para FeatureCollection, cria usando ee.FeatureCollection
        if validated_geom.get('type', '').lower() == 'featurecollection':
            logger.info("Criando ee.FeatureCollection")
            return ee.FeatureCollection(validated_geom)
        else:
            # Para geometrias simples, cria usando ee.Geometry
            logger.info(
                f"Criando ee.Geometry do tipo {validated_geom.get('type')}")
            return ee.Geometry(validated_geom)

    except Exception as e:
        logger.error(f"Erro na conversão para Earth Engine: {str(e)}")
        raise ValueError(f"Falha na conversão de geometria: {str(e)}")


def extract_geometry_from_feature_collection(fc_geometry):
    """
    Extrai a geometria combinada de uma FeatureCollection para usar como região
    """
    try:
        if isinstance(fc_geometry, dict) and fc_geometry.get('type') == 'FeatureCollection':
            features = fc_geometry.get('features', [])
            if not features:
                raise ValueError("FeatureCollection vazia")

            # Se tem apenas uma feature, usa sua geometria
            if len(features) == 1:
                return features[0]['geometry']

            # Se tem múltiplas features, cria um MultiPolygon ou mantém como FeatureCollection
            # Para processamento no Earth Engine, é melhor manter como FeatureCollection
            return fc_geometry

        return fc_geometry

    except Exception as e:
        logger.error(
            f"Erro ao extrair geometria da FeatureCollection: {str(e)}")
        raise


@router.get("/{roi_id}/download-sentinel")
async def download_sentinel_images(
    roi_id: int,
    start_date: str = Query(...,
                            description="Data de início no formato YYYY-MM-DD"),
    end_date: str = Query(...,
                          description="Data de término no formato YYYY-MM-DD"),
    cloud_pixel_percentage: float = Query(
        ..., description="Percentual máximo de nuvens permitido (0 a 100)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint para download de imagens do Sentinel-2 com base no roi_id,
    levando em consideração o tamanho do shapefile.
    """
    try:
        # Busca a ROI no banco de dados
        roi = await obter_roi_por_id(roi_id, current_user['id'])
        if not roi:
            raise HTTPException(status_code=404, detail="ROI não encontrada")

        # Validação de datas e parâmetros
        validate_date_range(start_date, end_date)
        if not 0 <= cloud_pixel_percentage <= 100:
            raise HTTPException(status_code=400, detail="Percentual de nuvens inválido")

        # Process metadata
        metadata = roi.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        area_ha = metadata.get("area_ha", None)
        if area_ha is None:
            try:
                area_ha = calculate_area_ha(roi['geometria'])
                logger.warning(
                    f"Calculated area on-the-fly for ROI {roi_id}: {area_ha} ha")
            except Exception as e:
                logger.error(
                    f"Failed to calculate area for ROI {roi_id}: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Não foi possível calcular a área da ROI. Erro: {str(e)}"
                )

        # Limite de área (ajuste conforme necessário)
        MAX_AREA_HA = 500000
        if area_ha > MAX_AREA_HA:
            raise HTTPException(
                status_code=400,
                detail=f"A área da ROI é muito grande ({area_ha:.2f} ha). Limite permitido: {MAX_AREA_HA} ha"
            )

        # Convert geometry to proper format for Earth Engine
        try:
            geom_data = roi['geometria']
            logger.debug(f"Geometry type: {type(geom_data)}")
            logger.debug(f"Geometry content sample: {str(geom_data)[:200]}")
            
            # Utiliza a nova função robusta para converter a geometria
            geometry = convert_geometry_to_ee(geom_data)
            
            if geometry is None:
                 raise ValueError("A conversão da geometria resultou em None")

        except Exception as geom_error:
            logger.error(
                f"Erro na conversão da geometria (ROI {roi_id}): {str(geom_error)}")
            raise HTTPException(
                status_code=400,
                detail=f"Geometria da ROI em formato inválido. Recrie a ROI com shapefile válido. Erro: {str(geom_error)}"
            )

        # Processa as imagens usando o EarthEngineProcessor
        processor = EarthEngineProcessor()
        parameters = {
            "latitude": 0,  # Adicionado para compatibilidade de cache
            "longitude": 0, # Adicionado para compatibilidade de cache
            "data": [start_date, end_date],
            "filter": f"CLOUDY_PIXEL_PERCENTAGE,{cloud_pixel_percentage}",
            "geometry": geometry  # Pass the geometry directly
        }

        try:
            result_files, _ = await processor.process_data(parameters)
        except Exception as ee_error:
            logger.error(
                f"Erro no Earth Engine (ROI {roi_id}): {str(ee_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao processar imagens no Earth Engine: {str(ee_error)}"
            )

        if not result_files:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma imagem encontrada para os critérios especificados"
            )

        # Cria o arquivo ZIP
        zip_creator = ZipCreator()
        zip_buffer = await zip_creator.create_zip_file(result_files)

        # Log successful download
        logger.info(
            f"Download realizado com sucesso para ROI {roi_id}. "
            f"Período: {start_date} a {end_date}, "
            f"Nuvens: {cloud_pixel_percentage}%, "
            f"Área: {area_ha:.2f} ha"
        )

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                'Content-Disposition': f'attachment; filename="sentinel_roi_{roi_id}_{start_date}_{end_date}.zip"'
            }
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(
            f"Erro geral no download das imagens (ROI {roi_id}): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro inesperado ao processar o download: {str(e)}"
        )