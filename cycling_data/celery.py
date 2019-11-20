from celery import Celery
from celery.signals import worker_init


@worker_init.connect
def bootstrap_pyramid(signal, sender):
    import os
    from pyramid.paster import bootstrap
    sender.app.settings = bootstrap(os.environ['YOUR_CONFIG'])['registry'].settings


celery.config_from_object('celeryconfig')
