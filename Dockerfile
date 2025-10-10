########## STAGE 1: builder ##########
FROM python:3.13-slim-bookworm AS builder
LABEL maintainer="Pandora ERP"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 POETRY_VIRTUALENVS_CREATE=false
WORKDIR /app

RUN apt-get update \
    && apt-get -y upgrade --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libffi-dev \
    libpango-1.0-0 libpangoft2-1.0-0 libpango1.0-dev \
    libjpeg62-turbo-dev zlib1g-dev libwebp-dev \
    libmagic1 file ghostscript ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Primeiro copia somente arquivos de requirements para cache eficiente
COPY requirements-prod.txt requirements-prod.txt
COPY requirements.txt requirements.txt
# Instala somente dependências de produção (requirements-prod.txt). requirements.txt permanece para referência / builds alternativos.
RUN pip install --upgrade pip --root-user-action=ignore \
    && pip install --no-cache-dir -r requirements-prod.txt daphne gunicorn

COPY . .

# Coleta de arquivos estáticos (build-time)
# Adiciona ALLOW_SQLITE_PROD=1 apenas para permitir uso temporário de SQLite durante collectstatic.
ENV DJANGO_DEBUG=False \
    STATIC_ROOT=/app/staticfiles_collected \
    ENABLE_WHITENOISE=1
RUN ALLOW_SQLITE_PROD=1 python manage.py collectstatic --noinput \
    && rm -rf /app/.venv 2>/dev/null || true
ENV DJANGO_DEBUG=

########## STAGE 2: runtime ##########
FROM python:3.13-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get -y upgrade --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    libpq-dev libpango-1.0-0 libpangoft2-1.0-0 \
    libjpeg62-turbo-dev zlib1g-dev libwebp-dev libmagic1 ghostscript ffmpeg \
    && apt-get purge -y --auto-remove \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Cria o usuário NA FASE RUNTIME
RUN useradd -m appuser

COPY --from=builder /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app
# (Removido chown específico de staticfiles_collected que gerava aviso quando diretório não existia)

# Garantir permissões para escrita (migrations, media, etc.)
RUN chown -R appuser:appuser /app

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && chown appuser:appuser /app/entrypoint.sh

USER appuser

EXPOSE 8080
ENV PORT=8080 GUNICORN_WORKERS=3 GUNICORN_TIMEOUT=90
CMD ["/app/entrypoint.sh"]
