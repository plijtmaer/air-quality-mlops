"""
Pipeline de Training para Clasificación de Calidad del Aire
============================================================

Este script implementa el pipeline de entrenamiento completo:

1. Carga datos desde Parquet curado
2. PyCaret: compare_models() → ranking de modelos
3. Selección: filtrar por múltiples métricas (F1, AUC)
4. Optuna: tune_model() → optimizar hiperparámetros
5. MLflow: loggear todo a DagsHub

Uso:
    python -m src.training.train
    
    # O con parámetros
    python -m src.training.train --metric f1 --threshold 0.7
"""

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import dagshub
import mlflow
import pandas as pd

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuración
# =============================================================================

# Paths
DATA_PATH = Path("data/curated/Buenos_Aires_air_quality.parquet")

# Target y features
TARGET_COLUMN = "air_quality_label"
FEATURE_COLUMNS = [
    "pm2_5", "pm10",
    "carbon_monoxide", "nitrogen_dioxide", "sulphur_dioxide", "ozone",
    "us_aqi", "european_aqi",
]

# Columnas a excluir del entrenamiento
EXCLUDE_COLUMNS = ["city", "latitude", "longitude", "timezone", "timestamp", "parameter"]

# DagsHub/MLflow config
DAGSHUB_REPO_OWNER = "plijtmaer"
DAGSHUB_REPO_NAME = "air-quality-mlops"


# =============================================================================
# Funciones de Carga de Datos
# =============================================================================

