from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown
from celery.utils.log import get_task_logger
from . import models
import configparser

logger = get_task_logger(__name__)

session_factory=None

config=configparser.ConfigParser()
config.read('/run/secrets/production.ini')

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
            conn.close()
            time.sleep(2)
            continue
        
        # If we get to this line, connection has succeeded so we break
        # out of the loop
        conn.close()
        break
    
    session_factory=models.get_session_factory(engine)

celery=Celery(backend=config['celery']['backend_url'], broker=config['celery']['broker_url'])
celery.config_from_object('cycling_data.celeryconfig')
