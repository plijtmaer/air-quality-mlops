# 🌬️ Air Quality MLOps

Proyecto de MLOps end-to-end para clasificación de calidad del aire, desarrollado como trabajo final de posgrado.

## 📋 Descripción

Pipeline completo de Machine Learning Operations que:
1. **Ingesta** datos de calidad del aire desde Open-Meteo API
2. **Transforma** los datos crudos usando PySpark
3. **Entrena** modelos de clasificación (próximamente)
4. **Despliega** una API de inferencia (próximamente)
5. **Monitorea** el drift de datos (próximamente)

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Orquestación | Apache Airflow 2.10 |
| Contenedores | Docker & Docker Compose |
| Transformación | PySpark (local mode) |
| Entrenamiento | PyCaret + Optuna (próximamente) |
| Tracking ML | MLflow (próximamente) |
| API | FastAPI (próximamente) |
| Monitoreo | Evidently (próximamente) |
| CI/CD | GitHub Actions (próximamente) |

## 📁 Estructura del Proyecto

```
air-quality-mlops/
├── airflow/                    # Configuración de Apache Airflow
│   ├── dags/                   # Definiciones de DAGs
│   │   ├── hello_airflow.py    # DAG de prueba
│   │   ├── ingest_air_quality.py
│   │   └── transform_air_quality.py
│   ├── logs/                   # Logs de ejecución (gitignore)
│   ├── plugins/                # Plugins personalizados
│   ├── docker-compose.yaml     # Servicios Docker
│   ├── Dockerfile              # Imagen custom con Java+PySpark
│   ├── .env                    # Variables de entorno
│   └── README.md               # Documentación de Airflow
│
├── src/                        # Código fuente Python
│   ├── ingestion/              # Módulo de ingesta
│   │   ├── __init__.py
│   │   └── open_meteo_client.py
│   ├── transform/              # Módulo de transformación
│   │   ├── __init__.py
│   │   └── air_quality_transform.py
│   ├── training/               # (próximamente)
│   ├── inference/              # (próximamente)
│   └── monitoring/             # (próximamente)
│
├── data/                       # Datos (gitignore excepto .gitkeep)
│   ├── raw/                    # JSON crudos de la API
│   │   └── Buenos_Aires/
│   ├── stg/                    # Staging (no usado actualmente)
│   └── curated/                # Parquet procesados
│       └── Buenos_Aires_air_quality.parquet/
│
├── mlflow/                     # Artefactos de MLflow (próximamente)
├── notebooks/                  # Jupyter notebooks de exploración
├── .github/workflows/          # GitHub Actions (próximamente)
├── .gitignore
├── .gitattributes
└── README.md                   # Este archivo
```

## 🚀 Inicio Rápido

### Requisitos Previos

- Docker Desktop instalado y corriendo
- ~6GB de espacio en disco para imágenes Docker
- Puerto 8080 disponible

### 1. Clonar el Repositorio

```bash
git clone <tu-repo>
cd air-quality-mlops
```

### 2. Levantar Airflow

```bash
cd airflow

# Construir imagen custom con Java + PySpark (~5 min primera vez)
docker compose build

# Levantar servicios (~1 min)
docker compose up -d

# Verificar que todo está corriendo
docker compose ps
```

### 3. Acceder a la UI

- **URL**: http://localhost:8080
- **Usuario**: `airflow`
- **Password**: `airflow`

### 4. Ejecutar el Pipeline

1. En la UI, activa el DAG `ingest_air_quality` (toggle ON)
2. Click en "Trigger DAG" (▶️) para ejecutar la ingesta
3. Espera a que termine (tarea verde = éxito)
4. Activa y ejecuta `transform_air_quality`
5. Verifica los datos generados:
   ```bash
   ls data/raw/Buenos_Aires/          # JSONs crudos
   ls data/curated/                   # Parquet procesado
   ```

### 5. Detener y Limpiar

