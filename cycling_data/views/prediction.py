from pyramid.view import view_config
from .rides import get_equipment_widget, get_surface_widget, get_ridergroup_widget, get_default_equipment, get_default_surface, get_default_ridergroup, get_location_widget, get_location_by_name
from ..models.cycling_models import Ride, Equipment, SurfaceType, RiderGroup, Location, WeatherData, RideWeatherData, PredictionModelResult
from sqlalchemy.sql import func
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound
from .header import view_with_header
from ..models.prediction import get_ride_predictions

class RidePredictionForm(colander.MappingSchema):
    equipment=colander.SchemaNode(
        colander.Integer(),
        default=get_default_equipment,
        widget=get_equipment_widget,missing=None
    )
    start_time=colander.SchemaNode(colander.DateTime(),missing=None)
    startloc=colander.SchemaNode(colander.String(),
                                 title='Start location',
                                 widget=get_location_widget,missing=None)
    endloc=colander.SchemaNode(colander.String(),
                               title='End location',
                               widget=get_location_widget,missing=None)
    distance=colander.SchemaNode(colander.Float(),missing=None)
    trailer=colander.SchemaNode(colander.Boolean(),missing=None)
    surface=colander.SchemaNode(
        colander.Integer(),
        default=get_default_surface,
        widget=get_surface_widget,missing=None
    )
    ridergroup=colander.SchemaNode(
        colander.Integer(),
        default=get_default_ridergroup,
        widget=get_ridergroup_widget,missing=None
    )

    windspeed=colander.SchemaNode(colander.Float(),title='Wind speed',missing=None)
    winddir=colander.SchemaNode(colander.Float(),title='Wind direction',missing=None)
    temperature=colander.SchemaNode(colander.Float(),missing=None)
    dewpoint=colander.SchemaNode(colander.Float(),missing=None)
    pressure=colander.SchemaNode(colander.Float(),missing=None)
    rain=colander.SchemaNode(colander.Float(),missing=None)
    snow=colander.SchemaNode(colander.Float(),missing=None)

def appstruct_to_ride(dbsession,appstruct):

    startloc=get_location_by_name(dbsession,appstruct['startloc'])
    endloc=get_location_by_name(dbsession,appstruct['endloc'])

    ride=Ride()

    ride.startloc=startloc
    ride.endloc=endloc
    if 'distance' in appstruct:
        ride.distance=appstruct['distance']
    else:
        ride.distance=dbsession.query(
            func.average(Ride.distance).label('average_distance')
        ).filter(Ride.startloc==startloc,Ride.endloc==endloc).scalar()
    ride.start_time=appstruct['start_time']
    ride.trailer=appstruct['trailer']
    ride.equipment=dbsession.query(Equipment).filter(Equipment.id==appstruct['equipment']).one()
    ride.ridergroup=dbsession.query(RiderGroup).filter(RiderGroup.id==appstruct['ridergroup']).one()
    ride.surface=dbsession.query(SurfaceType).filter(SurfaceType.id==appstruct['surface']).one()

    ride.wxdata=RideWeatherData()
    ride.wxdata.windspeed=appstruct['windspeed']
    ride.wxdata.winddir=appstruct['winddir']
    ride.wxdata.temperature=appstruct['temperature']
    ride.wxdata.dewpoint=appstruct['dewpoint']
    ride.wxdata.pressure=appstruct['pressure']
    ride.wxdata.rain=appstruct['rain']
    ride.wxdata.snow=appstruct['snow']

    return ride

class PredictionViews(object):

    def __init__(self, request):
        self.request = request

    def predict_form(self,dbsession=None):
        if dbsession is None: dbsession=self.request.dbsession

        all_equipment = dbsession.query(Equipment)
        equipment_choices=[(equipment.id,equipment.name) for equipment in all_equipment]
        surfacetypes = dbsession.query(SurfaceType)
        surface_choices=[(surface.id,surface.name) for surface in surfacetypes]
        ridergroups = dbsession.query(RiderGroup)
        ridergroup_choices=[(ridergroup.id,ridergroup.name) for ridergroup in ridergroups]
        schema=RidePredictionForm().bind(
            request=self.request,
            equipment_choices=equipment_choices,
            surface_choices=surface_choices,
            ridergroup_choices=ridergroup_choices,
            )
        return deform.Form(schema,buttons=['submit'])


    @view_config(route_name='ride_prediction', renderer='../templates/ride_prediction.jinja2')
    def ride_prediction(self):
        from ..models import get_tm_session
        import transaction

        tmp_tm = transaction.TransactionManager(explicit=True)
        with tmp_tm:
            dbsession_factory = self.request.registry['dbsession_factory']
            tmp_dbsession = get_tm_session(dbsession_factory, tmp_tm)
            form=self.predict_form(tmp_dbsession).render()

        if 'submit' in self.request.params:

            tmp_tm = transaction.TransactionManager(explicit=True)
            with tmp_tm:

                dbsession_factory = self.request.registry['dbsession_factory']
                tmp_dbsession = get_tm_session(dbsession_factory, tmp_tm)

                controls=self.request.POST.items()

                try:
                    appstruct=self.predict_form(tmp_dbsession).validate(controls)
                except deform.ValidationFailure as e:
                    return dict(form=e.render())

                ride=appstruct_to_ride(tmp_dbsession, appstruct)

            url = self.request.route_url('ride_prediction_result',_query=self.request.POST)
            return HTTPFound(url)

        return dict(form=form)

    @view_with_header
    @view_config(route_name='ride_prediction_result', renderer='../templates/ride_details.jinja2')
    def ride_prediction_result(self):
        from datetime import datetime, timedelta

        dbsession=self.request.dbsession

        appstruct=self.predict_form(dbsession).validate(self.request.GET.items())
        ride=appstruct_to_ride(dbsession,appstruct)

        for var in 'avspeed','maxspeed','total_time':
            try:
                var_predictions=get_ride_predictions(dbsession,[ride],var)
            except:
                var_predictions=None

            if var_predictions is not None:
                prediction=var_predictions[0,0]
            else:
                prediction=None

            setattr(ride,var,prediction)

        if ride.total_time is not None:
            ride.total_time=timedelta(minutes=ride.total_time)
        if ride.avspeed:
            ride.rolling_time=timedelta(hours=ride.distance/ride.avspeed)

        return {'ride':ride, 'wxdata':ride.wxdata,'predicted_speed':ride.avspeed}
