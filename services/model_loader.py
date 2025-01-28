import logging
from pathlib import Path
from typing import Optional
from spin.inference import KerasInferencePredictor

from spin.inference import (
    InferenceResult,
    KerasInferencePredictor,
    expected_layers,
    extract_layer,
)

logger = logging.getLogger(__name__)

binary_predictor: Optional[KerasInferencePredictor] = None
classification_predictor: Optional[KerasInferencePredictor] = None

def create_model_binary() -> Optional[KerasInferencePredictor]:
    """
    Cria e inicializa o preditor binário.
    Returns:
        KerasInferencePredictor: O modelo carregado ou None se houver falha
    """
    global binary_predictor
    try:
        model_path = Path("models/2024-10-17-15-51-39")
        if not model_path.exists():
            raise FileNotFoundError(f"Pasta do modelo não encontrada: {model_path}")
            
        binary_predictor = KerasInferencePredictor.from_folder(model_path)
        logger.info(f"Modelo binário carregado com sucesso de {model_path}")
        return binary_predictor
        
    except Exception as e:
        logger.error(f"Erro ao carregar modelo binário: {e}", exc_info=True)
        binary_predictor = None
        return None

def create_model_classification() -> Optional[KerasInferencePredictor]:
    """
    Cria e inicializa o preditor de classificação.
    Returns:
        KerasInferencePredictor: O modelo carregado ou None se houver falha
    """
    global classification_predictor
    try:
        model_path = Path("models/2024-10-21-14-34-42")
        if not model_path.exists():
            raise FileNotFoundError(f"Pasta do modelo não encontrada: {model_path}")
            
        classification_predictor = KerasInferencePredictor.from_folder(model_path)
        logger.info(f"Modelo de classificação carregado com sucesso de {model_path}")
        return classification_predictor
        
    except Exception as e:
        logger.error(f"Erro ao carregar modelo de classificação: {e}", exc_info=True)
        classification_predictor = None
        return None
    
def run_prediction(mode, image_data) -> InferenceResult:
    predictor = binary_predictor if mode == "binary" else classification_predictor
    image_array = predictor.preprocess_raster(image_data)
    predictions = predictor.predict(image_array)
    return predictor.postprocess_prediction(predictions)