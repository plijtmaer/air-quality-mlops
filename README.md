# 🌬️ Air Quality MLOps

Proyecto de MLOps end-to-end para clasificación de calidad del aire, desarrollado como trabajo final de posgrado.

## 📋 Descripción

Pipeline completo de Machine Learning Operations que:
1. **Ingesta** datos de calidad del aire desde Open-Meteo API (Airflow)
2. **Transforma** los datos crudos usando PySpark
3. **Versiona** datos con DVC + DagsHub
4. **Gestiona features** con Feast Feature Store
5. **Entrena** modelos con PyCaret + Optuna + MLflow
6. **Sirve** predicciones via FastAPI
7. **Monitorea** data drift con Evidently

## 🛠️ Stack Tecnológico

| Componente | Tecnología | Estado |
|------------|------------|--------|
| Orquestación | Apache Airflow 2.10 | ✅ |
| Contenedores | Docker & Docker Compose | ✅ |
| Transformación | PySpark (local mode) | ✅ |
| Versionado de Datos | DVC + DagsHub | ✅ |
| Feature Store | Feast | ✅ |
| AutoML | PyCaret | ✅ |
| Hyperparameter Tuning | Optuna | ✅ |
| Experiment Tracking | MLflow (DagsHub) | ✅ |
| API | FastAPI | ✅ |
| Monitoreo | Evidently | ✅ |
| IaC | Terraform | ⏳ |
| Kubernetes | Kind (local) | ⏳ |

## 📁 Estructura del Proyecto

```
air-quality-mlops/
├── airflow/                          # Apache Airflow
│   ├── dags/                         # Definiciones de DAGs
│   │   ├── hello_airflow.py          # DAG de prueba
│   │   ├── ingest_air_quality.py     # Ingesta desde Open-Meteo
│   │   └── transform_air_quality.py  # Transformación PySpark
│   ├── docker-compose.yaml           # Servicios Docker
│   ├── Dockerfile                    # Imagen custom (Java+PySpark)
│   └── README.md
│
├── src/                              # Código fuente Python
│   ├── ingestion/                    # Módulo de ingesta
│   │   └── open_meteo_client.py      # Cliente Open-Meteo API
│   ├── transform/                    # Módulo de transformación
│   │   └── air_quality_transform.py  # Pipeline PySpark
│   ├── training/                     # Módulo de entrenamiento
│   │   └── train.py                  # PyCaret + Optuna + MLflow
│   ├── inference/                    # API FastAPI
│   │   ├── main.py                   # Endpoints REST
│   │   ├── model.py                  # Carga del modelo
│   │   └── schemas.py                # Schemas Pydantic
│   └── monitoring/                   # Monitoreo con Evidently
│       └── drift_detector.py         # Detección de data drift
│
├── feature_store/                    # Feast Feature Store
│   └── air_quality_features/
│       └── feature_repo/
│           ├── air_quality_features.py  # Definición de features
│           └── feature_store.yaml       # Configuración
│
├── data/                             # Datos (versionados con DVC)
│   ├── raw/                          # JSON crudos de la API
│   └── curated/                      # Parquet procesados
│
├── models/                           # Modelos entrenados
│   └── air_quality_*_tuned.pkl       # Modelo PyCaret
│
├── .dvc/                             # Configuración DVC
├── .venv/                            # Virtual environment
├── .gitignore
├── .gitattributes
├── data/raw.dvc                      # Puntero DVC a datos raw
├── data/curated.dvc                  # Puntero DVC a datos curated
└── README.md
```

## 🚀 Inicio Rápido

### Requisitos Previos

- Python 3.11+
- Docker Desktop
- Git
- ~6GB de espacio en disco

### 1. Clonar y Configurar Entorno

```bash
git clone https://github.com/plijtmaer/air-quality-mlops.git
cd air-quality-mlops

# Crear virtual environment con uv (recomendado)
uv venv .venv --python 3.11 --seed
source .venv/Scripts/activate  # Windows Git Bash
# o
.venv\Scripts\activate         # Windows PowerShell

# Instalar dependencias
uv pip install dvc dagshub mlflow feast pycaret optuna
```

### 2. Descargar Datos (DVC)

```bash
# Configurar credenciales DVC (solo primera vez)
dvc remote modify origin --local auth basic
dvc remote modify origin --local user TU_USUARIO_DAGSHUB
dvc remote modify origin --local password TU_TOKEN_DAGSHUB

# Descargar datos
dvc pull
```

### 3. Ejecutar Training

```bash
python -m src.training.train

# Con parámetros personalizados
python -m src.training.train --metric F1 --min-f1 0.7 --tune-trials 30
```

### 4. Levantar Airflow (opcional)

```bash
cd airflow
docker compose build
docker compose up -d
# UI: http://localhost:8080 (airflow/airflow)
```

## 📊 Pipeline de Datos

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Open-Meteo    │────▶│   data/raw/     │────▶│  data/curated/  │
│      API        │     │   *.json        │     │   *.parquet     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
   Airflow DAG             DVC tracked            PySpark ETL
   (@hourly)                                    + clasificación
```

## 🤖 Pipeline de Training

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  data/curated/  │────▶│     PyCaret     │────▶│     Optuna      │
│   *.parquet     │     │ compare_models  │     │   tune_model    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                       │
                               ▼                       ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │     MLflow      │     │     models/     │
                        │    (DagsHub)    │     │   *.pkl         │
                        └─────────────────┘     └─────────────────┘
```

### Resultados del Último Training

