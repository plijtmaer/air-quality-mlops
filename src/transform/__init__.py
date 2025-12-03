"""
Módulo de Transformación de Datos
==================================

Este módulo contiene funciones para transformar datos crudos en datasets
curados listos para entrenamiento de modelos de ML.

Componentes:
    - air_quality_transform: Pipeline de transformación con PySpark

Ejemplo:
    from src.transform.air_quality_transform import run_air_quality_transform
    
    output_path = run_air_quality_transform(city="Buenos_Aires")
"""

from src.transform.air_quality_transform import (
    get_spark_session,
    load_raw_files_to_spark,
    transform_open_meteo_data,
    add_quality_label,
    deduplicate_data,
    save_curated_dataset,
    run_air_quality_transform,
)

__all__ = [
    "get_spark_session",
    "load_raw_files_to_spark",
    "transform_open_meteo_data",
    "add_quality_label",
    "deduplicate_data",
    "save_curated_dataset",
    "run_air_quality_transform",
]
