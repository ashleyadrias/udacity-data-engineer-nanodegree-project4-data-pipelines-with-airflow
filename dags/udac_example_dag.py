import datetime
import logging
from datetime import datetime, timedelta
import os

from airflow import DAG
#Fetch credentials, variables, and connections from Airflow
from airflow.models import Variable
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator
#Import S3 Hooks
from airflow.hooks.S3_hook import S3Hook
from airflow.operators import (StageToRedshiftOperator,
                               LoadFactOperator,
                               LoadDimensionOperator,
                               DataQualityOperator)
from helpers import SqlQueries

#AWS_KEY = os.environ.get('AWS_KEY')
#AWS_SECRET = os.environ.get('AWS_SECRET')

def start():
    logging.info("Start of DAG")
    
def end():
    logging.info("End of DAG")

def lit_keys():
    hook = S3Hook(aws_conn_id='aws_credentials')
    bucket = Variable.get('s3_bucket')
    
    keys = hook.list_keys(bucket)
    for key in keys:
        logging.info(f"- Listing Keys from  s3://{key}")
 

default_args = {
    'owner': 'udacity',
    'start_date': datetime.now(),#datetime(2019, 1, 12)
    'depends_on_past'=True,
    'wait_for_downstream'=True,
    'retires'=3,
    'retry_delay'=timedelta(minutes=2),
    'catchup'=True
}

dag = DAG('udac_example_dag',
          default_args=default_args,
          description='Load and transform data in Redshift with Airflow',
          schedule_interval='@hourly'
        )

start_operator = PythonOperator(
    task_id='Begin_execution',
    python_callable= start, 
    dag=dag)

# list_task = PythonOperator(
#     task_id="list_keys",
#     python_callable=list_keys,
#     dag=dag
# )

create_table = PostgresOperator(
    task_id="create_table",
    dag=dag,
    postgres_conn_id="redshift",
    sql=SqlQueries.create_tables
)

stage_events_to_redshift = StageToRedshiftOperator(
    task_id='Stage_events',
    dag=dag,
    table="staging_events",
    redshift_conn_id="redshift",
    aws_credentials_id="aws_credentials",
    s3_bucket="dend",
    s3_key="log_data"
)

stage_songs_to_redshift = StageToRedshiftOperator(
    task_id='Stage_songs',
    dag=dag,
    table="staging_songs",
    redshift_conn_id="redshift",
    aws_credentials_id="aws_credentials",
    s3_bucket="dend",
    s3_key="song_data"
)

load_songplays_table = LoadFactOperator(
    task_id='Load_songplays_fact_table',
    dag=dag,
    postgres_conn_id="redshift",
    sql=SqlQueries.songplay_table_insert
)

load_user_dimension_table = LoadDimensionOperator(
    task_id='Load_user_dim_table',
    dag=dag,
    postgres_conn_id="redshift",
    sql=SqlQueries.user_table_insert
)

load_song_dimension_table = LoadDimensionOperator(
    task_id='Load_song_dim_table',
    dag=dag,
    postgres_conn_id="redshift",
    sql=SqlQueries.song_table_insert
)

load_artist_dimension_table = LoadDimensionOperator(
    task_id='Load_artist_dim_table',
    dag=dag,
    postgres_conn_id="redshift",
    sql=SqlQueries.artist_table_insert
)

load_time_dimension_table = LoadDimensionOperator(
    task_id='Load_time_dim_table',
    dag=dag,
    postgres_conn_id="redshift",
    sql=SqlQueries.time_table_insert
)

run_quality_checks = DataQualityOperator(
    task_id='Run_data_quality_checks',
    dag=dag,
    provide_context=True,
    params={
        'table': 'artists', 'songplays', 'songs', 'users'
    }
)

end_operator = PythonOperator(
    task_id='Stop_execution', 
    python_callable= end,
    dag=dag)

#Setup Task Dependacies
#start_operator >> list_task
start_operator >> create_table 

#start_operator >> stage_events_to_redshift
#start_operator >> stage_songs_to_redshift

create_table >> stage_events_to_redshift
create_table >> stage_songs_to_redshift

#list_task >> stage_events_to_redshift
#list_task >> stage_songs_to_redshift

stage_events_to_redshift >> load_songplays_table
stage_songs_to_redshift >> load_songplays_table

load_songplays_table >> load_song_dimension_table
load_songplays_table >> load_user_dimension_table
load_songplays_table >> load_artist_dimension_table
load_songplays_table >> load_time_dimension_table

load_song_dimension_table >> run_quality_checks
load_user_dimension_table >> run_quality_checks
load_artist_dimension_table >> run_quality_checks
load_time_dimension_table >> run_quality_checks

run_quality_checks >> end_operator