```bash
# Detener servicios (preserva datos)
docker compose down

# Eliminar todo (incluye volúmenes de BD)
docker compose down -v

# Eliminar imágenes (libera ~6GB)
docker rmi airflow-custom:2.10.1-pyspark apache/airflow:2.10.1-python3.11 postgres:15 redis:7
```

## 📊 Datos

### Fuente de Datos

**Open-Meteo Air Quality API** (gratuita, sin API key)
- https://open-meteo.com/en/docs/air-quality-api

### Variables Capturadas (por hora)

| Variable | Unidad | Descripción |
|----------|--------|-------------|
| `pm2_5` | μg/m³ | Partículas < 2.5 micras |
| `pm10` | μg/m³ | Partículas < 10 micras |
| `carbon_monoxide` | μg/m³ | Monóxido de carbono |
| `nitrogen_dioxide` | μg/m³ | Dióxido de nitrógeno |
| `sulphur_dioxide` | μg/m³ | Dióxido de azufre |
| `ozone` | μg/m³ | Ozono |
| `us_aqi` | índice | US Air Quality Index |
| `european_aqi` | índice | European AQI |

### Clasificación de Calidad del Aire

Basada en EPA AQI para PM2.5:

| Etiqueta | PM2.5 (μg/m³) | Descripción |
|----------|---------------|-------------|
| `good` | < 12 | Buena calidad |
| `moderate` | 12 - 35.4 | Calidad moderada |
| `unhealthy` | ≥ 35.4 | No saludable |

### Cobertura Temporal

- **Granularidad**: Horaria (1 registro por hora)
- **Histórico**: 7 días hacia atrás
- **Forecast**: 1 día hacia adelante
- **Ciudad**: Buenos Aires, Argentina (-34.6, -58.4)

## 🔄 Pipeline de Datos

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Open-Meteo    │────▶│   data/raw/     │────▶│  data/curated/  │
│      API        │     │   *.json        │     │   *.parquet     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
   Ingesta DAG            JSON crudo              PySpark ETL
   (@hourly)              con arrays             DataFrame tabular
                          anidados               + clasificación
```

### DAG de Ingesta (`ingest_air_quality`)

- **Schedule**: `@hourly`
- **Acción**: Llama a Open-Meteo API → guarda JSON en `data/raw/{city}/`
- **Dependencias**: `requests` (incluido en Airflow)

### DAG de Transformación (`transform_air_quality`)

- **Schedule**: Cada 6 horas (`0 */6 * * *`)
- **Acción**: Lee JSONs → aplana con PySpark → clasifica → guarda Parquet
- **Dependencias**: PySpark + Java (incluidos en imagen custom)

## 🐳 Arquitectura Docker

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  Webserver  │  │  Scheduler  │  │   Worker    │          │
│  │   :8080     │  │             │  │  (Celery)   │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  PostgreSQL │  │    Redis    │  │  Triggerer  │          │
│  │  (metadata) │  │  (broker)   │  │             │          │
│  └─────────────┘  └─────────────┘  └─────────────┘          │
├─────────────────────────────────────────────────────────────┤
│  Volúmenes montados:                                         │
│  - ./dags → /opt/airflow/dags                               │
│  - ./logs → /opt/airflow/logs                               │
│  - ../src → /opt/airflow/src                                │
│  - ../data → /opt/airflow/data                              │
└─────────────────────────────────────────────────────────────┘
```

## 📝 Próximos Pasos

- [ ] **Entrenamiento**: Implementar pipeline con PyCaret + Optuna
- [ ] **MLflow**: Tracking de experimentos y registro de modelos
- [ ] **FastAPI**: API de inferencia con el mejor modelo
- [ ] **Evidently**: Monitoreo de data drift
- [ ] **GitHub Actions**: CI/CD para despliegue automatizado

## 👤 Autor

Proyecto desarrollado por Paul Lijtmaer como trabajo final de posgrado en MLOps.

## 📄 Licencia

Este proyecto es de uso académico.