def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    """Carga datos desde el Parquet curado."""
    logger.info(f"Loading data from {path}")
    
    df = pd.read_parquet(path)
    logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    
    return df


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara los datos para entrenamiento."""
    logger.info("Preparing data for training")
    
    # Eliminar columnas que no son features
    cols_to_drop = [c for c in EXCLUDE_COLUMNS if c in df.columns]
    df_clean = df.drop(columns=cols_to_drop)
    
    # Eliminar filas con valores nulos en el target
    df_clean = df_clean.dropna(subset=[TARGET_COLUMN])
    
    # Eliminar filas donde el label es "unknown"
    df_clean = df_clean[df_clean[TARGET_COLUMN] != "unknown"]
    
    logger.info(f"After cleaning: {len(df_clean)} rows")
    logger.info(f"Label distribution:\n{df_clean[TARGET_COLUMN].value_counts()}")
    
    return df_clean


# =============================================================================
# Setup MLflow con DagsHub
# =============================================================================

def setup_mlflow():
    """Configura MLflow para usar DagsHub como tracking server."""
    logger.info("Setting up MLflow with DagsHub")
    
    # Inicializar DagsHub (configura automáticamente MLflow)
    dagshub.init(
        repo_owner=DAGSHUB_REPO_OWNER,
        repo_name=DAGSHUB_REPO_NAME,
        mlflow=True
    )
    
    logger.info(f"MLflow tracking URI: {mlflow.get_tracking_uri()}")


# =============================================================================
# Training con PyCaret
# =============================================================================

def train_with_pycaret(
    df: pd.DataFrame,
    target: str = TARGET_COLUMN,
    sort_metric: str = "F1",
    n_select: int = 5
) -> Tuple:
    """
    Entrena modelos usando PyCaret AutoML.
    
    Args:
        df: DataFrame con features y target
        target: Nombre de la columna target
        sort_metric: Métrica para ordenar modelos (F1, AUC, Accuracy, etc.)
        n_select: Número de mejores modelos a retornar
    
    Returns:
        Tuple con (setup, best_models, comparison_results)
    """
    from pycaret.classification import setup, compare_models, pull
    
    logger.info("=" * 60)
    logger.info("Starting PyCaret AutoML")
    logger.info("=" * 60)
    
    # Setup de PyCaret (sin logging automático - lo hacemos manual con MLflow)
    clf_setup = setup(
        data=df,
        target=target,
        session_id=42,
        log_experiment=False,  # Desactivado para evitar conflictos con MLflow
        verbose=False,
    )
    
    # Comparar modelos
    logger.info(f"Comparing models, sorting by {sort_metric}")
    best_models = compare_models(
        sort=sort_metric,
        n_select=n_select,
        verbose=False,
    )
    
    # Obtener resultados de comparación
    results_df = pull()
    logger.info(f"\nTop {n_select} models by {sort_metric}:")
    logger.info(f"\n{results_df.head(n_select)}")
    
    return clf_setup, best_models, results_df


def filter_models_by_metrics(
    results_df: pd.DataFrame,
    best_models: list,
    min_f1: float = 0.5,
    min_auc: float = 0.5
) -> Tuple:
    """
    Filtra modelos por múltiples métricas.
    
    Args:
        results_df: DataFrame con resultados de compare_models
        best_models: Lista de modelos entrenados
        min_f1: F1 mínimo requerido
        min_auc: AUC mínimo requerido
    
    Returns:
        Tuple con (mejor_modelo, nombre_modelo, métricas)
    """
    logger.info(f"Filtering models: F1 >= {min_f1}, AUC >= {min_auc}")
    
    # Filtrar por métricas
    filtered = results_df[
        (results_df["F1"] >= min_f1) & 
        (results_df["AUC"] >= min_auc)
    ]
    
    if filtered.empty:
        logger.warning("No models meet the criteria, using best by F1")
        best_idx = 0
    else:
        # El primer modelo que cumple los criterios
        best_idx = results_df.index.get_loc(filtered.index[0])
        logger.info(f"Found {len(filtered)} models meeting criteria")
    
    best_model = best_models[best_idx] if isinstance(best_models, list) else best_models
    model_name = results_df.iloc[best_idx]["Model"] if "Model" in results_df.columns else type(best_model).__name__
    metrics = results_df.iloc[best_idx].to_dict()
    
    logger.info(f"Selected model: {model_name}")
    logger.info(f"Metrics: F1={metrics.get('F1', 'N/A'):.4f}, AUC={metrics.get('AUC', 'N/A'):.4f}")
    
    return best_model, model_name, metrics


# =============================================================================
# Tuning con Optuna
# =============================================================================

def tune_with_optuna(
    model,
    n_trials: int = 20,
    optimize_metric: str = "F1"
) -> Tuple:
    """
    Optimiza hiperparámetros usando Optuna (a través de PyCaret).
    
    Args:
        model: Modelo a optimizar
        n_trials: Número de trials de Optuna
        optimize_metric: Métrica a optimizar
    
    Returns:
        Tuple con (modelo_tuneado, resultados)
    """
    from pycaret.classification import tune_model, pull
    
    logger.info("=" * 60)
    logger.info(f"Tuning hyperparameters with Optuna ({n_trials} trials)")
    logger.info("=" * 60)
    
    # Tunear modelo
    tuned_model = tune_model(
        model,
        n_iter=n_trials,
        optimize=optimize_metric,
        search_library="optuna",
        verbose=False,
    )
    
    # Obtener resultados
    tune_results = pull()
    logger.info(f"Tuning results:\n{tune_results}")
    
    return tuned_model, tune_results


# =============================================================================
# Guardar Modelo
# =============================================================================

def save_model(model, model_name: str = "air_quality_model"):
    """Guarda el modelo usando PyCaret y lo registra en MLflow."""
    from pycaret.classification import save_model as pycaret_save
    
    logger.info(f"Saving model: {model_name}")
    
    # Guardar con PyCaret
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    model_path = models_dir / model_name
    pycaret_save(model, str(model_path))
    
    logger.info(f"Model saved to {model_path}")
    
    return str(model_path)


# =============================================================================
# Pipeline Principal
# =============================================================================

def run_training_pipeline(
    sort_metric: str = "F1",
    min_f1: float = 0.5,
    min_auc: float = 0.5,
    tune_trials: int = 20,
    save: bool = True
) -> dict:
    """
    Ejecuta el pipeline completo de entrenamiento.
    
    Args:
        sort_metric: Métrica para ordenar en compare_models
        min_f1: F1 mínimo para filtrar modelos
        min_auc: AUC mínimo para filtrar modelos
        tune_trials: Número de trials para Optuna
        save: Si guardar el modelo final
    
    Returns:
        Dict con resultados del entrenamiento
    """
    logger.info("=" * 60)
    logger.info("AIR QUALITY CLASSIFICATION - TRAINING PIPELINE")
    logger.info("=" * 60)
    
    # 1. Setup MLflow
    setup_mlflow()
    
    # 2. Cargar y preparar datos
    df = load_data()
    df_clean = prepare_data(df)
    
    # 3. Entrenar con PyCaret
    clf_setup, best_models, results_df = train_with_pycaret(
        df_clean,
        sort_metric=sort_metric,
        n_select=5
    )
    
    # Loggear resultados de comparación a MLflow
    with mlflow.start_run(run_name="pycaret_compare_models"):
        mlflow.log_param("sort_metric", sort_metric)
        mlflow.log_param("n_models_compared", len(results_df))
        mlflow.log_param("n_samples", len(df_clean))
        mlflow.log_param("n_features", len(FEATURE_COLUMNS))
        
        # Loggear métricas del mejor modelo
        if len(results_df) > 0:
            best_row = results_df.iloc[0]
            for col in ["Accuracy", "AUC", "Recall", "Prec.", "F1", "Kappa"]:
                if col in best_row:
                    mlflow.log_metric(f"best_{col.lower().replace('.', '')}", float(best_row[col]))
    
    # 4. Filtrar por múltiples métricas
    best_model, model_name, metrics = filter_models_by_metrics(
        results_df, best_models, min_f1, min_auc
    )
    
    # 5. Tunear con Optuna
    tuned_model, tune_results = tune_with_optuna(
        best_model,
        n_trials=tune_trials,
        optimize_metric=sort_metric
    )
    
    # Loggear resultados de tuning a MLflow
    with mlflow.start_run(run_name=f"optuna_tune_{model_name}"):
        mlflow.log_param("base_model", model_name)
        mlflow.log_param("tune_trials", tune_trials)
        mlflow.log_param("optimize_metric", sort_metric)
        
        # Loggear métricas del modelo tuneado
        if tune_results is not None and len(tune_results) > 0:
            for col in ["Accuracy", "AUC", "Recall", "Prec.", "F1", "Kappa"]:
                if col in tune_results.columns:
                    mlflow.log_metric(f"tuned_{col.lower().replace('.', '')}", float(tune_results[col].iloc[0]))
    
    # 6. Guardar modelo
    model_path = None
    if save:
        model_path = save_model(tuned_model, f"air_quality_{model_name.lower()}_tuned")
    
    # 7. Resumen
    logger.info("=" * 60)
    logger.info("TRAINING COMPLETED!")
    logger.info("=" * 60)
    logger.info(f"Best model: {model_name}")
    logger.info(f"Model path: {model_path}")
    logger.info(f"Check experiments at: https://dagshub.com/{DAGSHUB_REPO_OWNER}/{DAGSHUB_REPO_NAME}/experiments")
    
    return {
        "model": tuned_model,
        "model_name": model_name,
        "model_path": model_path,
        "metrics": metrics,
        "comparison_results": results_df,
    }


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train air quality classification model")
    parser.add_argument("--metric", type=str, default="F1", help="Metric to sort models by")
    parser.add_argument("--min-f1", type=float, default=0.5, help="Minimum F1 score")
    parser.add_argument("--min-auc", type=float, default=0.5, help="Minimum AUC score")
    parser.add_argument("--tune-trials", type=int, default=20, help="Number of Optuna trials")
    parser.add_argument("--no-save", action="store_true", help="Don't save the model")
    
    args = parser.parse_args()
    
    results = run_training_pipeline(
        sort_metric=args.metric,
        min_f1=args.min_f1,
        min_auc=args.min_auc,
        tune_trials=args.tune_trials,
        save=not args.no_save
    )
    
    print("\n✅ Training complete!")
    print(f"Best model: {results['model_name']}")
    print(f"Model saved to: {results['model_path']}")

