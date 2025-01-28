import dataclasses
import inspect
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Union


@dataclass
class ModelConfig:
    # Caminho para a pasta raiz do conjunto de dados
    dataset_path: str
    # Quantidade de epocas que vai rodar o treinamento
    epochs: int
    # Taxa de aprendizagem
    learning_rate: float
    resampling: str = "disabled"
    apply_aug: bool = False

    scheduler_epochs: int = 50
    scheduler_decay: float = 0.95
    patience: int = 10
    plateau_decay: float = 0.95

    base_model: str = "airbench"
    task_head: str = "binary"
    bias_scale: float = 80 / 400  # proporcao aproximada de (pos / neg)
    class_frequency: List[int] = field(default_factory=list)

    # Dropout nas camadas convolucionais
    conv_dropout: float = 0.3
    # Dropout nas camadas densas
    dense_dropout: float = 0.0

    # Parametro da loss de treinamento
    label_smoothing: float = 0.2

    # Tamanho alvo que vamos fazer o resize de todas as imagens durante o preprocessamento
    target_size: Tuple[int, ...] = field(default_factory=lambda: (124, 124))

    metrics: List[str] = field(default_factory=lambda: ["accuracy"])

    clipnorm: float = 10.0

    # Tamanho de batch utilizado durante o treinamento
    batch_size: int = 16

    stack_layers: bool = True
    stack_mode: str = field(default="channel")
    # Lista de classes que o modelo vai predizer
    class_map: List[str] = field(default_factory=list)
    # Shape que eh utilizado de entrada para o modelo
    input_shape: Tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.target_size = tuple(self.target_size)

    def as_json(self) -> str:
        """Transforma a classe em uma string JSON

        Returns:
            str: representação dos dados no formato JSON
        """
        return json.dumps(dataclasses.asdict(self))

    def serialize_json(self, folder: Path) -> None:
        """Transforma a classe para JSON e salva o resultado em um arquivo nomeado 'config.json'

        Args:
            folder (Path): caminho da pasta onde vai ser salvo o arquivo
        """
        out_path = folder / "config.json"
        data = self.as_json()
        out_path.write_text(data)

    @classmethod
    def read_json(cls, path: Union[str, Path]) -> "ModelConfig":
        """Cria uma instância da classe a partir de um arquivo JSON salvo em disco

        Args:
            path (Union[str, Path]): Caminho para o arquivo JSON contendo a configuração

        Returns:
            ModelConfig: Modelo com parâmetros carregados do arquivo
        """
        path = Path(path)
        data = json.loads(path.read_text())

        return ModelConfig(
            **{k: v for k, v in data.items() if k in inspect.signature(cls).parameters}
        )
