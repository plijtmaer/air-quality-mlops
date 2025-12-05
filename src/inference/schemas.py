"""
Schemas Pydantic para la API de Inferencia
==========================================

Define los modelos de datos para request y response.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class AirQualityInput(BaseModel):
    """
    Input para predicción de calidad del aire.
    
    Contiene las mediciones de contaminantes necesarias
    para predecir la categoría de calidad del aire.
    """
    
    pm2_5: float = Field(
        ...,
        description="Partículas PM2.5 (μg/m³)",
        ge=0,
        example=15.5
    )
    pm10: float = Field(
        ...,
        description="Partículas PM10 (μg/m³)",
        ge=0,
        example=25.0
    )
    carbon_monoxide: float = Field(
        ...,
        description="Monóxido de carbono (μg/m³)",
        ge=0,
        example=200.0
    )
    nitrogen_dioxide: float = Field(
        ...,
        description="Dióxido de nitrógeno (μg/m³)",
        ge=0,
        example=10.5
    )
    sulphur_dioxide: float = Field(
        ...,
        description="Dióxido de azufre (μg/m³)",
        ge=0,
        example=5.0
    )
    ozone: float = Field(
        ...,
        description="Ozono (μg/m³)",
        ge=0,
        example=50.0
    )
    us_aqi: Optional[int] = Field(
        None,
        description="Índice de Calidad del Aire US (0-500)",
        ge=0,
        le=500,
        example=42
    )
    european_aqi: Optional[int] = Field(
        None,
        description="Índice de Calidad del Aire Europeo (0-500)",
        ge=0,
        le=500,
        example=35
    )

    class Config:
        json_schema_extra = {
            "example": {
                "pm2_5": 15.5,
                "pm10": 25.0,
                "carbon_monoxide": 200.0,
                "nitrogen_dioxide": 10.5,
                "sulphur_dioxide": 5.0,
                "ozone": 50.0,
                "us_aqi": 42,
                "european_aqi": 35
            }
        }


class AirQualityPrediction(BaseModel):
    """
    Response con la predicción de calidad del aire.
    """
    
    prediction: str = Field(
        ...,
        description="Categoría de calidad del aire predicha",
        example="good"
    )
    confidence: Optional[float] = Field(
        None,
        description="Confianza de la predicción (0-1)",
        ge=0,
        le=1,
        example=0.95
    )
    probabilities: Optional[dict] = Field(
        None,
        description="Probabilidades por clase",
        example={"good": 0.95, "moderate": 0.04, "unhealthy": 0.01}
    )


class BatchAirQualityInput(BaseModel):
    """
    Input para predicción en lote.
    """
    
    samples: List[AirQualityInput] = Field(
        ...,
        description="Lista de muestras para predecir",
        min_length=1,
        max_length=1000
    )


class BatchAirQualityPrediction(BaseModel):
    """
    Response para predicción en lote.
    """
    
    predictions: List[AirQualityPrediction] = Field(
        ...,
        description="Lista de predicciones"
    )
    total: int = Field(
        ...,
        description="Total de predicciones realizadas",
        example=10
    )


class HealthResponse(BaseModel):
    """
    Response para el endpoint de health check.
    """
    
    status: str = Field(..., example="healthy")
    model_loaded: bool = Field(..., example=True)
    model_name: str = Field(..., example="DecisionTreeClassifier")
    version: str = Field(..., example="1.0.0")


class ErrorResponse(BaseModel):
    """
    Response para errores.
    """
    
    error: str = Field(..., description="Mensaje de error")
    detail: Optional[str] = Field(None, description="Detalle adicional")

