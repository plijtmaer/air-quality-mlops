"""
DAG: transform_air_quality
===========================

Este DAG transforma los datos crudos de calidad del aire (JSON)
en un dataset curado (Parquet) listo para entrenar modelos de ML.

Pipeline de transformación (PySpark):
    1. Cargar JSONs de data/raw/{city}/
    2. Aplanar estructura anidada de OpenAQ
    3. Filtrar solo mediciones de PM2.5
    4. Agregar etiqueta de clasificación (good/moderate/unhealthy)
    5. Guardar como Parquet en data/curated/{city}_air_quality.parquet

Dependencias:
    - Requiere datos en data/raw/ (ejecutar primero ingest_air_quality)
    - Requiere PySpark instalado en el worker

Programación:
    - Ejecuta cada 6 horas
    - Depende de que haya datos de ingesta disponibles

Configuración:
    - Ciudad: Buenos_Aires (hardcodeada por ahora)
    - En el futuro, se puede parametrizar via Airflow Variables

Output:
    - data/curated/{city}_air_quality.parquet
    - Columnas: city, location, parameter, value, unit, date_utc,
                latitude, longitude, air_quality_label

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
# Airflow monta el código en /opt/airflow/src
sys.path.insert(0, "/opt/airflow")

# Logger para este DAG
logger = logging.getLogger(__name__)

# =============================================================================
# Configuración del DAG
# =============================================================================

# Ciudad a procesar (TODO: mover a Airflow Variables)
DEFAULT_CITY = "Buenos_Aires"


# =============================================================================
# Funciones del DAG
# =============================================================================

def transform_air_quality_task(city: str = DEFAULT_CITY, **context) -> dict:
    """
    Tarea de transformación: convierte datos crudos en dataset curado.
    
    Esta función es el wrapper que llama al pipeline de PySpark
    desde el contexto de Airflow.
    
    Args:
        city: Nombre de la ciudad a procesar
        **context: Contexto de Airflow
    
    Returns:
        dict: Información sobre la transformación para XCom
            {
                "city": str,
                "output_path": str,
                "execution_date": str
            }
    
    Raises:
        ValueError: Si no hay datos crudos para la ciudad
        ImportError: Si PySpark no está instalado
    """
    # Importar aquí para que el error sea más claro si PySpark no está disponible
    try:
        from src.transform.air_quality_transform import run_air_quality_transform
    except ImportError as e:
        logger.error(
            "Failed to import transform module. "
            "Make sure PySpark is installed (add 'pyspark' to _PIP_ADDITIONAL_REQUIREMENTS)"
        )
        raise
    
    execution_date = context.get("execution_date", datetime.utcnow())
    
    logger.info("=" * 60)
    logger.info("Starting air quality transformation task")
    logger.info(f"City: {city}")
    logger.info(f"Execution date: {execution_date}")
    logger.info("=" * 60)
    
    # Ejecutar pipeline de transformación
    output_path = run_air_quality_transform(city=city)
    
    # Preparar resultado para XCom
    result = {
        "city": city,
        "output_path": output_path,
        "execution_date": str(execution_date),
    }
    
    logger.info("=" * 60)
    logger.info("Transformation completed successfully!")
    logger.info(f"Result: {result}")
    logger.info("=" * 60)
    
    return result


# =============================================================================
# Argumentos por defecto para las tareas
# =============================================================================

default_args = {
    "owner": "mlops-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# =============================================================================
# Definición del DAG
# =============================================================================

with DAG(
    dag_id="transform_air_quality",
    description="Transforma datos crudos de calidad del aire en dataset curado con PySpark",
    default_args=default_args,
    
    # Fecha de inicio
    start_date=datetime(2024, 1, 1),
    
    # Programación: cada 6 horas
    # Alternativas:
    #   "@daily"       - Una vez al día
    #   "0 */6 * * *"  - Cada 6 horas (cron)
    #   None           - Solo manual (útil para desarrollo)
    schedule_interval="0 */6 * * *",
    
    # No ejecutar DAGs para fechas pasadas
    catchup=False,
    
    # Tags para organizar en la UI
    tags=["transform", "pyspark", "air-quality", "curated-data"],
    
    # Documentación que aparece en la UI
    doc_md=__doc__,
    
) as dag:
    
    # -------------------------------------------------------------------------
    # Tarea: run_transform
    # -------------------------------------------------------------------------
    # Ejecuta el pipeline de transformación con PySpark
    # -------------------------------------------------------------------------
    
    run_transform = PythonOperator(
        task_id="run_transform",
        python_callable=transform_air_quality_task,
        
        # Argumentos para la función
        op_kwargs={
            "city": DEFAULT_CITY,
        },
        
        # Documentación de la tarea
        doc_md="""
        ### Run Air Quality Transformation
        
        Ejecuta el pipeline de transformación con PySpark:
        
        1. Lee JSONs de `data/raw/Buenos_Aires/`
        2. Aplana estructura y filtra PM2.5
        3. Clasifica calidad (good/moderate/unhealthy)
        4. Guarda Parquet en `data/curated/Buenos_Aires_air_quality.parquet`
        
        **Requiere:**
        - PySpark instalado (`pyspark` en _PIP_ADDITIONAL_REQUIREMENTS)
        - Datos de ingesta disponibles (ejecutar `ingest_air_quality` primero)
        
        **Output (XCom):**
        - output_path: Ruta del archivo Parquet generado
        """,
    )
    
    # Por ahora solo tenemos una tarea.
    # En el futuro podemos agregar:
    #   - validate_data: Verificar schema y calidad del Parquet
    #   - update_feature_store: Actualizar Feast con nuevas features
    #   - trigger_training: Disparar DAG de entrenamiento
    
    run_transform

