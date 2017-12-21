"""
airflow processing pipeline definition for MODIS aqua daily processing
"""
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.subdag_operator import SubDagOperator
from airflow.operators.sensors import ExternalTaskSensor
from datetime import timedelta, datetime

# === ./imars_dags/modis_aqua_processing.py :
from imars_dags.util.globals import QUEUE, DEFAULT_ARGS, SLEEP_ARGS
from imars_dags.util import satfilename
from imars_dags.settings.regions import REGIONS

default_args = DEFAULT_ARGS.copy()
# NOTE: start_date must be 12:00 (see _wait_for_passes_subdag)
default_args.update({
    'start_date': datetime(2017, 12, 16, 12, 0),
    'retries': 1
})
this_dag = DAG(
    'modis_aqua_daily',
    default_args=default_args,
    schedule_interval=timedelta(days=1),
    max_active_runs=1  # this must be limited b/c the subdag spawns 288 tasks,
                       # which can easily lead to deadlocks.
)

# =============================================================================
# === wait for pass-level processing
# =============================================================================
# spin up an ExternalTaskSensor for each pass so that we wait for the
# pass-level processing to complete before continuing.
# [ref](https://stackoverflow.com/a/38028511/1483986)
def _wait_for_passes_subdag(start_date, schedule_interval, def_args):
    subdag = DAG(
        'modis_aqua_daily.wait_for_passes',
        schedule_interval=schedule_interval,
        start_date=start_date,
        default_args=def_args
    )
    # here we assume that the execution date is at time 12:00
    # 144*2=288 5-minute dags per day (24*60/5=288)
    for tdelta in range(-144, 144):
        net_minutes = 12*60 + tdelta*5
        hr = int(net_minutes/60)
        mn = net_minutes%60
        ExternalTaskSensor(
            task_id='wait_for_passes_{}_{}'.format(hr,mn),
            external_dag_id='modis_aqua_passes',
            external_task_id='l2gen',
            allowed_states=['success','skipped'],  # skip means granule not in ROI
            execution_delta=timedelta(minutes=tdelta),
            dag=subdag,
            **SLEEP_ARGS
        )
    return subdag

pass_wait_args = SLEEP_ARGS.copy()
pass_wait_args.update({"execution_timeout": timedelta(minutes=10)})
wait_for_passes = SubDagOperator(
    subdag=_wait_for_passes_subdag(
        this_dag.start_date,
        this_dag.schedule_interval,
        this_dag.default_args
    ),
    task_id='wait_for_passes',
    dag=this_dag,
    **pass_wait_args
)

# =============================================================================
# === L3 Generation using GPT graph
# =============================================================================
# this assumes the l2 files for the whole day have already been generated
#
# example cmd:
#     /opt/snap/5.0.0/bin/gpt L3G_MODA_GOM_vIMARS.xml
#     -t /home1/scratch/epa/satellite/modis/GOM/L3G_OC/A2017313_map.nc
#     -f NetCDF-BEAM
#     /srv/imars-objects/modis_aqua_gom/l2/A2017313174500.L2
#     /srv/imars-objects/modis_aqua_gom/l2/A2017313192000.L2
#     /srv/imars-objects/modis_aqua_gom/l2/A2017313192500.L2
#
#     -t is the target (output) file, -f is the format

def get_list_todays_l2s_cmd(exec_date):
    """
    returns an ls command that lists all l2 files using the path & file fmt,
    but replaces hour/minute with wildcard *
    """
    satfilename.l2(exec_date)
    fmt_str = satfilename.l2_filename_fmt.replace("%M", "*").replace("%H", "*")
    return "ls " + satfilename.l2_basepath + exec_date.strftime(fmt_str)

l3gen = BashOperator(
    task_id="l3gen",
    bash_command="""
        /opt/snap/5.0.0/bin/gpt /root/airflow/dags/imars_dags/settings/L3G_MODA_GOM_vIMARS.xml \
        -t {{ params.satfilename.l3(execution_date) }} \
        -f NetCDF-BEAM \
        `{{ params.get_list_todays_l2s_cmd(execution_date) }}`
    """,
    params={
        'satfilename': satfilename,
        'get_list_todays_l2s_cmd':get_list_todays_l2s_cmd
    },
    queue=QUEUE.SNAP,
    dag=this_dag
)
wait_for_passes >> l3gen
# =============================================================================
# =============================================================================
# === export png(s) from l3 netCDF4 file
# =============================================================================
# vars we *could* export from the l3 generated earlier:
var_list = [
    "chlor_a",
    "nflh",
    "adg_443_giop",
    "Rrs_667"
#   lat
#   lon
]
for variable_name in var_list:
    l3_to_png = BashOperator(
        task_id="l3_to_png_"+variable_name,
        bash_command="""
        /opt/sat-scripts/sat-scripts/netcdf4_to_png.py
        {{params.satfilename.l3(execution_date)}}
        {{params.satfilename.png(execution_date, params.variable_name)}}
        {{params.variable_name}}
        """,
        params={
            'satfilename': satfilename,
            'variable_name': variable_name
        },
        queue=QUEUE.SAT_SCRIPTS,
        dag=this_dag
    )
    l3gen >> l3_to_png
# =============================================================================
