# Usa uma imagem oficial e leve do Python
FROM python:3.11-slim

# Evita que o Python guarde logs em buffer, mostrando-os em tempo real
ENV PYTHONUNBUFFERED 1

# Define o diretório de trabalho dentro do container
WORKDIR /code

# --- ALTERAÇÃO APLICADA AQUI ---
# Instala as dependências de sistema necessárias para o WeasyPrint
RUN apt-get update && apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libgobject-2.0-0

# Copia o arquivo de dependências e as instala
COPY requirements.txt /code/
RUN pip install -r requirements.txt

# Copia o resto do código do projeto para o diretório de trabalho
COPY . /code/