"""
DAG: ingest_air_quality
========================

Este DAG obtiene datos de calidad del aire desde la API de Open-Meteo
y los guarda en formato JSON crudo en la carpeta data/raw/.

Open-Meteo Air Quality API:
    - 100% gratuita, sin límites
    - No requiere API key ni autenticación
    - Datos horarios de PM2.5, PM10, NO2, O3, CO, SO2, AQI
    - Datos históricos (hasta 92 días) + pronóstico (hasta 7 días)

Flujo:
    1. Llama a la API de Open-Meteo para una ciudad específica
    2. Guarda el JSON completo en data/raw/{ciudad}/{timestamp}.json

Programación:
    - Ejecuta cada hora (@hourly)
    - No hace catchup de ejecuciones pasadas

Configuración:
    - Ciudad: Buenos_Aires (coordenadas: -34.6, -58.4)
    - Días históricos: 7 (para tener datos de entrenamiento)
    - Días de pronóstico: 1
    
    Ciudades disponibles: Buenos_Aires, Santiago, Lima, Bogota, Mexico_City, Sao_Paulo

Datos guardados:
    Los archivos se guardan en: /opt/airflow/data/raw/{ciudad}/{timestamp}.json
    
    Estructura del JSON:
    {
        "latitude": -34.6,
        "longitude": -58.4,
        "timezone": "America/Argentina/Buenos_Aires",
        "hourly_units": {
            "time": "iso8601",
            "pm2_5": "μg/m³",
            "pm10": "μg/m³",
            ...
        },
        "hourly": {
            "time": ["2025-01-01T00:00", "2025-01-01T01:00", ...],
            "pm2_5": [10.3, 9.5, ...],
            "pm10": [15.2, 14.1, ...],
            "us_aqi": [42, 38, ...],
            ...
        },
        "city_name": "Buenos_Aires",
        "fetch_timestamp": "2025-01-01T12:00:00.000000"
    }

Autor: MLOps Team
Proyecto: air-quality-mlops
"""

import logging
import sys
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# =============================================================================
# Configurar path para imports del proyecto
# =============================================================================
sys.path.insert(0, "/opt/airflow")

from src.ingestion.open_meteo_client import fetch_air_quality_data, save_raw_data

# Logger para este DAG
logger = logging.getLogger(__name__)

# =============================================================================
# Configuración del DAG
# =============================================================================

# Ciudad a monitorear
DEFAULT_CITY = "Buenos_Aires"

# Días históricos a obtener (para tener datos de entrenamiento)
DEFAULT_PAST_DAYS = 7

# Días de pronóstico
DEFAULT_FORECAST_DAYS = 1


# =============================================================================
# Funciones del DAG
# =============================================================================

def ingest_air_quality_task(
    city: str = DEFAULT_CITY,
    past_days: int = DEFAULT_PAST_DAYS,
    forecast_days: int = DEFAULT_FORECAST_DAYS,
    **context
) -> dict:
    """
    Tarea principal de ingestión: obtiene datos y los guarda.
    
    Args:
        city: Nombre de la ciudad
        past_days: Días históricos a obtener
        forecast_days: Días de pronóstico
        **context: Contexto de Airflow
    
    Returns:
        dict: Información sobre la ejecución para XCom
    """
    execution_date = context.get("execution_date", datetime.utcnow())
    
    logger.info("=" * 60)
    logger.info(f"Starting air quality ingestion from Open-Meteo")
    logger.info(f"City: {city}")
    logger.info(f"Past days: {past_days}, Forecast days: {forecast_days}")
    logger.info(f"Execution date: {execution_date}")
    logger.info("=" * 60)
    
    # Paso 1: Obtener datos de la API
    logger.info("Step 1: Fetching data from Open-Meteo API...")
    data = fetch_air_quality_data(
        city_name=city,
        past_days=past_days,
        forecast_days=forecast_days
    )
    
    hourly = data.get("hourly", {})
    num_records = len(hourly.get("time", []))
    logger.info(f"Fetched {num_records} hourly records")
    
    # Mostrar muestra de datos
    if num_records > 0:
        times = hourly.get("time", [])
        pm25 = hourly.get("pm2_5", [])
        logger.info(f"Sample - First record: {times[0]}, PM2.5: {pm25[0]} μg/m³")
        logger.info(f"Sample - Last record: {times[-1]}, PM2.5: {pm25[-1]} μg/m³")
    
    # Paso 2: Guardar datos crudos
    logger.info("Step 2: Saving raw data to filesystem...")
    filepath = save_raw_data(data=data, city=city)
    
    logger.info(f"Data saved to: {filepath}")
    
    # Preparar resultado para XCom
    result = {
        "city": city,
        "records_fetched": num_records,
        "filepath": filepath,
        "execution_date": str(execution_date),
        "api_source": "open-meteo",
    }
    
    logger.info("=" * 60)
    logger.info("Ingestion completed successfully!")
    logger.info(f"Result: {result}")
    logger.info("=" * 60)
    
    return result


# =============================================================================
# Argumentos por defecto
# =============================================================================

default_args = {
    "owner": "mlops-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


# =============================================================================
# Definición del DAG
# =============================================================================

with DAG(
    dag_id="ingest_air_quality",
    description="Ingesta datos de calidad del aire desde Open-Meteo API (gratuita)",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval="@hourly",
    catchup=False,
    tags=["ingestion", "open-meteo", "air-quality", "raw-data"],
    doc_md=__doc__,
) as dag:
    
    fetch_and_save = PythonOperator(
        task_id="fetch_and_save",
        python_callable=ingest_air_quality_task,
        op_kwargs={
            "city": DEFAULT_CITY,
            "past_days": DEFAULT_PAST_DAYS,
            "forecast_days": DEFAULT_FORECAST_DAYS,
        },
        doc_md="""
        ### Fetch and Save Air Quality Data
        
        Obtiene datos de Open-Meteo y los guarda en JSON.
        
        **API**: Open-Meteo Air Quality (gratuita, sin API key)
        
        **Parámetros:**
        - city: Buenos_Aires
        - past_days: 7 (datos históricos)
        - forecast_days: 1
        
        **Output (XCom):**
        - records_fetched: Número de registros horarios
        - filepath: Ruta del archivo guardado
        """,
    )
    
    fetch_and_save
