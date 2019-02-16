from pyramid.view import view_config
import colander
import deform.widget

from ..models.cycling_models import Location

class LocationViews(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name='locations_autocomplete', renderer='json')
    def ride_table(self):
        term=self.request.GET['term']
        locations=self.request.dbsession.query(Location).filter(
            Location.name.startswith(term))
        return [location.name for location in locations]

