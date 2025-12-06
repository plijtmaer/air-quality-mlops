# 🏗️ Arquitectura del Sistema

## Diagrama General

```mermaid
flowchart TB
    subgraph External["🌐 Fuentes Externas"]
        API_EXT[("Open-Meteo API<br/>Air Quality Data")]
    end

    subgraph Ingestion["📥 Ingesta"]
        AIRFLOW[("⚙️ Apache Airflow<br/>Orchestration")]
        INGEST["ingest_air_quality<br/>DAG"]
        RAW[("📁 data/raw/<br/>JSON files")]
    end

    subgraph Transform["🔄 Transformación"]
        SPARK["⚡ PySpark<br/>Local Mode"]
        TRANSFORM_DAG["transform_air_quality<br/>DAG"]
        CURATED[("📁 data/curated/<br/>Parquet")]
    end

    subgraph DataVersioning["📦 Versionado"]
        DVC["📊 DVC<br/>Data Version Control"]
        DAGSHUB[("☁️ DagsHub<br/>Remote Storage")]
    end

    subgraph FeatureStore["🗄️ Feature Store"]
        FEAST["🍽️ Feast<br/>Feature Management"]
        FEATURES[("Features<br/>air_quality_hourly")]
    end

    subgraph Training["🤖 Entrenamiento"]
        PYCARET["🔬 PyCaret<br/>AutoML"]
        OPTUNA["🎯 Optuna<br/>Hyperparameter Tuning"]
        MLFLOW[("📈 MLflow<br/>Experiment Tracking")]
        MODEL[("💾 models/<br/>*.pkl")]
    end

    subgraph Inference["🚀 Inferencia"]
        FASTAPI["⚡ FastAPI<br/>REST API"]
        DOCKER["🐳 Docker<br/>Container"]
    end

    subgraph Monitoring["📊 Monitoreo"]
        EVIDENTLY["📉 Evidently<br/>Data Drift Detection"]
        REPORTS[("📄 reports/<br/>HTML Reports")]
    end

    subgraph Infrastructure["☸️ Infraestructura"]
        TERRAFORM["🏗️ Terraform<br/>IaC"]
        KIND["☸️ Kind<br/>Local K8s"]
        K8S_DEPLOY["Deployment<br/>2 replicas"]
        K8S_SVC["Service<br/>NodePort 30000"]
    end

    subgraph CICD["🔄 CI/CD"]
        GITHUB["🐙 GitHub<br/>Repository"]
        ACTIONS["⚡ GitHub Actions<br/>Workflows"]
        GHCR[("📦 GHCR<br/>Container Registry")]
    end

    %% Connections
    API_EXT --> AIRFLOW
    AIRFLOW --> INGEST
    INGEST --> RAW
    
    RAW --> SPARK
    AIRFLOW --> TRANSFORM_DAG
    TRANSFORM_DAG --> SPARK
    SPARK --> CURATED
    
    CURATED --> DVC
    DVC <--> DAGSHUB
    
    CURATED --> FEAST
    FEAST --> FEATURES
    
    FEATURES --> PYCARET
    PYCARET --> OPTUNA
    PYCARET --> MLFLOW
    OPTUNA --> MLFLOW
    MLFLOW --> DAGSHUB
    OPTUNA --> MODEL
    
    MODEL --> FASTAPI
    FASTAPI --> DOCKER
    
    CURATED --> EVIDENTLY
    EVIDENTLY --> REPORTS
    FASTAPI --> EVIDENTLY
    
    DOCKER --> TERRAFORM
    TERRAFORM --> KIND
    KIND --> K8S_DEPLOY
    K8S_DEPLOY --> K8S_SVC
    
    GITHUB --> ACTIONS
    ACTIONS --> GHCR
    GHCR --> DOCKER

    %% Styling
    classDef external fill:#e1f5fe,stroke:#01579b
    classDef ingestion fill:#fff3e0,stroke:#e65100
    classDef transform fill:#f3e5f5,stroke:#7b1fa2
    classDef versioning fill:#e8f5e9,stroke:#2e7d32
    classDef feature fill:#fce4ec,stroke:#c2185b
    classDef training fill:#e3f2fd,stroke:#1565c0
    classDef inference fill:#f1f8e9,stroke:#558b2f
    classDef monitoring fill:#fff8e1,stroke:#f9a825
    classDef infra fill:#eceff1,stroke:#455a64
    classDef cicd fill:#fbe9e7,stroke:#bf360c

    class API_EXT external
    class AIRFLOW,INGEST,RAW ingestion
    class SPARK,TRANSFORM_DAG,CURATED transform
    class DVC,DAGSHUB versioning
    class FEAST,FEATURES feature
    class PYCARET,OPTUNA,MLFLOW,MODEL training
    class FASTAPI,DOCKER inference
    class EVIDENTLY,REPORTS monitoring
    class TERRAFORM,KIND,K8S_DEPLOY,K8S_SVC infra
    class GITHUB,ACTIONS,GHCR cicd
```

## Flujo de Datos Simplificado

```mermaid
flowchart LR
    A[🌐 Open-Meteo API] -->|hourly| B[📥 Airflow]
    B -->|JSON| C[⚡ PySpark]
    C -->|Parquet| D[🍽️ Feast]
    D -->|Features| E[🔬 PyCaret]
    E -->|Best Model| F[🎯 Optuna]
    F -->|Tuned Model| G[⚡ FastAPI]
    G -->|Predictions| H[👤 Users]
    
    C -.->|track| I[📊 DVC]
    E -.->|log| J[📈 MLflow]
    F -.->|log| J
    G -.->|monitor| K[📉 Evidently]
```

## Stack Tecnológico

```mermaid
mindmap
  root((Air Quality MLOps))
    Data Pipeline
      Apache Airflow
      PySpark
      Open-Meteo API
    Data Management
      DVC
      DagsHub
      Feast
    ML Training
      PyCaret
      Optuna
      MLflow
    Inference
      FastAPI
      Pydantic
      Uvicorn
    Monitoring
      Evidently
      HTML Reports
    Infrastructure
      Docker
      Terraform
      Kind / Kubernetes
    CI/CD
      GitHub Actions
      GHCR
```

## Componentes y Puertos

| Servicio | Puerto Local | Descripción |
|----------|--------------|-------------|
| Airflow UI | 8080 | Orquestación de pipelines |
| FastAPI (Docker) | 8000 | API de inferencia |
| FastAPI (K8s) | 8080 | API en Kubernetes |
| MLflow | DagsHub | Tracking de experimentos |
| Feast | SQLite | Feature store local |

## Endpoints de la API

```mermaid
flowchart LR
    subgraph API["FastAPI Endpoints"]
        direction TB
        A["/health"] --> A1["GET - Health Check"]
        B["/predict"] --> B1["POST - Single Prediction"]
        C["/predict/batch"] --> C1["POST - Batch Prediction"]
        D["/model/info"] --> D1["GET - Model Info"]
        E["/monitoring/drift"] --> E1["POST - Detect Drift"]
        F["/monitoring/report"] --> F1["POST - Generate Report"]
    end
```

