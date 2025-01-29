#!/bin/bash

# Solicita a palavra-chave ao usuário
echo -n "Digite a palavra-chave para buscar: "
read palavra

# Verifica se o usuário inseriu uma palavra
if [ -z "$palavra" ]; then
    echo "Nenhuma palavra-chave inserida. Saindo..."
    exit 1
fi

# Define o arquivo de saída
output_file="resultados.txt"

# Busca a palavra nos arquivos da pasta atual e subpastas e salva os nomes dos arquivos únicos
grep -rl "$palavra" . > "$output_file"

# Verifica se foram encontrados resultados
if [ -s "$output_file" ]; then
    echo "Busca concluída. Os arquivos com correspondência foram salvos em '$output_file'."
else
    echo "Nenhuma correspondência encontrada."
    rm "$output_file"
fi

