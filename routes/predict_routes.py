from fastapi import APIRouter, UploadFile, HTTPException
from typing import List
from pathlib import Path
import logging
import io
import asyncio
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from utils.async_utils import process_request_files
from services.model_loader import create_model_binary, create_model_classification, binary_predictor, classification_predictor


from spin.inference import (
    InferenceResult,
    KerasInferencePredictor,
    expected_layers,
    extract_layer,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["predict"])

# Configuração dos modelos
create_model_binary()
create_model_classification()

# pool_binary = ProcessPoolExecutor(max_workers=1, initializer=create_model_binary)
# pool_classification = ProcessPoolExecutor(max_workers=1, initializer=create_model_classification)

pool_binary = ThreadPoolExecutor(max_workers=1, initializer=create_model_binary)
pool_classification = ThreadPoolExecutor(max_workers=1, initializer=create_model_classification)

def run_prediction(mode, image_data) -> InferenceResult:
    predictor = binary_predictor if mode == "binary" else classification_predictor
    image_array = predictor.preprocess_raster(image_data)
    predictions = predictor.predict(image_array)
    return predictor.postprocess_prediction(predictions)

@router.post("/predict/")
async def predict_keras_model(files: List[UploadFile]) -> InferenceResult:
    """
    **Predicts the class of an image using a pre-trained Keras model.**

    This endpoint accepts a list of files upload containing all the images and returns the predicted class along with confidence scores.
    """
    data = await process_request_files(files)

    all_layers = {d["layer"] for d in data}
    missing_layers = expected_layers - all_layers
    if len(missing_layers) > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Estão faltando as camadas do tipo: {list(missing_layers)}",
        )

    extra_layers = all_layers - expected_layers
    if len(extra_layers) > 0:
        logger.info("Ignorando tipos de imagem enviado para a api", tipos=extra_layers)

    filtered_data = list(filter(lambda d: d["layer"] in expected_layers, data))
    raster_data = [d["data"] for d in filtered_data]

    loop = asyncio.get_event_loop()
    binary_result = await loop.run_in_executor(
        pool_binary, run_prediction, "binary", raster_data
    )
    if binary_result["predicted_class"] == "presente":
        classification_result = await loop.run_in_executor(
            pool_classification, run_prediction, "classification", raster_data
        )
        classification_result["probabilities"].update(binary_result["probabilities"])
        return classification_result

    return binary_result