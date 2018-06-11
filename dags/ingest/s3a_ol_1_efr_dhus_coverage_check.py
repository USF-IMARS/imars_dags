from datetime import timedelta

# unused DAG import is required for airflow to find the dag
from airflow import DAG  # noqa:F401
from imars_dags.dags.ingest.dhus.DHUSCoverageCheckDAG \
    import DHUSCoverageCheckDAG
from imars_dags.regions import gom

this_dag = DHUSCoverageCheckDAG(
    region=gom,
    region_short_name='gom',
    region_id=1,

    product_short_name='s3a_ol_1_efr',
    product_id=36,

    dhus_search_kwargs={
        # https://scihub.copernicus.eu/s3/api/stub/products?filter=OLCI%20AND%20(%20footprint:%22Intersects(POLYGON((-68.41794442091795%2018.587370193332475,-65.7408430169118%2018.587370193332475,-65.7408430169118%2021.005279979061285,-68.41794442091795%2021.005279979061285,-68.41794442091795%2018.587370193332475)))%22%20)&offset=0&limit=25&sortedby=ingestiondate&order=desc
        'echo_collection_id': 'C1370679936-OB_DAAC',
    },
    granule_len=timedelta(minutes=3),
    check_delay=timedelta(hours=3)
)