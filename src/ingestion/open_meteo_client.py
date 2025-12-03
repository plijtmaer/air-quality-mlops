"""
Cliente para la API de Open-Meteo Air Quality
==============================================

Open-Meteo es una API gratuita y de código abierto que proporciona datos
de calidad del aire basados en modelos de predicción.

API Docs: https://open-meteo.com/en/docs/air-quality-api

Características:
    - 100% gratuita, sin límites de uso
    - No requiere autenticación ni API key
    - Datos horarios de PM2.5, PM10, NO2, O3, etc.
    - Cobertura global basada en coordenadas

Este módulo provee funciones para:
1. Obtener datos de calidad del aire por coordenadas
2. Guardar los datos crudos en formato JSON

Uso:
    from src.ingestion.open_meteo_client import fetch_air_quality_data, save_raw_data
    
    # Buenos Aires
    data = fetch_air_quality_data(latitude=-34.6, longitude=-58.4, city_name="Buenos_Aires")
    filepath = save_raw_data(data, city="Buenos_Aires")

Autor: MLOps Team
Proyecto: air-quality-mlops
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Configurar logging
logger = logging.getLogger(__name__)

# =============================================================================
# Configuración
# =============================================================================

# URL base de la API de Open-Meteo Air Quality
OPEN_METEO_BASE_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Ruta base donde se guardan los datos crudos (relativa al root del proyecto)
# Dentro de Docker, esto será /opt/airflow/data/raw
DATA_RAW_PATH = Path("/opt/airflow/data/raw")

# Ciudades predefinidas con sus coordenadas
CITIES = {
    "Buenos_Aires": {"latitude": -34.6037, "longitude": -58.3816},
    "Santiago": {"latitude": -33.4489, "longitude": -70.6693},
    "Lima": {"latitude": -12.0464, "longitude": -77.0428},
    "Bogota": {"latitude": 4.7110, "longitude": -74.0721},
    "Mexico_City": {"latitude": 19.4326, "longitude": -99.1332},
    "Sao_Paulo": {"latitude": -23.5505, "longitude": -46.6333},
}


# =============================================================================
# Funciones públicas
# =============================================================================

def fetch_air_quality_data(
    latitude: float = None,
    longitude: float = None,
    city_name: str = "Buenos_Aires",
    forecast_days: int = 1,
    past_days: int = 7,
    timeout: int = 30
) -> dict:
    """
    Obtiene datos de calidad del aire desde la API de Open-Meteo.
    
    Args:
        latitude: Latitud de la ubicación (opcional si city_name está definido)
        longitude: Longitud de la ubicación (opcional si city_name está definido)
        city_name: Nombre de la ciudad (usa coordenadas predefinidas si lat/lon no se especifican)
        forecast_days: Días de pronóstico (1-7)
        past_days: Días históricos a incluir (0-92)
        timeout: Tiempo máximo de espera en segundos
    
    Returns:
        dict: Respuesta de la API con estructura:
            {
                "latitude": float,
                "longitude": float,
                "timezone": str,
                "hourly_units": {"time": "iso8601", "pm2_5": "μg/m³", ...},
                "hourly": {
                    "time": ["2025-01-01T00:00", ...],
                    "pm2_5": [10.3, ...],
                    "pm10": [15.2, ...],
                    ...
                },
                "city_name": str  # Agregado por nosotros
            }
    
    Raises:
        ValueError: Si no se especifican coordenadas ni ciudad válida
        ConnectionError: Si no se puede conectar a la API
        RuntimeError: Si la API devuelve un error
    """
    # Obtener coordenadas
    if latitude is None or longitude is None:
        if city_name not in CITIES:
            raise ValueError(
                f"Ciudad '{city_name}' no encontrada. "
                f"Ciudades disponibles: {list(CITIES.keys())}. "
                "O especifica latitude y longitude manualmente."
            )
        coords = CITIES[city_name]
        latitude = coords["latitude"]
        longitude = coords["longitude"]
    
    # Construir URL con parámetros
    params = [
        f"latitude={latitude}",
        f"longitude={longitude}",
        f"hourly=pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,us_aqi,european_aqi",
        f"forecast_days={forecast_days}",
        f"past_days={past_days}",
        "timezone=auto",
    ]
    url = f"{OPEN_METEO_BASE_URL}?{'&'.join(params)}"
    
    logger.info(f"Fetching air quality data from Open-Meteo")
    logger.info(f"City: {city_name}, Lat: {latitude}, Lon: {longitude}")
    logger.debug(f"URL: {url}")
    
    try:
        # Crear request
        request = Request(
            url,
            headers={
                "User-Agent": "air-quality-mlops/1.0",
                "Accept": "application/json"
            }
        )
        
        # Hacer la petición
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Open-Meteo API returned status {response.status}: {response.reason}"
                )
            
            raw_data = response.read().decode("utf-8")
            data = json.loads(raw_data)
            
            # Agregar metadatos
            data["city_name"] = city_name
            data["fetch_timestamp"] = datetime.utcnow().isoformat()
            
            # Log de éxito
            num_hours = len(data.get("hourly", {}).get("time", []))
            logger.info(f"Successfully fetched {num_hours} hourly records for {city_name}")
            
            return data
            
    except HTTPError as e:
        error_msg = f"HTTP Error {e.code} al llamar a Open-Meteo: {e.reason}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
        
    except URLError as e:
        error_msg = f"Error de conexión a Open-Meteo: {e.reason}"
        logger.error(error_msg)
        raise ConnectionError(error_msg) from e
        
    except json.JSONDecodeError as e:
        error_msg = f"Error parseando respuesta JSON de Open-Meteo: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def save_raw_data(
    data: dict,
    city: str,
    base_path: Optional[Path] = None
) -> str:
    """
    Guarda los datos crudos de calidad del aire en formato JSON.
    
    Los archivos se guardan con la estructura:
        {base_path}/{city}/{timestamp}.json
    
    Args:
        data: Dict con los datos a guardar
        city: Nombre de la ciudad (usado como nombre de carpeta)
        base_path: Ruta base donde guardar. Default: /opt/airflow/data/raw
    
    Returns:
        str: Ruta absoluta del archivo guardado
    
    Raises:
        ValueError: Si data no es un dict o city está vacío
        IOError: Si no se puede crear el directorio o escribir el archivo
    """
    if not isinstance(data, dict):
        raise ValueError("El parámetro 'data' debe ser un diccionario")
    
    if not city or not isinstance(city, str):
        raise ValueError("El parámetro 'city' debe ser un string no vacío")
    
    if base_path is None:
        base_path = DATA_RAW_PATH
    
    # Sanitizar nombre de ciudad
    city_safe = city.replace(" ", "_").replace("/", "_").replace("\\", "_")
    
    # Generar timestamp
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    
    # Construir ruta
    city_dir = base_path / city_safe
    filepath = city_dir / f"{timestamp}.json"
    
    logger.info(f"Saving raw data to: {filepath}")
    
    try:
        city_dir.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        num_hours = len(data.get("hourly", {}).get("time", []))
        logger.info(f"Successfully saved {num_hours} hourly records to {filepath}")
        
        return str(filepath)
        
    except OSError as e:
        error_msg = f"Error de I/O al guardar datos en {filepath}: {e}"
        logger.error(error_msg)
        raise IOError(error_msg) from e


def get_available_cities() -> dict:
    """
    Devuelve las ciudades disponibles con coordenadas predefinidas.
    
    Returns:
        dict: Diccionario {city_name: {latitude, longitude}}
    """
    return CITIES.copy()


# =============================================================================
# Ejecución directa (para testing)
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    print("=" * 60)
    print("Testing Open-Meteo Air Quality Client")
    print("=" * 60)
    
    try:
        # Obtener datos
        data = fetch_air_quality_data(city_name="Buenos_Aires", past_days=1)
        
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        pm25 = hourly.get("pm2_5", [])
        
        print(f"\n✅ Obtenidos {len(times)} registros horarios")
        
        if times and pm25:
            print(f"\nMuestra de datos:")
            for i in range(min(5, len(times))):
                print(f"  {times[i]}: PM2.5 = {pm25[i]} μg/m³")
        
        # Guardar (path local para testing)
        local_path = Path("./data/raw")
        filepath = save_raw_data(data, "Buenos_Aires", base_path=local_path)
        print(f"\n✅ Datos guardados en: {filepath}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

