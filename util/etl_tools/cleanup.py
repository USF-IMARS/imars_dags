"""
# === /tmp/ cleanup
# ======================================================================
"""

from airflow.operators.python_operator import PythonOperator
from airflow.operators.sensors import SqlSensor
from datetime import timedelta
import shutil

def add_cleanup(dag, to_cleanup):
    with dag as dag:
        def tmp_cleanup_task(**kwargs):
            to_cleanup = kwargs['to_cleanup']
            for cleanup_path in to_cleanup:
                cleanup_path = kwargs['task'].render_template(
                    '',
                    cleanup_path,
                    kwargs
                )
                if (cleanup_path.startswith(TMP_PREFIX)) and len(cleanup_path.strip()) > len(TMP_PREFIX):
                    print('rm -rf {}'.format(cleanup_path))
                    # TODO: shutil.rmtree(cleanup_path)
                else:
                    raise ValueError(
                        "\ncleanup paths must be in /tmp/ dir '{}'".format(TMP_PREFIX) +
                        "\n\t you attempted to 'rm -rf {}'".format(cleanup_path)
                    )

        tmp_cleanup = PythonOperator(
            task_id='tmp_cleanup',
            python_callable=tmp_cleanup_task,
            op_kwargs={'to_cleanup': to_cleanup},
            provide_context=True,
        )

        # to ensure we clean up even if something in the middle fails, we must
        # do some weird stuff. For details see:
        # https://github.com/USF-IMARS/imars_dags/issues/44
        poke_until_tmp_cleanup_done = SqlSensor(
            # poke until the cleanup is done
            task_id='poke_until_tmp_cleanup_done',
            conn_id='airflow_metadata',
            soft_fail=False,
            poke_interval=60*2,              # check every two minutes
            timeout=60*9,                    # for the first 9 minutes
            retries=10,                      # don't give up easily
            retry_delay=timedelta(hours=1),  # but be patient between checks
            retry_exponential_backoff=True,
            sql="""
            SELECT * FROM task_instance WHERE
                task_id="tmp_cleanup"
                AND state IN ('success','failed')
                AND dag_id="{{ dag.dag_id }}"
                AND execution_date="{{ execution_date }}";
            """
        )
        # start poking immediately
        # TODO: do we need another upstream task added here?
        # extract_file >> poke_until_tmp_cleanup_done

    return tmp_cleanup
