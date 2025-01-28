import os
from logging import Logger
from pathlib import Path
from typing import Dict, List, Tuple, Union

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import numpy as np
import rasterio
import structlog
from tensorflow import keras
from typing_extensions import TypedDict

from spin.config import ModelConfig
from spin.model import load_model_with_config

logger: Logger = structlog.get_logger()


class InferenceResult(TypedDict):
    # Classe que o modelo indicou com maior confiança
    predicted_class: str
    # Confiança da predição principal
    confidence: float
    # Lista de todas as probabilidades por classe
    probabilities: Dict[str, float]


def to_shape(a, shape):
    y_, x_ = shape
    y, x = a.shape
    y_pad = y_ - y
    x_pad = x_ - x
    return np.pad(
        a,
        ((y_pad // 2, y_pad // 2 + y_pad % 2), (x_pad // 2, x_pad // 2 + x_pad % 2)),
        mode="constant",
    )


def normalize_data(data: np.ndarray) -> np.ndarray:
    data = np.nan_to_num(data, neginf=0, posinf=0)
    if data.dtype == np.uint8:
        return data / 255
    return (data - data.min()) / (data.max() - data.min())


def decode_raster(source_data, target_shape: Tuple[int, int]) -> np.ndarray:
    with rasterio.open(source_data) as src:
        source_data = src.read(1)
    source_data = source_data[: target_shape[0], : target_shape[1]]
    source_data = to_shape(source_data, target_shape)
    return normalize_data(source_data)


grupo1 = [
    "BSI",
    "NDRE",
    "NDVI",
    "NDWI",
    "SAVI",
    "EVI",
]

grupo2 = [
    "DEM",
    "Aspect",
    "Curvature",
    "Elevation",
    "Flow_Acc",
    "HSG",
    "Slope_Length",
    "Slope",
    "TWI",
]

grupo3 = [
    "B11",
    "B12",
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "B7",
    "B8A",
    "B8",
    "B9",
]


def extract_layer(name: str) -> str:
    possible_layers = grupo1 + grupo2 + grupo3
    for tipo in possible_layers:
        if tipo in name:
            return tipo
    msg = f"Tipo de arquivo nao reconhecido {name}"
    raise ValueError(msg)


expected_layers = {*grupo3, "BSI", "NDVI", "NDWI", "SAVI"}


class KerasInferencePredictor:
    def __init__(self, model: keras.Model, config: ModelConfig) -> None:
        self.model = model
        self.config = config
        logger.info(
            "Criando KerasInferencePredictor com configuracao", config=config.as_json()
        )

    @classmethod
    def from_folder(cls, path: Union[str, Path]) -> "KerasInferencePredictor":
        """Construindo um InferencePredictor a partir de uma pasta contendo o modelo/config salvos durante o treinamento.

        Args:
            path (Union[str, Path]): Caminho da pasta onde são salvos os dados no treinamento

        Returns:
            KerasInferencePredictor: Modelo pronto para predição.
        """
        path = Path(path)
        model, config = load_model_with_config(path)
        return cls(model, config)

    def preprocess_raster(self, raster_data: List):
        """Processa uma lista de dados de raster de acordo com o que o modelo espera."""
        imgs = [
            decode_raster(r, target_shape=self.config.target_size) for r in raster_data
        ]

        if self.config.stack_mode == "channel":
            multispectral_img = np.stack(imgs, axis=-1)
        elif self.config.stack_mode == "hstack":
            multispectral_img = np.hstack(imgs)
            multispectral_img = np.expand_dims(multispectral_img, axis=-1)
        return multispectral_img

    def predict(self, image_array: np.ndarray) -> np.ndarray:
        """Realiza a predição de uma única imagem, deve vir após o pre-processamento.

        Args:
            image_array (np.ndarray): Array contendo a informação já pre-processada

        Returns:
            np.ndarray: Predição do keras com a lista de probabilidades
        """
        preprocessed_image = np.expand_dims(image_array, axis=0)
        return self.model.predict(preprocessed_image, verbose="0")

    def postprocess_prediction(self, predictions: np.ndarray) -> InferenceResult:
        """Extrai a predição e as classes do modelo de forma estruturada

        Args:
            predictions (np.ndarray): Predição do keras conforme retornado pela função predict

        Returns:
            InferenceResult: Dicionário estruturado com informações detalhadas da predição.
        """
        raw_probs = np.clip(100 * predictions, 0.0, 100.0)

        if self.config.task_head == "binary":
            max_prediction = np.squeeze((predictions > 0.5).astype(int))
            confidence = predictions[0]
            probabilities = {
                self.config.class_map[0]: 100 - int(raw_probs[0]),
                self.config.class_map[1]: int(raw_probs[0]),
            }
        else:
            max_prediction = int(np.argmax(predictions))
            confidence = predictions[0][max_prediction]
            probabilities = {
                k: int(v) for k, v in zip(self.config.class_map, raw_probs[0])
            }

        predicted_class = self.config.class_map[max_prediction]

        logger.info(
            "Realizada predicao das classes",
            probabilidades=probabilities,
            max_prediction=max_prediction,
        )

        return {
            "predicted_class": predicted_class,
            "confidence": float(confidence),
            "probabilities": probabilities,
        }
