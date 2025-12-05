"""
FastAPI Application - Air Quality Inference API
================================================

API REST para predicción de calidad del aire.

Endpoints:
- GET /health: Health check
- POST /predict: Predicción individual
- POST /predict/batch: Predicción en lote

Uso local:
    uvicorn src.inference.main:app --reload --host 0.0.0.0 --port 8000
    
Documentación:
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc (ReDoc)
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.inference.model import AirQualityPredictor, get_predictor
from src.inference.schemas import (
    AirQualityInput,
    AirQualityPrediction,
    BatchAirQualityInput,
    BatchAirQualityPrediction,
    ErrorResponse,
    HealthResponse,
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuración de la API
# =============================================================================

API_VERSION = "1.0.0"
API_TITLE = "Air Quality Classification API"
API_DESCRIPTION = """
## 🌬️ API de Clasificación de Calidad del Aire

Esta API permite predecir la categoría de calidad del aire
basándose en mediciones de contaminantes atmosféricos.

### Categorías de Calidad del Aire:
- **good**: Calidad del aire buena (PM2.5 < 12 μg/m³)
- **moderate**: Calidad del aire moderada (PM2.5 12-35 μg/m³)
- **unhealthy**: No saludable para grupos sensibles (PM2.5 35-55 μg/m³)
- **very_unhealthy**: No saludable (PM2.5 55-150 μg/m³)
- **hazardous**: Peligroso (PM2.5 > 150 μg/m³)

### Tecnologías:
- **FastAPI**: Framework web
- **PyCaret**: Modelo de ML
- **MLflow + DagsHub**: Tracking de experimentos
"""


# =============================================================================
# Lifespan Events
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Maneja el ciclo de vida de la aplicación.
    
    - Startup: Carga el modelo
    - Shutdown: Limpieza de recursos
    """
    # Startup
    logger.info("🚀 Iniciando API de Calidad del Aire...")
    try:
        predictor = get_predictor()
        logger.info(f"✅ Modelo cargado: {predictor.model_name}")
    except Exception as e:
        logger.error(f"❌ Error cargando modelo: {e}")
        # Permitir que la app inicie aunque falle el modelo
        # para que el health check pueda reportar el estado
    
    yield  # La aplicación está corriendo
    
    # Shutdown
    logger.info("👋 Apagando API...")


# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware para permitir requests desde frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Endpoints
# =============================================================================

@app.get(
    "/",
    summary="Root",
    description="Redirige a la documentación",
    tags=["General"],
)
async def root():
    """
    Endpoint raíz - información básica de la API.
    """
    return {
        "message": "🌬️ Air Quality Classification API",
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Verifica el estado de la API y el modelo",
    tags=["General"],
)
async def health_check():
    """
    Endpoint de health check.
    
    Retorna el estado de la API y si el modelo está cargado.
    """
    try:
        predictor = get_predictor()
        return HealthResponse(
            status="healthy",
            model_loaded=True,
            model_name=predictor.model_name or "Unknown",
            version=API_VERSION,
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            model_loaded=False,
            model_name="Not loaded",
            version=API_VERSION,
        )


