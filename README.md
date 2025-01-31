# Spin Suzano: Detecção de Erosão por Imagens de Satélite

## Introdução

O projeto Spin Suzano é uma ferramenta que utiliza imagens de satélite para detectar erosão em áreas específicas.

## Requisitos

- Python 3.9
- Modelos pré-treinados (disponíveis na pasta 'models')

## Instalação

### Ambiente de Desenvolvimento Local

1. Crie um ambiente virtual utilizando o `python -m venv` e ative-o com `source venv/bin/activate`
2. Instale as dependências necessárias: `pip install -e .`
3. Inicie o servidor de desenvolvimento `uvicorn app:app --host 0.0.0.0 --port 8000 --reload`

## Documentação

A documentação da API está disponível no Swagger em `http://127.0.0.1:8000/docs/`.

O frontend de exemplo está disponível em `http://127.0.0.1:8000/example/`.

### Preparando para Produção

1. Instale a dependência para criar o pacote: `pip install build`
2. Crie o pacote do código: `python -m build`
3. Realize o build do Dockerfile utilizando o comando `docker build -t spin_susano:0.1.0 -f deployment/Dockerfile .`
4. Execute o container com o comando `docker run -p 8000:8000 -d --name backend-test spin_susano:0.1.0`

## Logs e Erros em produção

Os logs do backend podem ser acessados com o comando `docker logs backend-test`.

```bash
docker logs backend-test
```