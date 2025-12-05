"""
Feature definitions for Air Quality MLOps project.

Este archivo define las features de calidad del aire que se usarán
tanto para training como para inference.
"""

from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, FileSource, Project, ValueType
from feast.types import Float32, Float64, Int64, String

# =============================================================================
# Proyecto
# =============================================================================

project = Project(
    name="air_quality_features",
    description="Features de calidad del aire para clasificación"
)

# =============================================================================
# Entidades
# =============================================================================

# La entidad principal es la ciudad (cada ciudad tiene sus mediciones)
city_entity = Entity(
    name="city",
    join_keys=["city"],
    value_type=ValueType.STRING,
    description="Ciudad donde se miden los datos de calidad del aire"
)

# =============================================================================
# Fuentes de Datos
# =============================================================================

# Fuente: Parquet curado con datos de calidad del aire
air_quality_source = FileSource(
    name="air_quality_parquet_source",
    path="../../../data/curated/Buenos_Aires_air_quality.parquet",
    timestamp_field="timestamp",
)

# =============================================================================
# Feature Views
# =============================================================================

# Features principales de calidad del aire
air_quality_features = FeatureView(
    name="air_quality_hourly",
    entities=[city_entity],
    ttl=timedelta(days=7),  # Los datos son válidos por 7 días
    schema=[
        # Partículas
        Field(name="pm2_5", dtype=Float32, description="PM2.5 (μg/m³)"),
        Field(name="pm10", dtype=Float32, description="PM10 (μg/m³)"),
        
        # Gases
        Field(name="carbon_monoxide", dtype=Float32, description="CO (μg/m³)"),
        Field(name="nitrogen_dioxide", dtype=Float32, description="NO2 (μg/m³)"),
        Field(name="sulphur_dioxide", dtype=Float32, description="SO2 (μg/m³)"),
        Field(name="ozone", dtype=Float32, description="O3 (μg/m³)"),
        
        # Índices de calidad
        Field(name="us_aqi", dtype=Int64, description="US Air Quality Index"),
        Field(name="european_aqi", dtype=Int64, description="European AQI"),
        
        # Coordenadas
        Field(name="latitude", dtype=Float64, description="Latitud"),
        Field(name="longitude", dtype=Float64, description="Longitud"),
        
        # Label (para training)
        Field(name="air_quality_label", dtype=String, description="Clasificación: good/moderate/unhealthy"),
    ],
    online=True,
    source=air_quality_source,
    tags={
        "team": "mlops",
        "project": "air-quality-classification",
    },
)

# =============================================================================
# Feature Services
# =============================================================================

# Servicio para training: todas las features + label
air_quality_training_service = FeatureService(
    name="air_quality_training",
    features=[air_quality_features],
    description="Features para entrenar modelo de clasificación de calidad del aire"
)

# Servicio para inference: solo features (sin label)
air_quality_inference_service = FeatureService(
    name="air_quality_inference",
    features=[
        air_quality_features[[
            "pm2_5", "pm10",
            "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide", "ozone",
            "us_aqi", "european_aqi",
        ]]
    ],
    description="Features para inference (predicción de calidad del aire)"
)

