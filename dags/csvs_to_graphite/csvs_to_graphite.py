"""
Reads each csv file and pushes the data into graphite.
"""

from datetime import datetime

from airflow import DAG
from airflow.operators.bash_operator import BashOperator

from imars_dags.util.get_default_args import get_default_args


this_dag = DAG(
    dag_id="csvs_to_graphite",
    default_args=get_default_args(
        start_date=datetime(2018, 7, 30)
    ),
    schedule_interval="@weekly",
    catchup=False,
    max_active_runs=1,
)

# for args in CSV2GRAPH_ARGS:
#     PythonOperator(
#         task_id=(
#             "csv2graphite_" +
#             args[1].replace('.', '_').replace('imars_regions_', '')
#         ),
#         python_callable=csv2graph,
#         dag=this_dag,
#         op_args=args,
#         provide_context=True,
#     )
# same thing, but as bash op:
BashOperator(
    task_id=(
        "all_csvs2graphite"
    ),
    bash_command="""
        python2
        /home/airflow/dags/imars_dags/dags/csvs_to_graphite/_csvs_to_graphite.py
    """,
    dag=this_dag,
)