"""
Módulo de Training para Air Quality MLOps.

Pipeline de entrenamiento que usa:
- PyCaret: AutoML para comparar modelos rápidamente
- Optuna: Optimización de hiperparámetros
- MLflow: Tracking de experimentos (integrado con DagsHub)
"""

from src.training.train import run_training_pipeline

__all__ = ["run_training_pipeline"]

