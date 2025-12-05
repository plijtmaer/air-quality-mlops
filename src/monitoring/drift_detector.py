"""
Detección de Data Drift con Evidently
=====================================

Este módulo implementa la detección de drift en datos
de calidad del aire usando Evidently.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from evidently import ColumnMapping
from evidently.metric_preset import DataDriftPreset, DataQualityPreset, TargetDriftPreset
from evidently.report import Report
from evidently.test_preset import DataDriftTestPreset, DataQualityTestPreset
from evidently.test_suite import TestSuite

logger = logging.getLogger(__name__)

# =============================================================================
# Configuración
# =============================================================================

# Paths
DATA_CURATED_PATH = Path("data/curated")
REPORTS_PATH = Path("reports/monitoring")
REPORTS_PATH.mkdir(parents=True, exist_ok=True)

# Features numéricas para monitorear
NUMERICAL_FEATURES = [
    "pm2_5",
    "pm10",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "us_aqi",
    "european_aqi",
]

# Feature categórica (target)
TARGET_COLUMN = "air_quality_label"


class DriftDetector:
    """
    Detector de Data Drift usando Evidently.
    
    Compara datos de referencia (training) con datos actuales (producción)
    para detectar cambios en la distribución de features y target.
    """
    
    def __init__(
        self,
        reference_data: Optional[pd.DataFrame] = None,
        numerical_features: Optional[List[str]] = None,
        target_column: Optional[str] = None,
    ):
        """
        Inicializa el detector de drift.
        
        Args:
            reference_data: DataFrame de referencia (training data).
                           Si es None, se carga desde data/curated/.
            numerical_features: Lista de features numéricas a monitorear.
            target_column: Nombre de la columna target.
        """
        self.numerical_features = numerical_features or NUMERICAL_FEATURES
        self.target_column = target_column or TARGET_COLUMN
        self.reference_data = reference_data
        
        # Configurar column mapping para Evidently
        self.column_mapping = ColumnMapping(
            target=self.target_column,
            numerical_features=self.numerical_features,
        )
        
        # Cargar datos de referencia si no se proporcionaron
        if self.reference_data is None:
            self._load_reference_data()
    
    def _load_reference_data(self):
        """
        Carga los datos de referencia desde el dataset curado.
        """
        try:
            parquet_files = list(DATA_CURATED_PATH.glob("*.parquet"))
            if not parquet_files:
                raise FileNotFoundError(
                    f"No se encontraron archivos Parquet en {DATA_CURATED_PATH}"
                )
            
            # Cargar el primer archivo encontrado como referencia
            self.reference_data = pd.read_parquet(parquet_files[0])
            
            # Filtrar solo las columnas necesarias
            columns_needed = self.numerical_features + [self.target_column]
            available_columns = [c for c in columns_needed if c in self.reference_data.columns]
            self.reference_data = self.reference_data[available_columns].copy()
            
            # Eliminar nulos
            self.reference_data = self.reference_data.dropna()
            
            logger.info(f"Datos de referencia cargados: {len(self.reference_data)} filas")
            
        except Exception as e:
            logger.error(f"Error cargando datos de referencia: {e}")
            raise
    
    def detect_drift(
        self,
        current_data: pd.DataFrame,
    ) -> Dict:
        """
        Detecta data drift comparando datos actuales con referencia.
        
        Args:
            current_data: DataFrame con datos actuales (producción).
            
        Returns:
            Diccionario con resultados del análisis de drift.
        """
        logger.info("Ejecutando detección de drift...")
        
        # Asegurar que tenemos las columnas necesarias
        columns_needed = self.numerical_features.copy()
        if self.target_column in current_data.columns:
            columns_needed.append(self.target_column)
        
        available_columns = [c for c in columns_needed if c in current_data.columns]
        current_data = current_data[available_columns].copy()
        
        # Crear reporte de drift
        report = Report(metrics=[
            DataDriftPreset(),
        ])
        
        report.run(
            reference_data=self.reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping,
        )
        
        # Extraer resultados
        result = report.as_dict()
        
        # Parsear resultados
        drift_summary = self._parse_drift_results(result)
        
        logger.info(f"Drift detectado: {drift_summary['drift_detected']}")
        
        return drift_summary
    
    def _parse_drift_results(self, result: Dict) -> Dict:
        """
        Parsea los resultados del reporte de Evidently.
        
        Args:
            result: Diccionario con resultados de Evidently.
            
        Returns:
            Diccionario simplificado con resultados de drift.
        """
        drift_summary = {
            "timestamp": datetime.now().isoformat(),
            "drift_detected": False,
            "drift_score": 0.0,
            "drifted_features": [],
            "feature_details": {},
        }
        
        try:
            metrics = result.get("metrics", [])
            
            for metric in metrics:
                metric_result = metric.get("result", {})
                
                # Dataset drift
                if "drift_share" in metric_result:
                    drift_summary["drift_score"] = metric_result.get("drift_share", 0)
                    drift_summary["drift_detected"] = metric_result.get("dataset_drift", False)
                
                # Drift por columna
                if "drift_by_columns" in metric_result:
                    for col, col_info in metric_result["drift_by_columns"].items():
                        if col in self.numerical_features:
                            drift_summary["feature_details"][col] = {
                                "drift_detected": col_info.get("drift_detected", False),
                                "drift_score": col_info.get("drift_score", 0),
                                "stattest_name": col_info.get("stattest_name", "unknown"),
                            }
                            if col_info.get("drift_detected", False):
                                drift_summary["drifted_features"].append(col)
        
        except Exception as e:
            logger.error(f"Error parseando resultados: {e}")
        
        return drift_summary
    
    def generate_report(
        self,
        current_data: pd.DataFrame,
        report_name: Optional[str] = None,
        include_data_quality: bool = True,
        include_target_drift: bool = True,
    ) -> Path:
        """
        Genera un reporte HTML completo de drift.
        
        Args:
            current_data: DataFrame con datos actuales.
            report_name: Nombre del archivo de reporte.
            include_data_quality: Incluir métricas de calidad de datos.
            include_target_drift: Incluir análisis de drift en target.
            
        Returns:
            Path al archivo HTML generado.
        """
        logger.info("Generando reporte de monitoreo...")
        
        # Construir lista de métricas
        metrics = [DataDriftPreset()]
        
        if include_data_quality:
            metrics.append(DataQualityPreset())
        
        if include_target_drift and self.target_column in current_data.columns:
            metrics.append(TargetDriftPreset())
        
        # Crear y ejecutar reporte
        report = Report(metrics=metrics)
        
        report.run(
            reference_data=self.reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping,
        )
        
        # Guardar reporte
        if report_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"drift_report_{timestamp}.html"
        
        report_path = REPORTS_PATH / report_name
        report.save_html(str(report_path))
        
        logger.info(f"Reporte guardado en: {report_path}")
        
        return report_path
    
    def run_tests(
        self,
        current_data: pd.DataFrame,
    ) -> Tuple[bool, Dict]:
        """
        Ejecuta tests automatizados de data drift y calidad.
        
        Args:
            current_data: DataFrame con datos actuales.
            
        Returns:
            Tupla (todos_los_tests_pasaron, resultados_detallados)
        """
        logger.info("Ejecutando tests de monitoreo...")
        
        # Crear suite de tests
        test_suite = TestSuite(tests=[
            DataDriftTestPreset(),
            DataQualityTestPreset(),
        ])
        
        test_suite.run(
            reference_data=self.reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping,
        )
        
        # Obtener resultados
        result = test_suite.as_dict()
        
        # Parsear resultados de tests
        all_passed = True
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
            },
            "tests": [],
        }
        
        try:
            tests = result.get("tests", [])
            test_results["summary"]["total"] = len(tests)
            
            for test in tests:
                test_info = {
                    "name": test.get("name", "Unknown"),
                    "status": test.get("status", "UNKNOWN"),
                    "description": test.get("description", ""),
                }
                
                if test.get("status") == "SUCCESS":
                    test_results["summary"]["passed"] += 1
                else:
                    test_results["summary"]["failed"] += 1
                    all_passed = False
                
                test_results["tests"].append(test_info)
        
        except Exception as e:
            logger.error(f"Error parseando resultados de tests: {e}")
            all_passed = False
        
        logger.info(
            f"Tests completados: {test_results['summary']['passed']}/{test_results['summary']['total']} pasaron"
        )
        
        return all_passed, test_results
    
    def get_reference_stats(self) -> Dict:
        """
        Retorna estadísticas descriptivas de los datos de referencia.
        
        Returns:
            Diccionario con estadísticas por feature.
        """
        stats = {
            "num_rows": len(self.reference_data),
            "features": {},
        }
        
        for col in self.numerical_features:
            if col in self.reference_data.columns:
                stats["features"][col] = {
                    "mean": float(self.reference_data[col].mean()),
                    "std": float(self.reference_data[col].std()),
                    "min": float(self.reference_data[col].min()),
                    "max": float(self.reference_data[col].max()),
                    "median": float(self.reference_data[col].median()),
                }
        
        if self.target_column in self.reference_data.columns:
            stats["target_distribution"] = (
                self.reference_data[self.target_column]
                .value_counts(normalize=True)
                .to_dict()
            )
        
        return stats


# =============================================================================
# Funciones de conveniencia
# =============================================================================

_detector: Optional[DriftDetector] = None


def get_detector() -> DriftDetector:
    """
    Obtiene la instancia singleton del detector de drift.
    """
    global _detector
    if _detector is None:
        _detector = DriftDetector()
    return _detector


def quick_drift_check(current_data: pd.DataFrame) -> Dict:
    """
    Ejecuta un chequeo rápido de drift.
    
    Args:
        current_data: DataFrame con datos actuales.
        
    Returns:
        Diccionario con resultados del drift.
    """
    detector = get_detector()
    return detector.detect_drift(current_data)

