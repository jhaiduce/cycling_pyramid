from pyramid.view import view_config
import colander
import deform.widget

from ..models.cycling_models import Location, Ride

class LocationViews(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name='locations_autocomplete', renderer='json')
    def ride_table(self):
        term=self.request.GET['term']

        # Subquery to get the first ride of each location
        last_id = self.request.dbsession.query(Ride.id).filter(
            Ride.startloc_id==Location.id
                or Ride.endloc_id==Location.id
        ).order_by(Ride.start_time.desc()).limit(1).correlate(Location)

        # Query locations matching the term variable,
        # most recently used first
        locations=self.request.dbsession.query(Location).filter(
                Location.name.startswith(term)
            ).outerjoin(Ride, Ride.id == last_id
            ).order_by(Ride.start_time.desc()
            ).order_by(Location.id.desc()).limit(8)

        return [location.name for location in locations]

