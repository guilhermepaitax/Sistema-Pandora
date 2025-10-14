ARG PYTHON_VERSION=3.13-slim

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependências de build e runtime para psycopg2, Cairo/Pango, WeasyPrint, lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    pkg-config \
    libcairo2-dev \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libfreetype6-dev \
    libharfbuzz-dev \
    libfribidi0 \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho consistente com o entrypoint
WORKDIR /app

# Instala dependências via pip
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app
# Garante diretório de dados para SQLite mesmo se volume não montar
RUN mkdir -p /data && chmod 777 /data

# Coleta estáticos em build; define STATIC_ROOT para dentro da imagem
ENV STATIC_ROOT=/app/staticfiles_collected
RUN python manage.py collectstatic --noinput || echo "[docker] collectstatic falhou (ok em dev)"

# Porta padrão usada pelo entrypoint/fly.toml
EXPOSE 8080

# Usa o entrypoint do repositório (migrações + daphne/gunicorn)
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