| Métrica | Valor |
|---------|-------|
| **Mejor modelo** | Decision Tree Classifier |
| **F1 Score** | 0.9886 (98.86%) |
| **AUC** | 0.95 (95%) |
| **Accuracy** | 0.9923 (99.23%) |

Ver experimentos: https://dagshub.com/plijtmaer/air-quality-mlops.mlflow

## 🍽️ Feast Feature Store

Features definidas para calidad del aire:

| Feature | Tipo | Descripción |
|---------|------|-------------|
| `pm2_5` | Float | PM2.5 (μg/m³) |
| `pm10` | Float | PM10 (μg/m³) |
| `carbon_monoxide` | Float | CO (μg/m³) |
| `nitrogen_dioxide` | Float | NO2 (μg/m³) |
| `sulphur_dioxide` | Float | SO2 (μg/m³) |
| `ozone` | Float | O3 (μg/m³) |
| `us_aqi` | Int | US Air Quality Index |
| `european_aqi` | Int | European AQI |
| `air_quality_label` | String | good/moderate/unhealthy |

### Usar Feast

```bash
cd feature_store/air_quality_features/feature_repo

# Aplicar definiciones
feast apply

# Materializar features
feast materialize-incremental $(date -u +"%Y-%m-%dT%H:%M:%S")
```

## 🚀 FastAPI Inference API

API REST para predicción de calidad del aire.

### Iniciar el Servidor

```bash
# Activar entorno virtual
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# Iniciar servidor
uvicorn src.inference.main:app --host 0.0.0.0 --port 8000

# O con recarga automática (desarrollo)
uvicorn src.inference.main:app --reload --port 8000
```

### Endpoints Disponibles

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Info de la API |
| `/health` | GET | Health check |
| `/predict` | POST | Predicción individual |
| `/predict/batch` | POST | Predicción en lote |
| `/model/info` | GET | Info del modelo |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc |

### Ejemplo de Predicción

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "pm2_5": 15.5,
    "pm10": 25.0,
    "carbon_monoxide": 200.0,
    "nitrogen_dioxide": 10.5,
    "sulphur_dioxide": 5.0,
    "ozone": 50.0,
    "us_aqi": 42,
    "european_aqi": 35
  }'
```

**Respuesta:**
```json
{
  "prediction": "moderate",
  "confidence": 1.0,
  "probabilities": null
}
```

## 📈 Clasificación de Calidad del Aire

Basada en EPA AQI para PM2.5:

| Etiqueta | PM2.5 (μg/m³) | Descripción |
|----------|---------------|-------------|
| `good` | < 12 | Buena calidad |
| `moderate` | 12 - 35.4 | Calidad moderada |
| `unhealthy` | ≥ 35.4 | No saludable |

## 🔗 Enlaces

- **DagsHub Repo**: https://dagshub.com/plijtmaer/air-quality-mlops
- **MLflow Experiments**: https://dagshub.com/plijtmaer/air-quality-mlops.mlflow
- **Open-Meteo API**: https://open-meteo.com/en/docs/air-quality-api

## 📊 Monitoreo con Evidently

Detección de data drift comparando datos de producción con datos de entrenamiento.

### Endpoints de Monitoreo

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/monitoring/drift` | POST | Detectar drift en datos |
| `/monitoring/reference-stats` | GET | Estadísticas de referencia |
| `/monitoring/report` | POST | Generar reporte HTML |

### Ejemplo de Detección de Drift

```bash
curl -X POST "http://localhost:8000/monitoring/drift" \
  -H "Content-Type: application/json" \
  -d '{
    "samples": [
      {"pm2_5": 15.5, "pm10": 25.0, "carbon_monoxide": 200.0, "nitrogen_dioxide": 10.5, "sulphur_dioxide": 5.0, "ozone": 50.0, "us_aqi": 42, "european_aqi": 35},
      {"pm2_5": 18.0, "pm10": 30.0, "carbon_monoxide": 250.0, "nitrogen_dioxide": 12.0, "sulphur_dioxide": 6.0, "ozone": 55.0, "us_aqi": 50, "european_aqi": 40}
    ]
  }'
```

**Respuesta:**
```json
{
  "timestamp": "2025-12-05T...",
  "drift_detected": false,
  "drift_score": 0.0,
  "drifted_features": [],
  "feature_details": {...}
}
```

### Reportes HTML

Los reportes se guardan en `reports/monitoring/` como archivos HTML interactivos.

## 📝 Próximos Pasos

- [x] ~~**FastAPI**: API REST para inferencia~~
- [x] ~~**Evidently**: Monitoreo de data drift~~
- [ ] **Docker**: Containerizar la aplicación completa
- [ ] **Terraform**: Infraestructura como código
- [ ] **Kind**: Deployment en Kubernetes local
- [ ] **GitHub Actions**: CI/CD

## 🛠️ Comandos Útiles

```bash
# Training
python -m src.training.train

# FastAPI
uvicorn src.inference.main:app --port 8000

# DVC
dvc pull                    # Descargar datos
dvc push                    # Subir datos
dvc status                  # Ver estado

# Feast
cd feature_store/air_quality_features/feature_repo
feast apply                 # Aplicar cambios
feast materialize-incremental "2025-12-05T00:00:00"

# Airflow
cd airflow
docker compose up -d        # Levantar
docker compose down         # Detener
docker compose logs -f      # Ver logs
```

## 👤 Autor

Proyecto desarrollado por **Paul Lijtmaer** como trabajo final de posgrado en MLOps.

## 📄 Licencia

Este proyecto es de uso académico.
