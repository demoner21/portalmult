from pathlib import Path
from typing import Tuple

from tensorflow import keras

from spin.config import ModelConfig


class IdentityLayer(keras.layers.Layer):
    def call(self, inputs):
        return inputs


def load_model_with_config(base: Path) -> Tuple[keras.Model, ModelConfig]:
    """Carrega o modelo e a configuração a partir de uma pasta contendo os arquivos gerados durante o treinamento.

    Args:
        base (Path): Pasta contendo os arquivos 'config.json' e 'model.checkpoint.keras'

    Returns:
        Tuple[keras.Model, ModelConfig]: Modelo e configuração carregados do disco
    """
    config = ModelConfig.read_json(base / "config.json")

    model_file = str(base / "model.checkpoint.best.keras")
    model = keras.models.load_model(
        model_file,
        custom_objects={"AugmentationLayer": IdentityLayer},
    )

    return model, config
