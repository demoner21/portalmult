# Estrutura do Programa:

## 1. Introdução

Este documento descreve a estrutura técnica do programa, incluindo os principais módulos, funcionalidades e definições técnicas. O sistema tem como objetivo processar dados geoespaciais utilizando modelos de machine learning para detecção de padrões e geração de visualizações.

## 2. Estrutura do Diretório

```
├── README.md
├── app.py
├── pyproject.toml
├── middleware/
│   ├── __init__.py
│   ├── cors.py
│   ├── logging.py
│   └── request_queue.py
├── models/
│   ├── <model_version>/
│       ├── config.json
│       ├── model.checkpoint.best.keras
│       ├── train/
│       ├── validation/
├── routes/
│   ├── __init__.py
│   ├── map_routes.py
│   ├── predict_routes.py
│   └── visualize_routes.py
├── services/
│   ├── __init__.py
│   ├── earth_engine_processor.py
│   ├── model_loader.py
│   └── zip_creator.py
├── spin/
│   ├── config.py
│   ├── inference.py
│   ├── model.py
│   └── plot.py
├── static/
│   └── index.html
├── utils/
│   ├── __init__.py
│   ├── async_utils.py
│   ├── logging.py
│   ├── raster_utils.py
│   ├── validators.py
│   └── zip_creator.py
```

## 3. Principais Componentes

### 3.1 Módulo `app.py`

**Descrição:** Arquivo principal do aplicativo FastAPI que inicializa os serviços, middleware e rotas.

- Inicialização do Google Earth Engine (GEE).
- Configuração do middleware de logging e CORS.
- Montagem de rotas para os endpoints de API.

### 3.2 Diretório `middleware`

**Descrição:** Contém middlewares para funcionalidades específicas.

- **`cors.py`**: Adiciona suporte a requisições de origem cruzada.
- **`logging.py`**: Configura logs estruturados utilizando `structlog`.
- **`request_queue.py`**: Implementa controle de taxa para requisições similares.

### 3.3 Diretório `models`

**Descrição:** Contém os modelos treinados e configurações relacionadas.

- **`config.json`**: Define parâmetros como taxa de aprendizado, classes, e arquitetura do modelo.
- **`model.checkpoint.best.keras`**: Modelo treinado salvo em formato Keras.

### 3.4 Diretório `routes`

**Descrição:** Define as rotas da API.

- **`map_routes.py`**: Geração de mapas baseados em dados de satélite.
- **`predict_routes.py`**: Predição de classes utilizando modelos de machine learning.
- **`visualize_routes.py`**: Visualização de dados geoespaciais.

### 3.5 Diretório `services`

**Descrição:** Contém serviços para processamento de dados.

- **`earth_engine_processor.py`**: Interação com o Google Earth Engine para download de bandas e cálculo de índices.
- **`model_loader.py`**: Carrega os modelos Keras para inferência.
- **`zip_creator.py`**: Cria arquivos ZIP a partir de resultados processados.

### 3.6 Diretório `spin`

**Descrição:** Implementação de lógica central de machine learning.

- **`config.py`**: Define a classe de configuração dos modelos.
- **`inference.py`**: Executa a inferência nos dados.
- **`model.py`**: Carrega os modelos treinados.
- **`plot.py`**: Cria subplots para visualização de múltiplas bandas.

### 3.7 Diretório `utils`

**Descrição:** Funções utilitárias para suporte geral.

- **`async_utils.py`**: Gerenciamento assíncrono de arquivos e downloads.
- **`logging.py`**: Configuração do sistema de logs.
- **`raster_utils.py`**: Processamento e normalização de dados raster.
- **`validators.py`**: Validação de entradas para requisições de API.
- **`zip_creator.py`**: Criação de arquivos compactados.

## 4. Glossário de Termos

| Termo              | Definição                                                                      |
| ------------------ | ------------------------------------------------------------------------------ |
| FastAPI            | Framework web em Python utilizado para criação de APIs RESTful.                |
| Earth Engine (GEE) | Plataforma de análise e processamento de dados geoespaciais do Google.         |
| CORS               | Cross-Origin Resource Sharing, permite controle de acesso entre origens.       |
| Middleware         | Camada intermediária que intercepta requisições ou respostas.                  |
| Raster             | Representação matricial de dados geoespaciais (ex: imagens TIFF).              |
| NDVI               | Índice de Vegetação por Diferença Normalizada, usado para monitorar vegetação. |
| Keras              | Biblioteca de deep learning para construção e treinamento de modelos.          |
| Structlog          | Biblioteca de logging estruturado.                                             |
| JSON               | Formato leve de troca de dados.                                                |
| Inference          | Processo de predição utilizando um modelo treinado.                            |
| API                | Interface de Programação de Aplicações, permite integração entre sistemas.     |

## 5. Conclusão

O programa modular que integra APIs modernas, ferramentas de aprendizado de máquina e recursos de processamento geoespacial para oferecer soluções robustas na análise de dados de satélite. O design do sistema promove escalabilidade e manutenibilidade, atendendo às necessidades de desenvolvedores e cientistas de dados.

