"""
=========================================================================
this sets up a file watcher that catches a whole bunch of products
and triggers DAGs and changes their status in the metadata db.
=========================================================================
Tasks in this DAG watch the imars metadata db for `status_id=="to_load"`
files of a certain `product` type. The `product.short_name` is used in the
name of the DAG in the form `file_trigger_{short_name}.py`. The
`last_processed` column is used to prioritize DAG triggering.

A file_trigger DAG only triggers external processing DAGs and updates
`file.status_id`.

---------------------------------------------------------------------------

External DAGs triggered should be triggered with `execution_date` set using
metadata from the file. Because of this each file within a `product_id`
and `area_id` must have a unique `date_time`.
I.e.:
```mysql
SELECT COUNT(*) FROM file WHERE
    date_time="2015-02-01 13:30:00" AND product_id=6;
```
should return only 1 result for any value of `date_time` and `product_id`.

This should be enforced by the following constraint:
`CONSTRAINT pid_and_date UNIQUE(product_id,date_time,area_id)`

---------------------------------------------------------------------------

The following diagram illustrates the relationship between this DAG and
`file.state` in the metadata db:

```
                                                    |====> ["std"]
(auto_ingest_dag) =|                                |
manual_ingest =====|==> ["to_load"] ==(file_trigger_dag)===> (processing_dag_1)
                                                      |====> (processing_dag_2)
                                                      |       ...
key:                                                  |====> (processing_dag_n)
---------
(dag_name)
["status"]

```
"""
from airflow import DAG

from imars_dags.operators.FileWatcher.FileWatcherOperator \
    import FileWatcherOperator
from imars_dags.util.get_dag_id import get_dag_id
from imars_dags.util.DAGType import DAGType


this_dag = DAG(
    dag_id="file_watcher",
    catchup=False,  # latest only
)
claimed_ids = []
with this_dag as dag:
    id_list = [
        x for x in range(7, 35) if x not in [11]
    ]
    assert [x not in claimed_ids for x in id_list]
    unprocessed_watcher_task = FileWatcherOperator(
        task_id="unprocessed_watcher_task",
        product_ids=id_list,
        dags_to_trigger=[],
    )
    claimed_ids.extend(id_list)

    assert 35 not in claimed_ids
    file_trigger_myd0_otis_l2 = FileWatcherOperator(
        task_id='file_trigger_myd0_otis_l2',
        product_ids=[35],
        dags_to_trigger=[
            # "processing_l2_to_l3_pass"  # deprecated
        ],
        area_names=[],
    )
    claimed_ids.append(35)

    assert 5 not in claimed_ids
    file_trigger_myd01 = FileWatcherOperator(
        task_id="file_trigger_myd01",
        product_ids=[5],
        dags_to_trigger=[
            # "proc_myd01_to_myd0_otis_l2"  # deprecated
            get_dag_id(
                dag_name="modis_aqua_pass", dag_type=DAGType.PROCESSING
            )
        ],
        area_names=['gom', 'fgbnms'],
    )
    claimed_ids.append(5)

    assert 11 not in claimed_ids
    file_trigger_ntf_wv2_m1bs = FileWatcherOperator(
        task_id="file_trigger_ntf_wv2_m1bs",
        product_ids=[11],
        dags_to_trigger=[
            # "proc_wv2_classification"  # deprecated
            get_dag_id(
                dag_name="wv2_classification", dag_type=DAGType.PROCESSING
            )
        ],
        area_names=['na', 'big_bend'],
    )
    claimed_ids.append(11)

    assert 6 not in claimed_ids
    file_trigger_zip_wv2_ftp_ingest = FileWatcherOperator(
        task_id="file_trigger_zip_wv2_ftp_ingest",
        product_ids=[6],
        dags_to_trigger=[
            "proc_wv2_unzip"
        ],
    )
    claimed_ids.append(6)

    # assert no duplicates in claimed_ids
    # (https://stackoverflow.com/a/1541827/1483986)
    if len(claimed_ids) != len(set(claimed_ids)):
        raise AssertionError(
            "too many claims on product #s {}".format(
                set([x for x in claimed_ids if claimed_ids.count(x) > 1])
                )
        )