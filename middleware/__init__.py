from .cors import add_cors_middleware

# Define o que será importado com `from middleware import *`
__all__ = [
    "add_cors_middleware",
]

from fastapi.middleware import Middleware
from fastapi_structlog.middleware import AccessLogMiddleware, CurrentScopeSetMiddleware, StructlogMiddleware
from asgi_correlation_id import CorrelationIdMiddleware

def get_middlewares():
    return [
        Middleware(CurrentScopeSetMiddleware),
        Middleware(CorrelationIdMiddleware),
        Middleware(StructlogMiddleware),
        Middleware(AccessLogMiddleware),
    ]