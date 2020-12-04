from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from celery.utils.log import get_task_logger
from . import models
import configparser

logger = get_task_logger(__name__)

session_factory=None

config=configparser.ConfigParser()
config.read('/run/secrets/production.ini')

def after_commit_task_hook(success,task,run_on_failure=False,run_on_success=True,task_args=[],task_kwargs={}):
    if (success and run_on_success) or (not success and run_on_failure):
        task.delay(*task_args,**task_kwargs)

@worker_process_init.connect
def bootstrap_pyramid(signal, sender, **kwargs):

    global session_factory
    
    import os
    from pyramid.paster import bootstrap

    settings = bootstrap('/run/secrets/production.ini')['registry'].settings

    engine=models.get_engine(settings,prefix='sqlalchemy.')
    
    while True:

        # Here we try to connect to database server until connection succeeds.
        # This is needed because the database server may take longer
        # to start than the application
        
        import sqlalchemy.exc

        try:
            print("Checking database connection")
            conn=engine.connect()
            conn.execute("select 'OK'")

        except sqlalchemy.exc.OperationalError:
            import time
            print("Connection failed. Sleeping.")
            time.sleep(2)
            continue
        
        # If we get to this line, connection has succeeded so we break
        # out of the loop
        conn.close()
        break
    
    session_factory=models.get_session_factory(engine)

try:
    backend=config['celery']['backend_url']
except KeyError:
    backend='rpc://cycling_test_rabbitmq'

try:
    broker=config['celery']['broker_url']
except KeyError:
    broker='pyamqp://guest@cycling_test_rabbitmq'

celery=Celery(backend=backend, broker=broker)
celery.config_from_object('cycling_data.celeryconfig')
celery.conf.task_default_queue='task_default'
