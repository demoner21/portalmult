from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import List, Optional

class MapRequest(BaseModel):
    """
    Modelo Pydantic para validação de requisições de mapas.
    """
    latitude: float
    longitude: float
    data: List[str]
    filter: Optional[str] = None

    @field_validator('latitude')
    @classmethod
    def validar_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude deve estar entre -90 e 90')
        return v

    @field_validator('longitude')
    @classmethod
    def validar_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude deve estar entre -180 e 180')
        return v

    @field_validator('data')
    @classmethod
    def validar_datas(cls, v):
        if len(v) != 2:
            raise ValueError('Forneça exatamente duas datas')
        try:
            datas = [datetime.strptime(data, '%Y-%m-%d') for data in v]
            if datas[1] < datas[0]:
                raise ValueError('Data final deve ser posterior à inicial')
            return v
        except ValueError:
            raise ValueError('Use o formato YYYY-MM-DD para as datas')
        
# Dicionário de bandas
bandas = {
    'B1': 0.443, 'B2': 0.490, 'B3': 0.560, 'B4': 0.665, 'B5': 0.705, 'B6': 0.740,
    'B7': 0.783, 'B8': 0.842, 'B8A': 0.865, 'B9': 0.945, 'B11': 1.610, 'B12': 2.190
}

class MapRequestValidator:
    """
    Classe utilitária para validação de requisições de mapas.
    """
    @classmethod
    async def validate(cls, latitude: float, longitude: float, data: List[str], filter: str) -> tuple[str, str, List[str], str]:
        """
        Valida os parâmetros de uma requisição de mapa.

        Args:
            latitude: Latitude do ponto central.
            longitude: Longitude do ponto central.
            data: Lista de datas no formato YYYY-MM-DD.
            filter: Filtro opcional.

        Returns:
            Tuple[str, str, List[str], str]: Parâmetros validados.
        """
        request = MapRequest(
            latitude=latitude,
            longitude=longitude,
            data=data,
            filter=filter
        )
        return (
            str(request.latitude),
            str(request.longitude),
            request.data,
            request.filter
        )