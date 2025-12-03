"""
DAG de prueba: hello_airflow
============================
Este DAG sirve como smoke test para verificar que Apache Airflow
está funcionando correctamente en Docker.

Uso:
    1. Levanta Airflow con: docker compose up
    2. Accede a http://localhost:8080
    3. Usuario: airflow / Password: airflow
    4. Busca el DAG "hello_airflow" en la lista
    5. Actívalo y ejecuta manualmente para probar

Autor: MLOps Team
Proyecto: air-quality-mlops
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator


# -----------------------------------------------------------------------------
# Argumentos por defecto para todas las tareas del DAG
# -----------------------------------------------------------------------------
default_args = {
    "owner": "mlops-team",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


# -----------------------------------------------------------------------------
# Función de ejemplo que se ejecutará en una tarea
# -----------------------------------------------------------------------------
def print_hello():
    """Imprime un mensaje de bienvenida en los logs de Airflow."""
    print("=" * 60)
    print("¡Hola desde Apache Airflow!")
    print("El entorno de MLOps está funcionando correctamente.")
    print("=" * 60)
    return "Hello Airflow!"


# -----------------------------------------------------------------------------
# Definición del DAG
# -----------------------------------------------------------------------------
with DAG(
    dag_id="hello_airflow",
    description="DAG de prueba para verificar que Airflow funciona correctamente",
    default_args=default_args,
    # Fecha de inicio fija en el pasado (no se ejecutará retroactivamente por catchup=False)
    start_date=datetime(2024, 1, 1),
    # Programación diaria
    schedule_interval="@daily",
    # No ejecutar tareas retroactivas desde start_date hasta hoy
    catchup=False,
    # Tags para organizar DAGs en la UI
    tags=["test", "hello", "smoke-test"],
) as dag:
    
    # -------------------------------------------------------------------------
    # Tareas del DAG
    # -------------------------------------------------------------------------
    
    # Tarea 1: Inicio (EmptyOperator - no hace nada, solo marca el inicio)
    start = EmptyOperator(
        task_id="start",
        doc="Marca el inicio del DAG",
    )
    
    # Tarea 2: Ejecutar función Python
    hello_task = PythonOperator(
        task_id="say_hello",
        python_callable=print_hello,
        doc="Imprime un mensaje de bienvenida",
    )
    
    # Tarea 3: Fin (EmptyOperator - marca el fin del flujo)
    end = EmptyOperator(
        task_id="end",
        doc="Marca el fin del DAG",
    )
    
    # -------------------------------------------------------------------------
    # Definir dependencias (orden de ejecución)
    # -------------------------------------------------------------------------
    # start -> say_hello -> end
    start >> hello_task >> end

