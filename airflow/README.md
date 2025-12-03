# Apache Airflow - Docker Setup

Este directorio contiene la configuración de Apache Airflow para el proyecto **air-quality-mlops**.

## 📋 Estructura

```
airflow/
├── dags/
│   ├── hello_airflow.py         # DAG de prueba (smoke test)
│   ├── ingest_air_quality.py    # Ingesta desde Open-Meteo API → JSON
│   └── transform_air_quality.py # Transformación con PySpark → Parquet
├── logs/                        # Logs generados (no se commitean)
├── plugins/                     # Plugins personalizados
├── docker-compose.yaml          # Orquestación de servicios
├── Dockerfile                   # Imagen custom con Java + PySpark
├── .env                         # Variables de entorno
└── README.md                    # Este archivo
```

## 🚀 Inicio Rápido

### Primera Vez (Setup Completo)

```bash
# 1. Navegar a la carpeta airflow
cd airflow

# 2. Construir imagen custom con Java + PySpark (~5 min)
docker compose build

# 3. Levantar todos los servicios
docker compose up -d

# 4. Verificar que todo está corriendo
docker compose ps

# 5. Acceder a la UI
# URL: http://localhost:8080
# Usuario: airflow
# Password: airflow
```

### Después (ya tenés la imagen)

```bash
cd airflow
docker compose up -d
```

## 📊 DAGs Disponibles

### 1. `hello_airflow` (Smoke Test)
- **Propósito**: Verificar que Airflow funciona correctamente
- **Schedule**: `@daily`
- **Tareas**: `start → say_hello → end`

### 2. `ingest_air_quality` (Ingesta)
- **Propósito**: Descargar datos de calidad del aire desde Open-Meteo API
- **Schedule**: `@hourly`
- **Output**: `data/raw/{city}/{timestamp}.json`
- **Ciudad**: Buenos Aires (-34.6, -58.4)
- **API**: https://open-meteo.com/en/docs/air-quality-api

### 3. `transform_air_quality` (Transformación)
- **Propósito**: Transformar JSON crudo → Parquet curado con PySpark
- **Schedule**: Cada 6 horas (`0 */6 * * *`)
- **Input**: `data/raw/{city}/*.json`
- **Output**: `data/curated/{city}_air_quality.parquet`
- **Requiere**: Java + PySpark (incluidos en imagen custom)

---

## ⚡ Ejecutar Pipeline Completo

### Opción A: Desde la UI Web

1. Abre http://localhost:8080
2. Login: `airflow` / `airflow`
3. Activa `ingest_air_quality` (toggle ON)
4. Click "Trigger DAG" (▶️)
5. Espera a que termine (verde = éxito)
6. Activa y ejecuta `transform_air_quality`

### Opción B: Desde CLI

```bash
# Trigger ingesta
docker exec airflow-scheduler airflow dags trigger ingest_air_quality

# Esperar unos segundos, luego trigger transformación
docker exec airflow-scheduler airflow dags trigger transform_air_quality

# Ver logs del worker
docker logs airflow-worker --tail 50
```

### Verificar Resultados

```bash
# Ver JSONs crudos
ls ../data/raw/Buenos_Aires/

# Ver Parquet curado
ls ../data/curated/
# Debería mostrar: Buenos_Aires_air_quality.parquet/
```

---

## 🛠️ Comandos Útiles

### Gestión de Servicios

```bash
# Levantar en background
docker compose up -d

# Ver estado de servicios
docker compose ps

# Ver logs en tiempo real
docker compose logs -f

# Ver logs de un servicio específico
docker compose logs -f airflow-worker

# Reiniciar todos los servicios
docker compose restart

# Detener sin eliminar datos
docker compose down

# Reset completo (elimina BD y volúmenes)
docker compose down -v
```

### Ejecutar Comandos en Contenedores

```bash
# Acceder a shell del worker
docker exec -it airflow-worker bash

# Listar DAGs
docker exec airflow-scheduler airflow dags list

# Trigger manual de DAG
docker exec airflow-scheduler airflow dags trigger ingest_air_quality

# Verificar Java está instalado
docker exec airflow-worker java -version

# Verificar PySpark está instalado
docker exec airflow-worker python -c "import pyspark; print(pyspark.__version__)"
```

### Base de Datos (PostgreSQL de Airflow)

```bash
# Conectar a PostgreSQL
docker exec -it airflow-postgres psql -U airflow -d airflow

# Ver DAGs registrados
docker exec airflow-postgres psql -U airflow -d airflow -c "SELECT dag_id, is_paused FROM dag;"
```

---

## 📦 Servicios Incluidos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `airflow-webserver` | 8080 | UI web de Airflow |
| `airflow-scheduler` | - | Programa y lanza tareas |
| `airflow-worker` | - | Ejecuta tareas (Celery) |
| `airflow-triggerer` | - | Maneja deferrable operators |
| `airflow-postgres` | - | Base de datos de metadatos |
| `airflow-redis` | - | Message broker para Celery |

