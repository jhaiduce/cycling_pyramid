def includeme(config):
    config.add_static_view('deform_static', 'deform:static/')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home', '/')
    config.add_route('rides', '/rides')
    config.add_route('rides_add', '/rides/add')
    config.add_route('locations_autocomplete', '/locations/autocomplete')
