from pyramid.config import Configurator


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    with Configurator(settings=settings,
                      root_factory='.resources.Root') as config:
        config.include('.models')
        config.include('pyramid_jinja2')
        config.include('.routes')
        config.include('.security')
        config.scan(ignore=['.tests','.migration_tests'])
        config.set_default_permission('view')

    return config.make_wsgi_app()
