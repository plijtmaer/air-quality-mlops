"""
Paquete src - Código fuente del proyecto air-quality-mlops
===========================================================

Este paquete contiene todos los módulos de Python del proyecto:

- ingestion/   : Clientes para obtener datos de APIs externas
- transform/   : Transformación y feature engineering
- training/    : Scripts de entrenamiento ML (PyCaret, Optuna)
- inference/   : API de inferencia (FastAPI)
- monitoring/  : Reportes de drift (Evidently)
- utils/       : Utilidades compartidas

Uso desde Airflow:
    from src.ingestion.openaq_client import fetch_air_quality_data
"""

