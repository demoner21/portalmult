import rasterio as rio
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

# Configuração para ignorar avisos de divisão por zero
np.seterr(divide='ignore', invalid='ignore')

# Função para normalizar uma banda
def normalize_band(band):
    min_val = np.nanmin(band)
    max_val = np.nanmax(band)
    return (band - min_val) / (max_val - min_val)

# Função para aplicar threshold
def apply_threshold(image, min_val, max_val):
    return np.where((image >= min_val) & (image <= max_val), 1, 0)  # Retorna uma máscara binária

# Função principal para processar NDVI e NDWI
def process_ndvi_ndwi(ndvi_path, ndwi_path, output_png_path):
    # Carregar e normalizar as imagens NDVI e NDWI
    with rio.open(ndvi_path, 'r') as ndvi_file:
        ndvi_band = ndvi_file.read(1)
        normalized_ndvi = normalize_band(ndvi_band)

    with rio.open(ndwi_path, 'r') as ndwi_file:
        ndwi_band = ndwi_file.read(1)
        normalized_ndwi = normalize_band(ndwi_band)

    # Empilhar as imagens em um array 3D
    arr_st = np.stack([normalized_ndvi, normalized_ndwi])

    # Tratar valores NaN (substituir por 0)
    arr_st = np.nan_to_num(arr_st, nan=0.0)

    # Aplicar K-means em todas as bandas
    n_clusters = 2
    images_flat = arr_st.reshape(arr_st.shape[0], -1).T  # Remodelar para (n_pixels, n_bands)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(images_flat)
    segmented_image = labels.reshape(arr_st.shape[1], arr_st.shape[2])  # Remodelar para o formato original

    # Selecionar o cluster de interesse
    cluster_of_interest = 1

    # Criar uma máscara para o cluster de interesse
    cluster_mask = segmented_image == cluster_of_interest

    # Aplicar threshold no NDVI e no NDWI
    min_threshold_ndvi = 0  # Ajuste conforme necessário
    max_threshold_ndvi = 0.4  # Ajuste conforme necessário
    min_threshold_ndwi = 0  # Ajuste conforme necessário
    max_threshold_ndwi = 0.3  # Ajuste conforme necessário

    ndvi_mask = apply_threshold(arr_st[0], min_threshold_ndvi, max_threshold_ndvi)
    ndwi_mask = apply_threshold(arr_st[1], min_threshold_ndwi, max_threshold_ndwi)

    # Aplicar operação bitwise (AND lógico) entre as máscaras de NDVI e NDWI
    common_mask = np.logical_and(ndvi_mask, ndwi_mask)

    # Aplicar a máscara comum ao cluster de interesse
    final_mask = np.logical_and(common_mask, cluster_mask)

    # Verificar se há pixels na máscara final
    if np.sum(final_mask) == 0:
        print("Atenção: A máscara final está vazia (todos os pixels são 0).")
    else:
        print(f"Número de pixels na máscara final: {np.sum(final_mask)}")

    # Salvar a Máscara Final como imagem PNG
    plt.figure(figsize=(10, 10))
    plt.imshow(final_mask, cmap='binary')  # Usar mapa de cores em preto e branco
    plt.title("Máscara Final (NDVI + NDWI)")
    plt.axis('off')  # Remover eixos
    plt.savefig(output_png_path, bbox_inches='tight', pad_inches=0, dpi=300)  # Salvar como PNG
    plt.close()

    print(f"Resultado salvo como {output_png_path}")

# Exemplo de uso
if __name__ == "__main__":
    ndvi_path = "./NDVI.tif"
    ndwi_path = "./NDWI.tif"
    output_png_path = "./output2_mask.png"

    process_ndvi_ndwi(ndvi_path, ndwi_path, output_png_path)