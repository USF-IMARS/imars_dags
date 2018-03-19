# =========================================================================
# wv2 unzip to final destination
# =========================================================================
from datetime import datetime,timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.mysql_operator import MySqlOperator
from airflow.operators.sensors import SqlSensor

from imars_dags.util.globals import DEFAULT_ARGS
import imars_etl

default_args = DEFAULT_ARGS.copy()
default_args.update({
    'start_date': datetime(2018, 3, 5, 16, 0),
    'retries': 1
})

this_dag = DAG(
    dag_id="wv2_unzip",
    default_args=default_args,
    schedule_interval=timedelta(days=1)
)

# === wait for a valid target to process
SQL_SELECTION="status = 3 AND product_type_id = 6"
SQL_STR="SELECT id FROM file WHERE " + SQL_SELECTION
check_for_to_loads = SqlSensor(
    task_id='check_for_to_loads',
    conn_id="imars_metadata",
    sql=SQL_STR,
    soft_fail=True,
    dag=this_dag
)

# TODO: should set imars_product_metadata.status to "processing" to prevent
#    duplicates?

# === Extract
def extract_file(**kwargs):
    ti = kwargs['ti']
    fname = imars_etl.extract({
        "sql":SQL_SELECTION
    })['filepath']
    ti.xcom_push(key='fname', value=fname)
    return fname

extract_file = PythonOperator(
    task_id='extract_file',
    provide_context=True,
    python_callable=extract_file,
    dag=this_dag
)
check_for_to_loads >> extract_file

# === Transform
unzip_wv2_ingest = BashOperator(
    task_id="unzip_wv2_ingest",
    dag = this_dag,
    bash_command="""
        unzip \
            {{ ti.xcom_pull(task_ids="extract_file", key="fname") }} \
            -d /tmp/airflow_output_{{ ts }}
    """
)
extract_file >> unzip_wv2_ingest

# === load result(s)
def load_file(**kwargs):
    ti = kwargs['ti']
    metadata={  # metadata of the file (or dir) we are outputting
        "filepath": ti.xcom_pull(task_ids="extract_file", key="fname"),
        "type":6
    }
    imars_etl.load(metadata)

load_file = PythonOperator(
    task_id='load_file',
    provide_context=True,
    python_callable=load_file,
    dag=this_dag
)
unzip_wv2_ingest >> load_file

# === wv2 schedule zip file for deletion
update_input_file_meta_db = MySqlOperator(
    task_id="update_input_file_meta_db",
    sql=""" UPDATE file SET status="to_delete" WHERE filepath="{{ ti.xcom_pull(task_ids="extract_file", key="fname") }}" """,
    mysql_conn_id='imars_metadata',
    autocommit=False,  # TODO: True?
    parameters=None,
    dag=this_dag
)
load_file >> update_input_file_meta_db
