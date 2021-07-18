from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from celery.utils.log import get_task_logger
from . import models
import configparser

logger = get_task_logger(__name__)

engine=None
settings=None

config=configparser.ConfigParser()
config.read('/run/secrets/production.ini')

class after_commit_task_hook(object):

    def __init__(self,task,run_on_failure=False,run_on_success=True,task_args=[],task_kwargs={}):
        self.task=task
        self.run_on_failure=run_on_failure
        self.run_on_success=run_on_success
        self.task_args=task_args
        self.task_kwargs=task_kwargs

    def __call__(self,success):
        if (success and self.run_on_success) \
           or (not success and self.run_on_failure):
            self.task.delay(*self.task_args,**self.task_kwargs)

@worker_process_init.connect
def bootstrap_pyramid(signal, sender, **kwargs):

    global engine
    
    import os
    from pyramid.paster import bootstrap
    from sqlalchemy.pool import StaticPool

    try:
        global settings, env
        env = bootstrap('/run/secrets/production.ini')
        settings = env['registry'].settings
    except FileNotFoundError:
        import warnings
        warnings.warn('Settings file does not exist. Not configuring database session factory.')
        return

    settings['sqlalchemy.poolclass']=StaticPool

    engine=models.get_engine(settings,prefix='worker_sqlalchemy.')
    
    while True:

        # Here we try to connect to database server until connection succeeds.
        # This is needed because the database server may take longer
        # to start than the application
        
        import sqlalchemy.exc

        try:
            print("Checking database connection")
            conn=engine.connect()
            conn.execute("select 'OK'")

        except sqlalchemy.exc.OperationalError as e:
            import time
            print(e)
            print("Connection failed. Sleeping.")
            time.sleep(2)
            continue
        
        # If we get to this line, connection has succeeded so we break
        # out of the loop
        conn.close()
        break
    
def session_factory():
    from sqlalchemy.orm import Session
    from zope.sqlalchemy import ZopeTransactionExtension

    global engine

    session=Session(engine, extension=ZopeTransactionExtension())

    return session

def create_app():
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

    return celery

celery=create_app()
