from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.responses import Response
from typing import List
import logging
import io
import matplotlib.pyplot as plt
from spin.plot import create_subplots
from utils import get_raster_center_coords
from utils.async_utils import process_request_files
from concurrent.futures import ProcessPoolExecutor
from services.model_loader import create_model_binary, binary_predictor

from spin.inference import (
    InferenceResult,
    KerasInferencePredictor,
    expected_layers,
    extract_layer,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["visualize"])

# Configuração dos modelos
binary_predictor = None
classification_predictor = None

def create_model_binary() -> None:
    global binary_predictor
    binary_predictor = KerasInferencePredictor.from_folder(
        "models/2024-10-17-15-51-39/"
    ) 

def create_model_classification() -> None:
    global classification_predictor
    classification_predictor = KerasInferencePredictor.from_folder(
        "models/2024-10-21-14-34-42/"
    )

pool_binary = ProcessPoolExecutor(max_workers=1, initializer=create_model_binary)
pool_classification = ProcessPoolExecutor(max_workers=1, initializer=create_model_classification)

def run_prediction(mode, image_data) -> InferenceResult:
    predictor = binary_predictor if mode == "binary" else classification_predictor
    image_array = predictor.preprocess_raster(image_data)
    predictions = predictor.predict(image_array)
    return predictor.postprocess_prediction(predictions)
    
@router.post("/visualize/")
async def visualize_all_data(
    files: List[UploadFile], rgb_image: bool = False
) -> Response:
    """
    **Visualiza os dados de imagem enviados.**

    Este endpoint aceita uma lista de arquivos contendo imagens e retorna uma visualização das mesmas.
    Se o parâmetro `rgb_image` for True, a imagem é visualizada em RGB. Caso contrário, cada banda é visualizada separadamente.

    Parâmetros:
    - files: Lista de arquivos de imagem.
    - rgb_image: Booleano que indica se a visualização deve ser em RGB.

    Retorna:
    - Uma resposta HTTP contendo a imagem gerada no formato PNG.
    """
    try:
        # Verifica se o modelo está carregado
        if binary_predictor is None:
            logger.warning("Modelo não encontrado, recarregando...")
            create_model_binary()
        
        data = await process_request_files(files)
        raster_data = [d["data"] for d in data]
        multispectral_img = binary_predictor.preprocess_raster(raster_data)
        all_tipos = [d["layer"] for d in data]

        # Verifica se todas as bandas necessárias estão presentes
        required_bands = {"B4", "B3", "B2"} if rgb_image else set()
        missing_bands = required_bands - set(all_tipos)
        if missing_bands:
            raise HTTPException(
                status_code=400, 
                detail=f"Bandas necessárias ausentes: {missing_bands}"
            )

        i_b4 = all_tipos.index("B4")
        center_coords = get_raster_center_coords(data[i_b4]["data"])

        if rgb_image:
            fig, ax = plt.subplots(figsize=(10, 10))
            i_b3 = all_tipos.index("B3")
            i_b2 = all_tipos.index("B2")
            rgb_image = multispectral_img[:, :, (i_b4, i_b3, i_b2)]
            ax.imshow(rgb_image)
            ax.set_axis_off()
            plt.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)
        else:
            num_channels = multispectral_img.shape[-1]
            fig, ax = create_subplots(num_channels)
            for i in range(num_channels):
                ax[i].imshow(multispectral_img[:, :, i], cmap="terrain")
                ax[i].set_title(data[i]["layer"], fontsize=8)

        plt.tight_layout()
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format="png")
        plt.close(fig)

        headers = {
            "Content-Disposition": 'inline; filename="out.png"',
            "Longitude": str(center_coords[0]),
            "Latitude": str(center_coords[1]),
            "Access-Control-Expose-Headers": "Longitude, Latitude"
        }

        return Response(img_buf.getvalue(), headers=headers, media_type="image/png")

    except Exception as e:
        logger.error(f"Erro na visualização: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))