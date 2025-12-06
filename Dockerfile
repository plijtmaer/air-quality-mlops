# =============================================================================
# Air Quality MLOps - FastAPI Inference API
# =============================================================================
# 
# Este Dockerfile construye la imagen para la API de inferencia.
#
# Build:
#   docker build -t air-quality-api:latest .
#
# Run:
#   docker run -p 8000:8000 air-quality-api:latest
#
# =============================================================================

FROM python:3.11-slim

# Metadata
LABEL maintainer="Paul Lijtmaer"
LABEL description="Air Quality Classification API - FastAPI + PyCaret + Evidently"
LABEL version="1.0.0"

# Configurar variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Crear directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para aprovechar cache de Docker)
COPY requirements.txt .

# Instalar dependencias de Python
# Usamos --no-deps para evitar conflictos y luego instalamos todo
RUN pip install --upgrade pip && \
    pip install \
    fastapi==0.115.6 \
    uvicorn[standard]==0.34.0 \
    pydantic==2.10.6 \
    pandas==2.1.4 \
    numpy==1.26.4 \
    scikit-learn==1.4.2 \
    pycaret==3.3.2 \
    evidently==0.4.33 \
    requests==2.32.5

# Copiar el código fuente
COPY src/ ./src/

# Crear directorios para datos y modelos
# En producción, estos se montan como volúmenes
RUN mkdir -p /app/models /app/data/curated /app/reports/monitoring

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando por defecto
CMD ["uvicorn", "src.inference.main:app", "--host", "0.0.0.0", "--port", "8000"]

