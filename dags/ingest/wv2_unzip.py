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
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
})

this_dag = DAG(
    dag_id="wv2_unzip",
    default_args=default_args,
    schedule_interval=timedelta(hours=1),
    catchup=False,  # NOTE: this & max_active_runs prevents duplicate extractions
    max_active_runs=1
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
#    duplicates? Not an issue so long as catchup=False & max_active_runs=1

# === Extract
# ============================================================================
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
# ============================================================================
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

# these GIS_FILES need to be removed so they don't get accidentally ingested
# later on.
rm_spurrious_gis_files = BashOperator(
    task_id="rm_spurrious_gis_files",
    dag=this_dag,
    bash_command="""
        rm -r /tmp/airflow_output_{{ ts }}/*/*/GIS_FILES
    """
)
unzip_wv2_ingest >> rm_spurrious_gis_files

# === wv2 schedule zip file for deletion
update_input_file_meta_db = MySqlOperator(
    task_id="update_input_file_meta_db",
    sql=""" UPDATE file SET status=1 WHERE filepath="{{ ti.xcom_pull(task_ids="extract_file", key="fname") }}" """,
    mysql_conn_id='imars_metadata',
    autocommit=False,  # TODO: True?
    parameters=None,
    dag=this_dag
)

# === delete any remaining junk we left in /tmp/
tmp_cleanup = BashOperator(
    task_id="tmp_cleanup",
    dag=this_dag,
    bash_command="""
        rm -r /tmp/airflow_output_{{ ts }}
    """
)

# === Load
# ============================================================================
LOAD_TEMPLATE="""
    /opt/imars-etl/imars-etl.py -vvv load \
        --product_type_name {{ params.product_type_name }} \
        --json '{{ params.json }}' \
        --directory /tmp/airflow_output_{{ ts }}
"""

# a list of params for products we are loading from the output directory
to_load=[
    # INSERT INTO product (short_name,full_name,satellite,sensor) VALUES("att_wv2_m1bs","wv2 m 1b .att","worldview2","multispectral")
    "att_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("eph_wv2_m1bs","wv2 1b multispectral .eph","worldview2")
    "eph_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("geo_wv2_m1bs","wv2 1b multispectral .geo","worldview2")
    "geo_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("imd_wv2_m1bs","wv2 1b multispectral .imd","worldview2")
    "imd_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("ntf_wv2_m1bs","wv2 1b multispectral .ntf","worldview2");
    "ntf_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("rpb_wv2_m1bs","wv2 1b multispectral .rpb","worldview2");
    "rpb_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("til_wv2_m1bs","wv2 1b multispectral .til","worldview2");
    "til_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("xml_wv2_m1bs","wv2 1b multispectral .xml","worldview2");
    "xml_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("jpg_wv2_m1bs","wv2 1b multispectral .jpg","worldview2");
    "jpg_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("txt_wv2_m1bs","wv2 1b multispectral readme","worldview2");
    "txt_wv2_m1bs",
    # # # GIS FILES # load "$unzipped_path/GIS_FILES/"
    # INSERT INTO product (short_name,full_name,satellite) VALUES("shx_wv2_m1bs","wv2 1b multispectral .shx","worldview2");
    "shx_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("shp_wv2_m1bs","wv2 1b multispectral .shp","worldview2");
    "shp_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("prj_wv2_m1bs","wv2 1b multispectral .prj","worldview2");
    "prj_wv2_m1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("dbf_wv2_m1bs","wv2 1b multispectral .dbf","worldview2");
    "dbf_wv2_m1bs",

    # INSERT INTO product (short_name,full_name,satellite) VALUES("att_wv2_p1bs","wv2 1b panchromatic .att","worldview2")
    "att_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("eph_wv2_p1bs","wv2 1b panchromatic .eph","worldview2");
    "eph_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("geo_wv2_p1bs","wv2 1b panchromatic .geo","worldview2");
    "geo_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("imd_wv2_p1bs","wv2 1b panchromatic .imd","worldview2");
    "imd_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("ntf_wv2_p1bs","wv2 1b panchromatic .ntf","worldview2");
    "ntf_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("rpb_wv2_p1bs","wv2 1b panchromatic .rpb","worldview2");
    "rpb_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("til_wv2_p1bs","wv2 1b panchromatic .til","worldview2");
    "til_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("xml_wv2_p1bs","wv2 1b panchromatic .xml","worldview2");
    "xml_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("jpg_wv2_p1bs","wv2 1b panchromatic .jpg","worldview2");
    "jpg_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("txt_wv2_p1bs","wv2 1b panchromatic readme","worldview2");
    "txt_wv2_p1bs",
    # # # GIS_FILES
    # INSERT INTO product (short_name,full_name,satellite) VALUES("shx_wv2_p1bs","wv2 1b panchromatic .shx","worldview2");
    "shx_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("shp_wv2_p1bs","wv2 1b panchromatic .shp","worldview2");
    "shp_wv2_p1bs",
    # INSERT INTO product (short_name,full_name,satellite) VALUES("dbf_wv2_p1bs","wv2 1b panchromatic .dbf","worldview2");
    "dbf_wv2_p1bs",
]

# imars-etl.load each of the file products listed in to_load
for product_short_name in to_load:
    # set params common to all files being loaded:
    output_params = {
        "json":'{"status":3, "area_id":5}',
        "product_type_name": product_short_name
    }

    load_operator = BashOperator(
        task_id="load_" + product_short_name,
        dag = this_dag,
        bash_command=LOAD_TEMPLATE,
        params=output_params
    )
    rm_spurrious_gis_files >> load_operator
    load_operator >> update_input_file_meta_db
    load_operator >> tmp_cleanup
