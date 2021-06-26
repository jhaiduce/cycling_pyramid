from pyramid.view import view_config
from .header import view_with_header

class weather_views(object):

    def __init__(self, request):
        self.request = request

    @view_config(route_name='fill_missing_weather',renderer='json')
    def fill_missing_weather(self):

        """
        Queue a task to fill missing weather data
        """

        from ..processing.weather import fill_missing_weather
        fill_missing_weather_task=fill_missing_weather.delay()

        return {'fill_missing_weather_task_id':fill_missing_weather_task.task_id}
