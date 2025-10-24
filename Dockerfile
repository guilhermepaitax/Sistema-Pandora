ARG PYTHON_VERSION=3.13-slim
FROM python:${PYTHON_VERSION} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependências de build (compilar wheels) + libs necessárias para compilações
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    pkg-config \
    libpq-dev \
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

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

COPY . /app
# collectstatic durante build (usa dependências do builder)
ENV STATIC_ROOT=/app/staticfiles_collected
RUN python manage.py collectstatic --noinput || echo "[docker] collectstatic falhou (ok em dev)"

# ---------------- RUNTIME IMAGE ----------------
FROM python:${PYTHON_VERSION} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STATIC_ROOT=/app/staticfiles_collected

# Apenas libs runtime necessárias (sem toolchain pesada)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    libxml2 \
    libxslt1.1 \
    libjpeg62-turbo \
    zlib1g \
    libfreetype6 \
    libharfbuzz0b \
    libfribidi0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia wheels e instala (sem cache)
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copia código e estáticos coletados do builder
COPY --from=builder /app /app

# Garante diretório de dados para SQLite se volume não montar
RUN mkdir -p /data && chmod 777 /data

EXPOSE 8080
ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