---

## 🐳 Imagen Custom (Dockerfile)

La imagen `airflow-custom:2.10.1-pyspark` incluye:

- **Base**: `apache/airflow:2.10.1-python3.11`
- **Java**: OpenJDK 17 (requerido por Spark)
- **PySpark**: 3.5.3
- **procps**: Para comandos como `ps` (requerido por Spark)

### Reconstruir la Imagen

```bash
# Si modificaste el Dockerfile:
docker compose build --no-cache

# Luego reinicia:
docker compose down
docker compose up -d
```

---

## ⚙️ Configuración

### Variables de Entorno (`.env`)

```bash
AIRFLOW_UID=50000                    # UID del usuario en contenedor
_AIRFLOW_WWW_USER_USERNAME=airflow   # Usuario admin UI
_AIRFLOW_WWW_USER_PASSWORD=airflow   # Password admin UI
```

### Agregar Paquetes Python

Edita el `Dockerfile` para agregar más paquetes:

```dockerfile
RUN pip install --no-cache-dir \
    pyspark==3.5.3 \
    pandas \
    pycaret \
    mlflow
```

Luego reconstruye:
```bash
docker compose build --no-cache
docker compose up -d
```

---

## 🔧 Troubleshooting

### Error de permisos en logs/

```bash
# En Linux/WSL, obtén tu UID:
id -u

# Actualiza .env con ese valor:
AIRFLOW_UID=1000
```

### DAG no aparece en la UI

1. Verifica que el archivo esté en `dags/`
2. Revisa errores de sintaxis:
   ```bash
   docker compose logs airflow-scheduler | grep -i error
   ```
3. Importa el DAG manualmente para ver errores:
   ```bash
   docker exec airflow-worker python /opt/airflow/dags/ingest_air_quality.py
   ```

### Error "JAVA_HOME is not set"

Asegúrate de estar usando la imagen custom:

```bash
# Verificar imagen en uso
docker ps --format "table {{.Names}}\t{{.Image}}"

# Debe mostrar: airflow-custom:2.10.1-pyspark
# NO: apache/airflow:2.10.1-python3.11

# Si no, reconstruye:
docker compose build
docker compose down
docker compose up -d
```

### Error "No raw data found for city"

Ejecuta primero el DAG de ingesta:
```bash
docker exec airflow-scheduler airflow dags trigger ingest_air_quality
# Espera 30 segundos
docker exec airflow-scheduler airflow dags trigger transform_air_quality
```

### Contenedores lentos al iniciar (health: starting)

Es normal la primera vez porque se instalan dependencias. Espera ~2-3 minutos.

Si persiste, verifica los logs:
```bash
docker compose logs airflow-webserver
```

### Reiniciar desde cero

```bash
docker compose down -v          # Elimina contenedores y volúmenes
docker compose build --no-cache # Reconstruye imagen
docker compose up -d            # Levanta todo
```

---

## 📁 Flujo de Datos

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AIRFLOW DAGs                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┴──────────────────┐
           ▼                                     ▼
┌─────────────────────┐               ┌─────────────────────┐
│  ingest_air_quality │               │ transform_air_quality│
│  (@hourly)          │               │  (cada 6h)           │
└─────────────────────┘               └─────────────────────┘
           │                                     │
           ▼                                     ▼
┌─────────────────────┐               ┌─────────────────────┐
│  Open-Meteo API     │               │  PySpark Pipeline   │
│  (gratuita, sin key)│               │  (local[*])         │
└─────────────────────┘               └─────────────────────┘
           │                                     │
           ▼                                     ▼
┌─────────────────────┐               ┌─────────────────────┐
│  data/raw/          │──────────────▶│  data/curated/       │
│  Buenos_Aires/      │               │  Buenos_Aires_       │
│  {timestamp}.json   │               │  air_quality.parquet │
└─────────────────────┘               └─────────────────────┘

Variables capturadas (por hora):
• pm2_5, pm10 (partículas)
• carbon_monoxide, nitrogen_dioxide, sulphur_dioxide, ozone
• us_aqi, european_aqi (índices)
• air_quality_label (clasificación: good/moderate/unhealthy)
```

---

## 🧹 Limpieza

### Detener servicios (preserva datos)

```bash
docker compose down
```

### Eliminar todo (BD, logs, volúmenes)

```bash
docker compose down -v
```

### Eliminar imágenes (libera ~6GB)

```bash
docker rmi airflow-custom:2.10.1-pyspark apache/airflow:2.10.1-python3.11 postgres:15 redis:7
```

### Limpiar caché de Docker

```bash
docker system prune -a
```
