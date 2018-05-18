# =========================================================================
# wv2 unzip to final destination
# =========================================================================
from datetime import datetime,timedelta

from airflow import DAG
from airflow.operators.bash_operator import BashOperator

from imars_dags.util.globals import DEFAULT_ARGS
import imars_dags.util.imars_etl as imars_etl_builder

default_args = DEFAULT_ARGS.copy()
default_args.update({
    'start_date': datetime(1980, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
})

this_dag = DAG(
    dag_id="proc_wv2_unzip_na",
    default_args=default_args,
    schedule_interval=None,
)

UNZIP_DIR = imars_etl_builder.tmp_filepath(this_dag.dag_id, "unzip_dir")
unzip_wv2_ingest = BashOperator(
    task_id="unzip_wv2_ingest",
    dag = this_dag,
    bash_command="""
        unzip \
            {{ ti.xcom_pull(task_ids="extract_file") }} \
            -d """ + UNZIP_DIR
)

# these GIS_FILES need to be removed so they don't get accidentally ingested
# later on.
rm_spurrious_gis_files = BashOperator(
    task_id="rm_spurrious_gis_files",
    dag=this_dag,
    bash_command="""
        rm -r """ + UNZIP_DIR + """/*/*/GIS_FILES
    """
)
unzip_wv2_ingest >> rm_spurrious_gis_files

COMMON_JSON='{"status_id":3, "area_id":5}'
# a list of params for products we are loading from the output directory
to_load=[
    # INSERT INTO product (short_name,full_name,satellite,sensor) VALUES("att_wv2_m1bs","wv2 m 1b .att","worldview2","multispectral")
    {
        "product_type_name":"att_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json":COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("eph_wv2_m1bs","wv2 1b multispectral .eph","worldview2")
    {
        "product_type_name": "eph_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("geo_wv2_m1bs","wv2 1b multispectral .geo","worldview2")
    {
        "product_type_name": "geo_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("imd_wv2_m1bs","wv2 1b multispectral .imd","worldview2")
    {
        "product_type_name": "imd_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("ntf_wv2_m1bs","wv2 1b multispectral .ntf","worldview2");
    {
        "product_type_name": "ntf_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("rpb_wv2_m1bs","wv2 1b multispectral .rpb","worldview2");
    {
        "product_type_name": "rpb_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("til_wv2_m1bs","wv2 1b multispectral .til","worldview2");
    {
        "product_type_name": "til_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("xml_wv2_m1bs","wv2 1b multispectral .xml","worldview2");
    {
        "product_type_name": "xml_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("jpg_wv2_m1bs","wv2 1b multispectral .jpg","worldview2");
    {
        "product_type_name": "jpg_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("txt_wv2_m1bs","wv2 1b multispectral readme","worldview2");
    {
        "product_type_name": "txt_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # # # GIS FILES # load "$unzipped_path/GIS_FILES/"
    # INSERT INTO product (short_name,full_name,satellite) VALUES("shx_wv2_m1bs","wv2 1b multispectral .shx","worldview2");
    {
        "product_type_name": "shx_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("shp_wv2_m1bs","wv2 1b multispectral .shp","worldview2");
    {
        "product_type_name": "shp_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("prj_wv2_m1bs","wv2 1b multispectral .prj","worldview2");
    {
        "product_type_name": "prj_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("dbf_wv2_m1bs","wv2 1b multispectral .dbf","worldview2");
    {
        "product_type_name": "dbf_wv2_m1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },

    # INSERT INTO product (short_name,full_name,satellite) VALUES("att_wv2_p1bs","wv2 1b panchromatic .att","worldview2")
    {
        "product_type_name": "att_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("eph_wv2_p1bs","wv2 1b panchromatic .eph","worldview2");
    {
        "product_type_name": "eph_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("geo_wv2_p1bs","wv2 1b panchromatic .geo","worldview2");
    {
        "product_type_name": "geo_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("imd_wv2_p1bs","wv2 1b panchromatic .imd","worldview2");
    {
        "product_type_name": "imd_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("ntf_wv2_p1bs","wv2 1b panchromatic .ntf","worldview2");
    {
        "product_type_name": "ntf_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("rpb_wv2_p1bs","wv2 1b panchromatic .rpb","worldview2");
    {
        "product_type_name": "rpb_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("til_wv2_p1bs","wv2 1b panchromatic .til","worldview2");
    {
        "product_type_name": "til_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("xml_wv2_p1bs","wv2 1b panchromatic .xml","worldview2");
    {
        "product_type_name": "xml_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("jpg_wv2_p1bs","wv2 1b panchromatic .jpg","worldview2");
    {
        "product_type_name": "jpg_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("txt_wv2_p1bs","wv2 1b panchromatic readme","worldview2");
    {
        "product_type_name": "txt_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # # # GIS_FILES
    # INSERT INTO product (short_name,full_name,satellite) VALUES("shx_wv2_p1bs","wv2 1b panchromatic .shx","worldview2");
    {
        "product_type_name": "shx_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("shp_wv2_p1bs","wv2 1b panchromatic .shp","worldview2");
    {
        "product_type_name": "shp_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    },
    # INSERT INTO product (short_name,full_name,satellite) VALUES("dbf_wv2_p1bs","wv2 1b panchromatic .dbf","worldview2");
    {
        "product_type_name": "dbf_wv2_p1bs",
        "directory": UNZIP_DIR,
        "json": COMMON_JSON
    }
]

imars_etl_builder.add_tasks(
    this_dag, "product_id=6", [unzip_wv2_ingest], [rm_spurrious_gis_files],
    products_to_load_from_dir=to_load,
    to_cleanup=[UNZIP_DIR]
)