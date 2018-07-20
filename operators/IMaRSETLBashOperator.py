from airflow.operators.bash_operator import BashOperator

from imars_dags.operators.IMaRSETLMixin import IMaRSETLMixin


class IMaRSETLPythonOperator(IMaRSETLMixin, BashOperator):

    def __init__(
        self,
        *args,

        dag=None,
        inputs={},  # aka extracts\
        outputs={},  # aka loads
        tmpdirs=[],

        **kwargs
    ):
        self.pre_init(inputs, outputs, tmpdirs, dag)

        super(IMaRSETLPythonOperator, self).__init__(
            *args,
            dag=dag,
            **kwargs
        )
