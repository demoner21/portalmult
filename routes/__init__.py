from .map_routes import router as map_router
from .predict_routes import router as predict_router
from .visualize_routes import router as visualize_router

# Define o que será importado com `from routes import *`
__all__ = [
    "map_router",
    "predict_router",
    "visualize_router",
]