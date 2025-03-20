import structlog
import logging

def setup_logging():
    """
    Configura o logging para o projeto.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,  # Filtra logs por nível
            structlog.processors.TimeStamper(fmt="iso"),  # Adiciona timestamp
            structlog.processors.JSONRenderer()  # Formata logs como JSON
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()