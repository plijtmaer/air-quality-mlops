"""
Cliente para la API de OpenAQ
==============================

OpenAQ es una plataforma abierta que proporciona datos de calidad del aire
de estaciones de monitoreo alrededor del mundo.

API Docs: https://docs.openaq.org/

Este módulo provee funciones para:
1. Obtener mediciones de calidad del aire por ciudad
2. Guardar los datos crudos en formato JSON

Uso:
    from src.ingestion.openaq_client import fetch_air_quality_data, save_raw_data
    
    # Obtener datos
    data = fetch_air_quality_data(city="Buenos Aires", limit=100)
    
    # Guardar en data/raw/
    filepath = save_raw_data(data, city="Buenos_Aires")

Notas:
    - La API de OpenAQ es gratuita y no requiere autenticación para uso básico
    - Límite de rate: ~100 requests/minuto (sin API key)
    - Los datos se actualizan aproximadamente cada hora

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

# URL base de la API de OpenAQ v2
OPENAQ_BASE_URL = "https://api.openaq.org/v2"

# Ruta base donde se guardan los datos crudos (relativa al root del proyecto)
# Dentro de Docker, esto será /opt/airflow/data/raw
DATA_RAW_PATH = Path("/opt/airflow/data/raw")


# =============================================================================
# Funciones públicas
# =============================================================================

def fetch_air_quality_data(
    city: str,
    limit: int = 100,
    timeout: int = 30
) -> dict:
    """
    Obtiene datos de calidad del aire desde la API de OpenAQ.
    
    Esta función hace una petición HTTP GET al endpoint de measurements
    de OpenAQ y devuelve los datos en formato dict.
    
    Args:
        city: Nombre de la ciudad (ej: "Buenos Aires", "Santiago", "Lima")
        limit: Número máximo de mediciones a obtener (default: 100, max: 10000)
        timeout: Tiempo máximo de espera en segundos (default: 30)
    
    Returns:
        dict: Respuesta completa de la API con la estructura:
            {
                "meta": {...},       # Metadatos de la respuesta
                "results": [...]     # Lista de mediciones
            }
    
    Raises:
        ValueError: Si los parámetros son inválidos
        ConnectionError: Si no se puede conectar a la API
        RuntimeError: Si la API devuelve un error (status != 200)
    
    Ejemplo:
        >>> data = fetch_air_quality_data("Buenos Aires", limit=50)
        >>> print(f"Obtenidas {len(data['results'])} mediciones")
    
    Notas sobre los datos devueltos:
        Cada medición en 'results' contiene:
        - location: Nombre de la estación
        - city: Ciudad
        - country: País (código ISO)
        - parameter: Tipo de contaminante (pm25, pm10, o3, no2, so2, co)
        - value: Valor de la medición
        - unit: Unidad de medida (µg/m³, ppm, etc.)
        - date: Fecha/hora de la medición (UTC y local)
    """
    # Validar parámetros
    if not city or not isinstance(city, str):
        raise ValueError("El parámetro 'city' debe ser un string no vacío")
    
    if not isinstance(limit, int) or limit < 1:
        raise ValueError("El parámetro 'limit' debe ser un entero positivo")
    
    if limit > 10000:
        logger.warning(f"limit={limit} es muy alto, OpenAQ limita a 10000. Ajustando.")
        limit = 10000
    
    # Construir URL con parámetros
    # Nota: urllib.parse.quote podría usarse para encoding, pero para ciudades
    # con espacios, simplemente los reemplazamos por %20
    city_encoded = city.replace(" ", "%20")
    url = f"{OPENAQ_BASE_URL}/measurements?city={city_encoded}&limit={limit}"
    
    logger.info(f"Fetching air quality data from OpenAQ: city={city}, limit={limit}")
    logger.debug(f"URL: {url}")
    
    try:
        # Crear request con User-Agent (algunas APIs lo requieren)
        request = Request(
            url,
            headers={
                "User-Agent": "air-quality-mlops/1.0",
                "Accept": "application/json"
            }
        )
        
        # Hacer la petición
        with urlopen(request, timeout=timeout) as response:
            # Verificar status code
            if response.status != 200:
                raise RuntimeError(
                    f"OpenAQ API returned status {response.status}: {response.reason}"
                )
            
            # Leer y parsear JSON
            raw_data = response.read().decode("utf-8")
            data = json.loads(raw_data)
            
            # Log de éxito
            num_results = len(data.get("results", []))
            logger.info(f"Successfully fetched {num_results} measurements for {city}")
            
            return data
            
    except HTTPError as e:
        error_msg = f"HTTP Error {e.code} al llamar a OpenAQ: {e.reason}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
        
    except URLError as e:
        error_msg = f"Error de conexión a OpenAQ: {e.reason}"
        logger.error(error_msg)
        raise ConnectionError(error_msg) from e
        
    except json.JSONDecodeError as e:
        error_msg = f"Error parseando respuesta JSON de OpenAQ: {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
        
    except Exception as e:
        error_msg = f"Error inesperado al obtener datos de OpenAQ: {e}"
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
    
    Donde timestamp tiene formato: YYYY-MM-DDTHH-MM-SS (ISO 8601 con - en vez de :)
    
    Args:
        data: Dict con los datos a guardar (típicamente la respuesta de la API)
        city: Nombre de la ciudad (se usa como nombre de carpeta)
        base_path: Ruta base donde guardar. Default: /opt/airflow/data/raw
    
    Returns:
        str: Ruta absoluta del archivo guardado (como string POSIX)
    
    Raises:
        ValueError: Si data no es un dict o city está vacío
        IOError: Si no se puede crear el directorio o escribir el archivo
    
    Ejemplo:
        >>> data = fetch_air_quality_data("Buenos Aires")
        >>> path = save_raw_data(data, "Buenos_Aires")
        >>> print(path)
        '/opt/airflow/data/raw/Buenos_Aires/2025-02-10T18-00-00.json'
    
    Notas:
        - Los espacios en el nombre de ciudad se reemplazan por guiones bajos
        - Se crean las carpetas automáticamente si no existen
        - El timestamp usa UTC para consistencia entre zonas horarias
    """
    # Validar parámetros
    if not isinstance(data, dict):
        raise ValueError("El parámetro 'data' debe ser un diccionario")
    
    if not city or not isinstance(city, str):
        raise ValueError("El parámetro 'city' debe ser un string no vacío")
    
    # Usar path por defecto si no se especifica
    if base_path is None:
        base_path = DATA_RAW_PATH
    
    # Sanitizar nombre de ciudad (reemplazar espacios y caracteres especiales)
    city_safe = city.replace(" ", "_").replace("/", "_").replace("\\", "_")
    
    # Generar timestamp UTC
    # Formato: 2025-02-10T18-00-00 (usamos - en vez de : para evitar problemas en Windows)
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
    
    # Construir ruta del archivo
    city_dir = base_path / city_safe
    filepath = city_dir / f"{timestamp}.json"
    
    logger.info(f"Saving raw data to: {filepath}")
    
    try:
        # Crear directorio si no existe
        city_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar JSON con indentación para legibilidad
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully saved {len(data.get('results', []))} records to {filepath}")
        
        # Devolver como string POSIX (con /)
        return str(filepath)
        
    except OSError as e:
        error_msg = f"Error de I/O al guardar datos en {filepath}: {e}"
        logger.error(error_msg)
        raise IOError(error_msg) from e
        
    except Exception as e:
        error_msg = f"Error inesperado al guardar datos: {e}"
        logger.error(error_msg)
        raise IOError(error_msg) from e


# =============================================================================
# Función auxiliar para ejecución directa (testing)
# =============================================================================

if __name__ == "__main__":
    # Configurar logging para pruebas locales
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Ejemplo de uso
    print("=" * 60)
    print("Testing OpenAQ Client")
    print("=" * 60)
    
    try:
        # Obtener datos
        data = fetch_air_quality_data("Buenos Aires", limit=10)
        print(f"\n✅ Obtenidas {len(data.get('results', []))} mediciones")
        
        # Mostrar muestra de datos
        if data.get("results"):
            sample = data["results"][0]
            print(f"\nMuestra de medición:")
            print(f"  - Location: {sample.get('location')}")
            print(f"  - Parameter: {sample.get('parameter')}")
            print(f"  - Value: {sample.get('value')} {sample.get('unit')}")
            print(f"  - Date: {sample.get('date', {}).get('utc')}")
        
        # Guardar (usar path local para testing)
        # En producción, usará /opt/airflow/data/raw
        local_path = Path("./data/raw")
        filepath = save_raw_data(data, "Buenos_Aires", base_path=local_path)
        print(f"\n✅ Datos guardados en: {filepath}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

