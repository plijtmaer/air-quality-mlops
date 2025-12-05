"""
Carga y Predicción del Modelo
=============================

Este módulo maneja la carga del modelo entrenado
y las predicciones.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# =============================================================================
# Configuración
# =============================================================================

# Path al modelo entrenado (relativo a la raíz del proyecto)
MODEL_DIR = Path("models")

# Features esperadas por el modelo (en orden)
FEATURE_COLUMNS = [
    "pm2_5", "pm10",
    "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide", "ozone",
    "us_aqi", "european_aqi",
]

# Clases de calidad del aire
AIR_QUALITY_CLASSES = ["good", "moderate", "unhealthy", "very_unhealthy", "hazardous"]


class AirQualityPredictor:
    """
    Clase para manejar predicciones de calidad del aire.
    
    Carga el modelo entrenado con PyCaret y proporciona
    métodos para hacer predicciones individuales o en lote.
    """
    
    def __init__(self, model_path: Optional[Path] = None):
        """
        Inicializa el predictor cargando el modelo.
        
        Args:
            model_path: Path al archivo .pkl del modelo.
                       Si es None, busca el modelo más reciente en MODEL_DIR.
        """
        self.model = None
        self.model_name = None
        self.model_path = model_path
        self._load_model()
    
    def _find_latest_model(self) -> Path:
        """
        Encuentra el modelo más reciente en el directorio de modelos.
        
        Returns:
            Path al archivo .pkl más reciente.
            
        Raises:
            FileNotFoundError: Si no hay modelos disponibles.
        """
        model_files = list(MODEL_DIR.glob("*.pkl"))
        
        if not model_files:
            raise FileNotFoundError(
                f"No se encontraron modelos en {MODEL_DIR}. "
                "Ejecuta el pipeline de training primero."
            )
        
        # Ordenar por fecha de modificación (más reciente primero)
        model_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        return model_files[0]
    
    def _load_model(self):
        """
        Carga el modelo desde disco.
        
        El modelo fue guardado con PyCaret usando save_model(),
        así que usamos load_model() para cargarlo.
        """
        try:
            # Si no se especificó path, buscar el más reciente
            if self.model_path is None:
                self.model_path = self._find_latest_model()
            
            logger.info(f"Cargando modelo desde: {self.model_path}")
            
            # PyCaret guarda los modelos con .pkl, pero save_model() no añade extensión
            # load_model() espera el path sin extensión
            from pycaret.classification import load_model
            
            # Remover extensión .pkl si existe
            model_path_str = str(self.model_path)
            if model_path_str.endswith('.pkl'):
                model_path_str = model_path_str[:-4]
            
            self.model = load_model(model_path_str)
            self.model_name = type(self.model).__name__
            
            logger.info(f"Modelo cargado: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")
            raise
    
    def predict(self, features: Dict[str, float]) -> Tuple[str, Optional[float], Optional[Dict[str, float]]]:
        """
        Realiza una predicción individual.
        
        Args:
            features: Diccionario con las features del input.
            
        Returns:
            Tupla con (predicción, confianza, probabilidades_por_clase)
        """
        if self.model is None:
            raise RuntimeError("Modelo no cargado")
        
        # Crear DataFrame con las features en el orden correcto
        df = pd.DataFrame([features])
        
        # Asegurar que tenemos todas las columnas necesarias
        for col in FEATURE_COLUMNS:
            if col not in df.columns:
                df[col] = 0  # Valor por defecto si falta
        
        # Reordenar columnas
        df = df[FEATURE_COLUMNS]
        
        # Realizar predicción
        from pycaret.classification import predict_model
        
        predictions = predict_model(self.model, data=df)
        
        # Extraer resultados
        # PyCaret añade columnas: 'prediction_label' y 'prediction_score'
        prediction = predictions['prediction_label'].iloc[0]
        
        # Intentar obtener la confianza
        confidence = None
        probabilities = None
        
        if 'prediction_score' in predictions.columns:
            confidence = float(predictions['prediction_score'].iloc[0])
        
        # Intentar obtener probabilidades por clase
        try:
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(df[FEATURE_COLUMNS])
                if hasattr(self.model, 'classes_'):
                    probabilities = {
                        str(cls): float(prob) 
                        for cls, prob in zip(self.model.classes_, proba[0])
                    }
        except Exception:
            pass  # No todas las implementaciones soportan predict_proba
        
        return str(prediction), confidence, probabilities
    
    def predict_batch(self, samples: List[Dict[str, float]]) -> List[Tuple[str, Optional[float], Optional[Dict[str, float]]]]:
        """
        Realiza predicciones en lote.
        
        Args:
            samples: Lista de diccionarios con features.
            
        Returns:
            Lista de tuplas (predicción, confianza, probabilidades)
        """
        if self.model is None:
            raise RuntimeError("Modelo no cargado")
        
        # Crear DataFrame con todas las muestras
        df = pd.DataFrame(samples)
        
        # Asegurar columnas
        for col in FEATURE_COLUMNS:
            if col not in df.columns:
                df[col] = 0
        
        df = df[FEATURE_COLUMNS]
        
        # Predicción en lote
        from pycaret.classification import predict_model
        
        predictions = predict_model(self.model, data=df)
        
        results = []
        for i in range(len(predictions)):
            prediction = str(predictions['prediction_label'].iloc[i])
            confidence = None
            probabilities = None
            
            if 'prediction_score' in predictions.columns:
                confidence = float(predictions['prediction_score'].iloc[i])
            
            results.append((prediction, confidence, probabilities))
        
        return results
    
    def get_model_info(self) -> Dict:
        """
        Retorna información sobre el modelo cargado.
        """
        return {
            "model_name": self.model_name,
            "model_path": str(self.model_path),
            "features": FEATURE_COLUMNS,
            "classes": AIR_QUALITY_CLASSES,
        }


# Singleton para la aplicación
_predictor: Optional[AirQualityPredictor] = None


def get_predictor() -> AirQualityPredictor:
    """
    Obtiene la instancia singleton del predictor.
    
    Returns:
        Instancia de AirQualityPredictor
    """
    global _predictor
    if _predictor is None:
        _predictor = AirQualityPredictor()
    return _predictor

