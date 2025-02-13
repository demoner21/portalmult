from .map_routes import router as map_router
from .predict_routes import router as predict_router
from .visualize_routes import router as visualize_router
from .shp_routes import router as shp_routes

# Define o que será importado com `from routes import *`
__all__ = [
    "map_router",
    "predict_router",
    "visualize_router",
    "shp_routes",
]