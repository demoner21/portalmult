import asyncio
import time
import logging

logger = logging.getLogger(__name__)

class RequestQueue:
    def __init__(self, cooldown_period=2):
        """
        Inicializa a fila de processamento com um período de cooldown entre requisições semelhantes.
        
        Args:
            cooldown_period: Tempo mínimo entre requisições para o mesmo ponto (em segundos).
        """
        self.request_cache = {}
        self.cooldown_period = cooldown_period
        self._lock = asyncio.Lock()

    async def can_process_request(self, key: str) -> bool:
        """
        Verifica se uma requisição pode ser processada com base no histórico recente.
        
        Args:
            key: Chave única para identificar a requisição.

        Returns:
            bool: True se a requisição pode ser processada, False caso contrário.
        """
        async with self._lock:
            current_time = time.time()
            
            # Se não existir entrada anterior para esta chave, permite a requisição
            if key not in self.request_cache:
                self.request_cache[key] = current_time
                return True
            
            # Verifica o tempo desde a última requisição
            last_request_time = self.request_cache[key]
            if current_time - last_request_time >= self.cooldown_period:
                self.request_cache[key] = current_time
                return True
            
            return False