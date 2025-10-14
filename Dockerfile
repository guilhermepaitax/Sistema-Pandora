ARG PYTHON_VERSION=3.13-slim

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Dependências de build para psycopg2 e afins
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho consistente com o entrypoint
WORKDIR /app

# Instala dependências via pip
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o restante do código
COPY . /app

# Coleta estáticos em build; define STATIC_ROOT para dentro da imagem
ENV STATIC_ROOT=/app/staticfiles_collected
RUN python manage.py collectstatic --noinput || echo "[docker] collectstatic falhou (ok em dev)"

# Porta padrão usada pelo entrypoint/fly.toml
EXPOSE 8080

# Usa o entrypoint do repositório (migrações + daphne/gunicorn)
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