@app.post(
    "/predict",
    response_model=AirQualityPrediction,
    responses={
        200: {"description": "Predicción exitosa"},
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
    summary="Predicción Individual",
    description="Predice la categoría de calidad del aire para una muestra",
    tags=["Prediction"],
)
async def predict(input_data: AirQualityInput):
    """
    Realiza una predicción de calidad del aire.
    
    Recibe las mediciones de contaminantes y retorna
    la categoría de calidad del aire predicha.
    """
    try:
        predictor = get_predictor()
        
        # Convertir input a diccionario
        features = input_data.model_dump()
        
        # Realizar predicción
        prediction, confidence, probabilities = predictor.predict(features)
        
        return AirQualityPrediction(
            prediction=prediction,
            confidence=confidence,
            probabilities=probabilities,
        )
        
    except FileNotFoundError as e:
        logger.error(f"Modelo no encontrado: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo no disponible. Ejecuta el pipeline de training primero."
        )
    except Exception as e:
        logger.error(f"Error en predicción: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post(
    "/predict/batch",
    response_model=BatchAirQualityPrediction,
    responses={
        200: {"description": "Predicciones exitosas"},
        500: {"model": ErrorResponse, "description": "Error interno"},
    },
    summary="Predicción en Lote",
    description="Predice la categoría de calidad del aire para múltiples muestras",
    tags=["Prediction"],
)
async def predict_batch(input_data: BatchAirQualityInput):
    """
    Realiza predicciones en lote.
    
    Recibe una lista de muestras y retorna las predicciones
    para cada una.
    """
    try:
        predictor = get_predictor()
        
        # Convertir inputs a lista de diccionarios
        samples = [sample.model_dump() for sample in input_data.samples]
        
        # Realizar predicciones
        results = predictor.predict_batch(samples)
        
        predictions = [
            AirQualityPrediction(
                prediction=pred,
                confidence=conf,
                probabilities=probs,
            )
            for pred, conf, probs in results
        ]
        
        return BatchAirQualityPrediction(
            predictions=predictions,
            total=len(predictions),
        )
        
    except FileNotFoundError as e:
        logger.error(f"Modelo no encontrado: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Modelo no disponible. Ejecuta el pipeline de training primero."
        )
    except Exception as e:
        logger.error(f"Error en predicción batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get(
    "/model/info",
    summary="Información del Modelo",
    description="Retorna información sobre el modelo cargado",
    tags=["Model"],
)
async def model_info():
    """
    Retorna información sobre el modelo actualmente cargado.
    """
    try:
        predictor = get_predictor()
        return predictor.get_model_info()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


# =============================================================================
# Monitoring Endpoints (Evidently)
# =============================================================================

@app.post(
    "/monitoring/drift",
    summary="Detectar Data Drift",
    description="Analiza si hay drift entre datos de referencia y datos actuales",
    tags=["Monitoring"],
)
async def detect_drift(input_data: BatchAirQualityInput):
    """
    Detecta data drift en un lote de datos.
    
    Compara las distribuciones de features entre los datos
    de entrenamiento (referencia) y los datos proporcionados.
    """
    try:
        import pandas as pd
        from src.monitoring.drift_detector import get_detector
        
        # Convertir input a DataFrame
        samples = [sample.model_dump() for sample in input_data.samples]
        current_data = pd.DataFrame(samples)
        
        # Detectar drift
        detector = get_detector()
        drift_results = detector.detect_drift(current_data)
        
        return drift_results
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Datos de referencia no disponibles: {e}"
        )
    except Exception as e:
        logger.error(f"Error detectando drift: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get(
    "/monitoring/reference-stats",
    summary="Estadísticas de Referencia",
    description="Retorna estadísticas de los datos de entrenamiento",
    tags=["Monitoring"],
)
async def reference_stats():
    """
    Retorna estadísticas descriptivas de los datos de referencia.
    """
    try:
        from src.monitoring.drift_detector import get_detector
        
        detector = get_detector()
        stats = detector.get_reference_stats()
        
        return stats
        
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Datos de referencia no disponibles: {e}"
        )
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post(
    "/monitoring/report",
    summary="Generar Reporte de Drift",
    description="Genera un reporte HTML completo de drift",
    tags=["Monitoring"],
)
async def generate_drift_report(input_data: BatchAirQualityInput):
    """
    Genera un reporte HTML de drift y lo guarda en reports/monitoring/.
    
    Retorna la ruta al archivo generado.
    """
    try:
        import pandas as pd
        from src.monitoring.drift_detector import get_detector
        
        # Convertir input a DataFrame
        samples = [sample.model_dump() for sample in input_data.samples]
        current_data = pd.DataFrame(samples)
        
        # Generar reporte
        detector = get_detector()
        report_path = detector.generate_report(current_data)
        
        return {
            "status": "success",
            "report_path": str(report_path),
            "message": f"Reporte generado exitosamente en {report_path}"
        }
        
    except Exception as e:
        logger.error(f"Error generando reporte: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.inference.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

