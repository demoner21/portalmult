import pytest
import httpx

@pytest.mark.asyncio
async def test_get_map_successful_request():
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.get(
            "http://localhost:8000/get_map",
            params={
                "latitude": -23.5505,
                "longitude": -46.6333,
                "data": "2023-01-01,2023-01-31",
                "filter": "CLOUDY_PIXEL_PERCENTAGE,10"
            }
        )
        
        assert response.status_code == 200
        assert response.headers['content-type'] == 'application/zip'

@pytest.mark.asyncio
async def test_get_map_invalid_coordinates():
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.get(
            "http://localhost:8000/get_map",
            params={
                "latitude": 100,
                "longitude": 200,
                "data": "2023-01-01,2023-01-31",
                "filter": "CLOUDY_PIXEL_PERCENTAGE,10"
            }
        )
        
        assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_map_invalid_date_range():
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.get(
            "http://localhost:8000/get_map",
            params={
                "latitude": -23.5505,
                "longitude": -46.6333,
                "data": "2024-01-01,2023-01-31",
                "filter": "CLOUDY_PIXEL_PERCENTAGE,10"
            }
        )
        
        assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_map_no_images_found():
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        response = await client.get(
            "http://localhost:8000/get_map",
            params={
                "latitude": -23.5505,
                "longitude": -46.6333,
                "data": "1990-01-01,1990-01-31",
                "filter": "CLOUDY_PIXEL_PERCENTAGE,0"
            }
        )
        
        assert response.status_code == 404