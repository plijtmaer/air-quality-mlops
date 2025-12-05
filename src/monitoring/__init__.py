"""
Módulo de Monitoreo - Evidently
===============================

Este módulo implementa monitoreo de data drift y model drift
usando Evidently AI.

Funcionalidades:
- Detección de data drift en features
- Detección de target drift
- Generación de reportes HTML
- Integración con FastAPI
"""

from src.monitoring.drift_detector import DriftDetector

__all__ = ["DriftDetector"]

