"""
Módulo de Transformación de Datos de Calidad del Aire con PySpark
==================================================================

Este módulo transforma los datos crudos (JSON) de Open-Meteo
en un dataset tabular curado listo para entrenar modelos de ML.

Pipeline de transformación:
    1. Cargar JSONs crudos de data/raw/{city}/
    2. Expandir datos horarios en filas individuales
    3. Seleccionar columnas relevantes (PM2.5, PM10, timestamps)
    4. Agregar etiqueta de calidad del aire (clasificación)
    5. Guardar como Parquet en data/curated/

Formato de entrada (Open-Meteo):
    {
        "latitude": -34.6,
        "longitude": -58.4,
        "city_name": "Buenos_Aires",
        "hourly": {
            "time": ["2025-01-01T00:00", ...],
            "pm2_5": [10.3, ...],
            "pm10": [15.2, ...],
            "us_aqi": [42, ...]
        }
    }

Clasificación de calidad del aire (basada en EPA AQI para PM2.5):
    - good:      value < 12 μg/m³
    - moderate:  12 <= value < 35.4 μg/m³
    - unhealthy: value >= 35.4 μg/m³

Autor: MLOps Team
Proyecto: air-quality-mlops
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from pyspark.sql import SparkSession, DataFrame

logger = logging.getLogger(__name__)

# =============================================================================
# Configuración
# =============================================================================

DATA_RAW_PATH = Path("/opt/airflow/data/raw")
DATA_CURATED_PATH = Path("/opt/airflow/data/curated")

# Umbrales EPA AQI para PM2.5 (μg/m³)
PM25_GOOD_THRESHOLD = 12.0
PM25_MODERATE_THRESHOLD = 35.4


# =============================================================================
# Funciones de Transformación
# =============================================================================

def get_spark_session(app_name: str = "AirQualityTransform") -> "SparkSession":
    """
    Crea o reutiliza una SparkSession en modo local.
    """
    from pyspark.sql import SparkSession
    
    logger.info(f"Creating SparkSession: {app_name}")
    
    spark = (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    
    spark.sparkContext.setLogLevel("WARN")
    logger.info(f"SparkSession created: Spark {spark.version}")
    
    return spark


def load_raw_files_to_spark(
    spark: "SparkSession",
    city: str,
    base_path: Path = DATA_RAW_PATH
) -> "DataFrame":
    """
    Carga todos los archivos JSON de Open-Meteo para una ciudad.
    """
    city_path = base_path / city
    
    logger.info(f"Loading raw data from: {city_path}")
    
    if not city_path.exists():
        raise ValueError(
            f"No raw data found for city '{city}'. "
            f"Path does not exist: {city_path}"
        )
    
    json_files = list(city_path.glob("*.json"))
    if not json_files:
        raise ValueError(
            f"No JSON files found for city '{city}' in {city_path}. "
            "Run the ingestion DAG first."
        )
    
    logger.info(f"Found {len(json_files)} JSON files")
    
    # Leer todos los JSON
    df = spark.read.option("multiline", "true").json(str(city_path))
    
    logger.info(f"Loaded {df.count()} JSON documents")
    
    return df


def transform_open_meteo_data(df: "DataFrame") -> "DataFrame":
    """
    Transforma los datos de Open-Meteo de formato anidado a tabular.
    
    Open-Meteo devuelve datos en formato:
    {
        "city_name": "Buenos_Aires",
        "latitude": -34.6,
        "longitude": -58.4,
        "hourly": {
            "time": ["2025-01-01T00:00", ...],
            "pm2_5": [10.3, ...],
            "pm10": [15.2, ...]
        }
    }
    
    Transformamos a filas individuales:
    | city | latitude | longitude | timestamp | pm2_5 | pm10 | ... |
    """
    from pyspark.sql.functions import (
        col, explode, arrays_zip, to_timestamp, lit
    )
    
    logger.info("Transforming Open-Meteo data to tabular format")
    
    # Crear un array de structs con time y valores
    # Esto nos permite explotar todos los arrays juntos
    df_with_arrays = df.select(
        col("city_name"),
        col("latitude"),
        col("longitude"),
        col("timezone"),
        # Zipear los arrays para poder explode juntos
        arrays_zip(
            col("hourly.time"),
            col("hourly.pm2_5"),
            col("hourly.pm10"),
            col("hourly.carbon_monoxide"),
            col("hourly.nitrogen_dioxide"),
            col("hourly.sulphur_dioxide"),
            col("hourly.ozone"),
            col("hourly.us_aqi"),
            col("hourly.european_aqi")
        ).alias("hourly_zipped")
    )
    
    # Explotar el array zipped
    df_exploded = df_with_arrays.select(
        col("city_name").alias("city"),
        col("latitude"),
        col("longitude"),
        col("timezone"),
        explode(col("hourly_zipped")).alias("hourly_data")
    )
    
    # Extraer los campos del struct
    # arrays_zip nombra los campos según los nombres de las columnas de entrada
    df_flat = df_exploded.select(
        col("city"),
        col("latitude"),
        col("longitude"),
        col("timezone"),
        to_timestamp(col("hourly_data.time")).alias("timestamp"),
        col("hourly_data.pm2_5").alias("pm2_5"),
        col("hourly_data.pm10").alias("pm10"),
        col("hourly_data.carbon_monoxide").alias("carbon_monoxide"),
        col("hourly_data.nitrogen_dioxide").alias("nitrogen_dioxide"),
        col("hourly_data.sulphur_dioxide").alias("sulphur_dioxide"),
        col("hourly_data.ozone").alias("ozone"),
        col("hourly_data.us_aqi").alias("us_aqi"),
        col("hourly_data.european_aqi").alias("european_aqi"),
        lit("pm2_5").alias("parameter"),  # Para compatibilidad
    )
    
    row_count = df_flat.count()
    logger.info(f"Transformed to {row_count} rows")
    
    return df_flat


def add_quality_label(df: "DataFrame") -> "DataFrame":
    """
    Agrega una columna de clasificación de calidad del aire basada en PM2.5.
    
    Clasificación EPA AQI para PM2.5:
        - good:      value < 12 μg/m³
        - moderate:  12 <= value < 35.4 μg/m³
        - unhealthy: value >= 35.4 μg/m³
        - unknown:   value es NULL
    """
    from pyspark.sql.functions import col, when, lit
    
    logger.info("Adding air quality classification labels based on PM2.5")
    
    df_labeled = df.withColumn(
        "air_quality_label",
        when(col("pm2_5").isNull(), lit("unknown"))
        .when(col("pm2_5") < PM25_GOOD_THRESHOLD, lit("good"))
        .when(col("pm2_5") < PM25_MODERATE_THRESHOLD, lit("moderate"))
        .otherwise(lit("unhealthy"))
    )
    
    # Log distribución
    label_counts = df_labeled.groupBy("air_quality_label").count().collect()
    for row in label_counts:
        logger.info(f"  {row['air_quality_label']}: {row['count']} records")
    
    return df_labeled


def deduplicate_data(df: "DataFrame") -> "DataFrame":
    """
    Elimina duplicados basados en city + timestamp.
    
    Como podemos tener múltiples archivos JSON con datos superpuestos,
    eliminamos duplicados manteniendo la última versión.
    """
    from pyspark.sql.functions import col, row_number
    from pyspark.sql.window import Window
    
    logger.info("Deduplicating data by city and timestamp")
    
    # Ventana para ordenar por timestamp descendente dentro de cada city+timestamp
    window = Window.partitionBy("city", "timestamp").orderBy(col("timestamp").desc())
    
    # Agregar número de fila y quedarse solo con la primera (más reciente)
    df_dedup = (
        df
        .withColumn("row_num", row_number().over(window))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )
    
    original_count = df.count()
    dedup_count = df_dedup.count()
    logger.info(f"Deduplicated: {original_count} -> {dedup_count} rows ({original_count - dedup_count} removed)")
    
    return df_dedup


def save_curated_dataset(
    df: "DataFrame",
    city: str,
    base_path: Path = DATA_CURATED_PATH
) -> str:
    """
    Guarda el DataFrame curado en formato Parquet.
    """
    logger.info(f"Saving curated dataset for city: {city}")
    
    base_path.mkdir(parents=True, exist_ok=True)
    
    output_path = base_path / f"{city}_air_quality.parquet"
    
    df.write.mode("overwrite").parquet(str(output_path))
    
    row_count = df.count()
    logger.info(f"Saved {row_count} records to: {output_path}")
    
    return str(output_path)


# =============================================================================
# Función Orquestadora Principal
# =============================================================================

def run_air_quality_transform(city: str) -> str:
    """
    Ejecuta el pipeline completo de transformación.
    
    Pipeline:
        1. Crear SparkSession
        2. Cargar JSONs de Open-Meteo
        3. Transformar a formato tabular
        4. Agregar etiquetas de clasificación
        5. Deduplicar
        6. Guardar como Parquet
    
    Args:
        city: Nombre de la ciudad a procesar
    
    Returns:
        str: Ruta del dataset curado guardado
    """
    logger.info("=" * 60)
    logger.info(f"Starting air quality transformation for city: {city}")
    logger.info("=" * 60)
    
    spark = get_spark_session(app_name=f"AirQuality-{city}")
    
    try:
        # 1. Cargar datos crudos
        df_raw = load_raw_files_to_spark(spark, city)
        
        # 2. Transformar a formato tabular
        df_tabular = transform_open_meteo_data(df_raw)
        
        # 3. Agregar etiquetas de clasificación
        df_labeled = add_quality_label(df_tabular)
        
        # 4. Deduplicar
        df_dedup = deduplicate_data(df_labeled)
        
        # 5. Guardar
        output_path = save_curated_dataset(df_dedup, city)
        
        logger.info("=" * 60)
        logger.info("Transformation completed successfully!")
        logger.info(f"Output: {output_path}")
        logger.info("=" * 60)
        
        return output_path
        
    finally:
        spark.stop()
        logger.info("SparkSession stopped")


# =============================================================================
# Ejecución directa (para testing)
# =============================================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    city = sys.argv[1] if len(sys.argv) > 1 else "Buenos_Aires"
    
    print(f"\n{'='*60}")
    print(f"Running transformation for: {city}")
    print(f"{'='*60}\n")
    
    try:
        # Para ejecución local, usar paths relativos
        DATA_RAW_PATH = Path("./data/raw")
        DATA_CURATED_PATH = Path("./data/curated")
        
        output = run_air_quality_transform(city)
        print(f"\n✅ Success! Dataset saved to: {output}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
