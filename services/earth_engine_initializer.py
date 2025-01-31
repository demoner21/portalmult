import ee
import logging

logger = logging.getLogger(__name__)

def initialize_earth_engine():
    try:
        ee.Initialize()
    except Exception as e:
        logger.error(f"Erro ao inicializar o Earth Engine: {str(e)}")
        logger.info("Autenticando no Earth Engine...")
        try:
            ee.Authenticate()
            ee.Initialize()
            logger.info("Autenticação bem-sucedida.")
        except Exception as auth_error:
            logger.error(f"Falha na autenticação do Earth Engine: {str(auth_error)}")
            raise RuntimeError("Erro ao autenticar o Earth Engine.")
