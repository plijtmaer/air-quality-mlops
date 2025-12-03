"""
Módulo de Ingestión de Datos
============================

Este módulo contiene clientes para obtener datos de APIs externas
de calidad del aire.

Componentes:
    - open_meteo_client: Cliente para Open-Meteo Air Quality API (recomendado)
    - openaq_client: Cliente para OpenAQ (deprecated - requiere API key)

Ejemplo:
    from src.ingestion.open_meteo_client import fetch_air_quality_data, save_raw_data
    
    data = fetch_air_quality_data(city_name="Buenos_Aires")
    filepath = save_raw_data(data, city="Buenos_Aires")
"""

# Cliente principal: Open-Meteo (gratuito, sin API key)
from src.ingestion.open_meteo_client import (
    fetch_air_quality_data,
    save_raw_data,
    get_available_cities,
)

__all__ = [
    "fetch_air_quality_data",
    "save_raw_data",
    "get_available_cities",
]
