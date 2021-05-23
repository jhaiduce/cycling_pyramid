def includeme(config):
    config.add_static_view('deform_static', 'deform:static/')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view(name='jquery-validate',path='cycling_data:node_modules/jquery-validation/dist')
    config.add_static_view(name='bootstrap-duration-picker',path='cycling_data:node_modules/bootstrap-duration-picker/dist')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('home', '/')
    config.add_route('backup', '/backup')
    config.add_route('restore', '/restore')
    config.add_route('rides', '/rides')
    config.add_route('rides_add', '/rides/add')
    config.add_route('rides_edit', '/rides/{ride_id}/edit')
    config.add_route('rides_scatter', '/rides/scatter')
    config.add_route('ride_details', '/rides/{ride_id}/details')
    config.add_route('last_odo', '/rides/last_odo')
    config.add_route('validate_ride_distance', '/rides/validation/distance')
    config.add_route('validate_ride_odometer', '/rides/validation/odometer')
    config.add_route('locations_autocomplete', '/locations/autocomplete')
    config.add_route('location_add', '/locations/add')
    config.add_route('location_edit','/locations/{location_id}/edit')
    config.add_route('locations_table','/locations/list')
    config.add_route('ridergroup_add', '/ridergroups/add')
    config.add_route('ridergroup_edit','/ridergroups/{ridergroup_id}/edit')
    config.add_route('ridergroups_table','/ridergroups/list')
    config.add_route('equipment_add', '/equipment/add')
    config.add_route('equipment_edit','/equipment/{equipment_id}/edit')
    config.add_route('equipment_table','/equipment/list')
    config.add_route('ogimet_requests','/ogimet_rate_limiting')
