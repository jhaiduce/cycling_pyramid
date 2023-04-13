from pyramid.view import view_config
from .rides import appstruct_to_ride

class PredictionViews(object):

    @view_config(route_name='ride_prediction', renderer='../templates/ride_prediction.jinja2')
    def ride_prediction(self):
        pass
