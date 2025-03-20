import importlib
import pkgutil
from fastapi import APIRouter

def load_routes():
    routers = []
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{module_name}")
        if hasattr(module, "router"):
            routers.append(module.router)
    return routers

__all__ = ["load_routes"]