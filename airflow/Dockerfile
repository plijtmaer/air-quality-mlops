# =============================================================================
# Dockerfile - Airflow con PySpark y Java pre-instalados
# =============================================================================
# Esta imagen extiende la imagen oficial de Apache Airflow e instala
# las dependencias necesarias para el proyecto air-quality-mlops.
#
# Build:
#   docker compose build --no-cache
#
# =============================================================================

FROM apache/airflow:2.10.1-python3.11

# Cambiar a root para instalar paquetes del sistema
USER root

# Instalar Java (requerido por PySpark) y procps (requerido por Spark)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar JAVA_HOME
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Volver al usuario airflow para instalar paquetes Python
USER airflow

# Instalar dependencias de Python
RUN pip install --no-cache-dir \
    pyspark==3.5.3
