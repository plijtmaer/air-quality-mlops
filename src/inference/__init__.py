"""
Módulo de Inferencia - FastAPI API
==================================

Este módulo expone el modelo de clasificación de calidad del aire
a través de una API REST con FastAPI.

Estructura:
- main.py: Aplicación FastAPI y endpoints
- model.py: Carga y predicción del modelo
- schemas.py: Esquemas Pydantic para request/response
"""

from src.inference.model import AirQualityPredictor

__all__ = ["AirQualityPredictor"]

