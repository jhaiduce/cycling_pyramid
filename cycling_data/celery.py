from celery import Celery
from celery.signals import worker_init

@worker_init.connect
def bootstrap_pyramid(signal, sender, **kwargs):
    import os
    from pyramid.paster import bootstrap
    sender.app.settings = bootstrap(os.environ['YOUR_CONFIG'])['registry'].settings

celery=Celery(backend='rpc://cycling_stack_rabbitmq', broker='pyamqp://guest@cycling_stack_rabbitmq')
celery.config_from_object('cycling_data.celeryconfig')
