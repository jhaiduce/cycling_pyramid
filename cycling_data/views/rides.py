from pyramid.view import view_config
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound
import json
from pyramid.response import Response

from .showtable import SqlalchemyOrmPage

from ..models.cycling_models import Ride, Equipment, SurfaceType, RiderGroup, Location, WeatherData, RideWeatherData, PredictionModelResult

import logging
log = logging.getLogger(__name__)

from .header import view_with_header

from datetime import timedelta

import colander.interfaces
from colander import null

class Duration(colander.interfaces.Type):

    def serialize(self,node,appstruct):
        if appstruct in (colander.null, None):
            return colander.null

        if not isinstance(appstruct,timedelta):
            raise colander.Invalid(
                node, 'Expected datetime.timedelta, not {val}.'.format(
                    val=type(appstruct).__name__)
            )
        return str(appstruct.total_seconds())

    def deserialize(self, node, cstruct):
        if cstruct != 0 and not cstruct:
            return colander.null

        try:
            return timedelta(seconds=int(cstruct))
        except Exception:
            raise colander.Invalid(
                node, '"{val}" is not a number'.format(val= cstruct)
            )

def submit_update_ride_weather_task(success,ride_id):

    from ..processing.weather import update_ride_weather
    update_ride_weather.delay(ride_id)

def time_to_timedelta(time):
    from datetime import datetime, date
    if time is None:
        return None
    return datetime.combine(date.min,time)-datetime.min

def timedelta_to_time(timedelta):
    from datetime import datetime, date

    return (datetime.min+timedelta).time()

@colander.deferred
def get_equipment_widget(node, kw):
    return deform.widget.SelectWidget(values=kw['equipment_choices'])

@colander.deferred
def get_surface_widget(node, kw):
    return deform.widget.SelectWidget(values=kw['surface_choices'])

@colander.deferred
def get_ridergroup_widget(node, kw):
    return deform.widget.SelectWidget(values=kw['ridergroup_choices'])

@colander.deferred
def get_default_equipment(node, kw):
    return 1

@colander.deferred
def get_default_surface(node, kw):
    return 1

@colander.deferred
def get_default_ridergroup(node, kw):
    return 1

@colander.deferred
def get_location_widget(node,kw):
    return deform.widget.AutocompleteInputWidget(
        min_length=1,
        values=kw['request'].route_path(
            'locations_autocomplete'
            )
        
    )

registry = deform.widget.ResourceRegistry()
registry.set_js_resources('boostrap-duration-picker', '2.1.3', 'boostrap-duration-picker.js')
registry.set_css_resources('bootstrap-duration-picker', '2.1.3', 'bootstrap-duration-picker.css')

class DurationWidget(deform.widget.Widget):
    template="cycling_data:templates/duration.pt"
    type_name="duration"
    requirements=(('bootstrap-duration-picker',None),)
    options=None

    def serialize(self, field, cstruct, **kw):
        if cstruct in (colander.null, None):
            cstruct = ""
        readonly = kw.get("readonly", self.readonly)
        options = kw.get("options", self.options)
        if options is None:
            options = {}
        options = json.dumps(dict(options))
        kw["duration_options"] = options
        values = self.get_template_values(field, cstruct, kw)
        template = readonly and self.readonly_template or self.template
        return field.renderer(template, **values)

    def deserialize(self, field, pstruct):
        if pstruct is colander.null:
            return colander.null
        elif not isinstance(pstruct, str):
            raise Invalid(field.schema, "Pstruct is not a string")
        pstruct = pstruct.strip()
        if not pstruct:
            return colander.null
        return pstruct

def get_datetime_widget():
    return deform.widget.TextInputWidget(mask='9999-99-99 99:99:99')

def get_timedelta_widget():
    return DurationWidget(options={'showSeconds':True})

class RideForm(colander.MappingSchema):
    id=colander.SchemaNode(colander.Integer(),
        widget=deform.widget.HiddenWidget(),missing=None)
    equipment=colander.SchemaNode(
        colander.Integer(),
        default=get_default_equipment,
        widget=get_equipment_widget,missing=None
    )
    start_time=colander.SchemaNode(colander.DateTime(),missing=None)
    end_time=colander.SchemaNode(colander.DateTime(),missing=None)
    startloc=colander.SchemaNode(colander.String(),
        widget=get_location_widget,missing=None)
    endloc=colander.SchemaNode(colander.String(),
        widget=get_location_widget,missing=None)
    route=colander.SchemaNode(colander.String(),missing=None)
    rolling_time=colander.SchemaNode(
        Duration(),
        widget=get_timedelta_widget(),missing=None)
    total_time=colander.SchemaNode(
        Duration(),
        widget=get_timedelta_widget(),missing=None)
    distance=colander.SchemaNode(colander.Float(),missing=None)
    odometer=colander.SchemaNode(colander.Float(),missing=None)
    avspeed=colander.SchemaNode(colander.Float(),missing=None)
    maxspeed=colander.SchemaNode(colander.Float(),missing=None)
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
    remarks=colander.SchemaNode(colander.String(),
        widget=deform.widget.TextAreaWidget(),missing=None)

def get_location_by_name(dbsession,name):

    from sqlalchemy.orm.exc import NoResultFound

    try:
        location=dbsession.query(Location).filter(
            Location.name==name).one()
    except NoResultFound:
        location=Location(name=name)
        dbsession.add(location)
    return location

def appstruct_to_ride(dbsession,appstruct,existing_ride=None):

    if existing_ride:
        ride=existing_ride
    else:
        ride=Ride()

    startloc=get_location_by_name(dbsession,appstruct['startloc'])
    endloc=get_location_by_name(dbsession,appstruct['endloc'])

    ride.startloc=startloc
    ride.endloc=endloc
    ride.distance=appstruct['distance']
    ride.odometer=appstruct['odometer']
    ride.rolling_time=appstruct['rolling_time']
    ride.total_time=appstruct['total_time']
    ride.start_time=appstruct['start_time']
    ride.end_time=appstruct['end_time']
    ride.avspeed=appstruct['avspeed']
    ride.maxspeed=appstruct['maxspeed']
    ride.trailer=appstruct['trailer']
    ride.equipment_id=appstruct['equipment']
    ride.ridergroup_id=appstruct['ridergroup']
    ride.surface_id=appstruct['surface']
    ride.route=appstruct['route']
    ride.remarks=appstruct['remarks']

    return ride

class RideViews(object):
    def __init__(self, request):
        self.request = request
        
    def ride_form(self,dbsession=None):
        if dbsession is None: dbsession=self.request.dbsession
        all_equipment = dbsession.query(Equipment)
        equipment_choices=[(equipment.id,equipment.name) for equipment in all_equipment]
        surfacetypes = dbsession.query(SurfaceType)
        surface_choices=[(surface.id,surface.name) for surface in surfacetypes]
        ridergroups = dbsession.query(RiderGroup)
        ridergroup_choices=[(ridergroup.id,ridergroup.name) for ridergroup in ridergroups]
        schema=RideForm().bind(
            request=self.request,
            equipment_choices=equipment_choices,
            surface_choices=surface_choices,
            ridergroup_choices=ridergroup_choices,
            )
        return deform.Form(schema,buttons=['submit'])

    @view_with_header
    @view_config(route_name='rides', renderer='../templates/ride_table.jinja2')
    def ride_table(self):

        current_page = int(self.request.params.get("page",1))
        rides=self.request.dbsession.query(Ride).order_by(Ride.start_time.desc())
        page=SqlalchemyOrmPage(rides,page=current_page,items_per_page=30)
        return dict(rides=rides,page=page)

    @view_with_header
    @view_config(route_name='rides_scatter', renderer='../templates/rides_scatter.jinja2')
    def rides_scatter(self):
    
        import plotly
        
        xvar=self.request.params.get('x','start_time')
        yvar=self.request.params.get('y','avspeed')

        self.request.dbsession.autoflush=False

        computed_vars=['avspeed_est']
        hybrid_properties=['grade','azimuth','tailwind','crosswind']

        predicted_vars=['avspeed','maxspeed','total_time']
        predicted_vars_with_suffix=[var+'_pred' for var in predicted_vars]
        
        # List of valid variable names
        valid_vars=Ride.__table__.columns.keys()+WeatherData.__table__.columns.keys()+RideWeatherData.__table__.columns.keys()+computed_vars+hybrid_properties+predicted_vars_with_suffix
        
        # Make sure xvar is a valid column name
        if xvar not in valid_vars:
            raise ValueError('Invalid field {0}'.format(xvar))
        
        # Make sure yvar is a valid column name
        if yvar not in valid_vars:
            raise ValueError('Invalid field {0}'.format(yvar))

        # Build list of columns to fetch
        fetch_entities=[Ride.id,Ride.distance,Ride.rolling_time,Ride.start_time,Ride.end_time,Ride.total_time]
        for var in xvar,yvar:
            if var in Ride.__table__.columns.keys() or var in hybrid_properties:
                fetch_entities.append(getattr(Ride,var))
            elif var in WeatherData.__table__.columns.keys():
                fetch_entities.append(getattr(WeatherData,var))
            elif var in RideWeatherData.__table__.columns.keys():
                fetch_entities.append(getattr(RideWeatherData,var))

        # Fetch the data
        ride_query=self.request.dbsession.query(Ride).join(Ride.wxdata,isouter=True)
        rides=ride_query.with_entities(*fetch_entities)

        # Convert data to pandas
        import pandas as pd
        import numpy as np

        from ..models.prediction import get_ride_predictions, prepare_model_dataset, get_model
        dbsession_factory = self.request.registry['dbsession_factory']
        df=pd.read_sql_query(rides.statement,rides.session.bind)

        if xvar in predicted_vars_with_suffix or yvar in predicted_vars_with_suffix:
            prediction_query=dbsession_factory().query(PredictionModelResult).with_entities(PredictionModelResult.ride_id,PredictionModelResult.avspeed,PredictionModelResult.maxspeed,PredictionModelResult.total_time)
            df_predictions=pd.read_sql_query(
                prediction_query.statement,
                prediction_query.session.bind
            )
            df_predictions=df_predictions.rename(columns={
                'avspeed':'avspeed_pred',
                'maxspeed':'maxspeed_pred',
                'total_time':'total_time_pred',
                'ride_id':'id',
            })

            df=df.merge(df_predictions,on='id')

        # Fill in missing average speeds
        if 'avspeed_est' in [xvar,yvar] or 'avspeed' in [xvar,yvar]:
            rolling_time_hours=df['rolling_time']/np.timedelta64(1,'h')
            df['avspeed_est']=pd.Series(df['distance']/rolling_time_hours,index=df.index)
        if 'avspeed' in list(df.columns)+[xvar,yvar]:
            df['avspeed']=df['avspeed'].fillna(df['avspeed_est'])

        # fill in missing total time
        computed_total_time=pd.to_timedelta((df.end_time-df.start_time).dt.total_seconds()/60)
        df.total_time.fillna(computed_total_time)

        for column in 'rolling_time', 'total_time':
            if column in df:
                df[column]=df[column].dt.total_seconds()/60

        # Get x and y data
        x=df[xvar]
        y=df[yvar]

        graphs=[
            {
                'data':[{
                    'x':x,
                    'y':y,
                    'type':'scatter',
                    'mode':'markers',
                    'marker':{
                        'size':4
                    }
                }],
                'layout':{
                    'xaxis':{
                        'title':xvar
                    },
                    'yaxis':{
                        'title':yvar
                    },
                },
                'config':{'responsive':True}
            }
        ]

        # Add "ids" to each of the graphs to pass up to the client
        # for templating
        ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]

        # Convert the figures to JSON
        # PlotlyJSONEncoder appropriately converts pandas, datetime, etc
        # objects to their JSON equivalents
        graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)

        return {'graphJSON':graphJSON, 'ids':ids}

    @view_config(route_name='rides_add', renderer='../templates/rides_addedit.jinja2')
    def ride_add(self):

        from ..models import get_tm_session
        import transaction

        tmp_tm = transaction.TransactionManager(explicit=True)
        with tmp_tm:
            dbsession_factory = self.request.registry['dbsession_factory']
            tmp_dbsession = get_tm_session(dbsession_factory, tmp_tm)
            form=self.ride_form(tmp_dbsession).render()

        if 'submit' in self.request.params:

            tmp_tm = transaction.TransactionManager(explicit=True)
            with tmp_tm:

                dbsession_factory = self.request.registry['dbsession_factory']
                tmp_dbsession = get_tm_session(dbsession_factory, tmp_tm)

                controls=self.request.POST.items()

                try:
                    appstruct=self.ride_form(tmp_dbsession).validate(controls)
                except deform.ValidationFailure as e:
                    return dict(form=e.render())

                ride=appstruct_to_ride(tmp_dbsession,appstruct)
                tmp_dbsession.add(ride)

                # Flush dbsession so ride gets an id assignment
                tmp_dbsession.flush()

                # Store ride id
                ride_id=ride.id

            log.info('Added ride {}'.format(ride_id))

            ride=self.request.dbsession.query(Ride).filter(Ride.id==ride_id).one()

            # Queue a task to update ride's weather data
            from ..processing.weather import update_ride_weather
            update_weather_task=update_ride_weather.delay(ride_id)

            url = self.request.route_url('rides')
            return HTTPFound(
                url,
                content_type='application/json',
                charset='',
                text=json.dumps(
                    {'ride_id':ride_id,
                     'update_weather_task_id':update_weather_task.task_id}))

        return dict(form=form)

    @view_with_header
    @view_config(route_name='ride_details', renderer='../templates/ride_details.jinja2')
    def ride_details(self):
        from ..models.prediction import get_ride_predictions

        ride_id=int(self.request.matchdict['ride_id'])

        dbsession=self.request.dbsession

        ride=dbsession.query(Ride).filter(Ride.id==ride_id).one()

        if ride.wxdata is None:
            ride.wxdata=RideWeatherData()

        try:
            predictions=get_ride_predictions(dbsession,[ride])
        except:
            predictions=None

        if predictions is not None:
            predicted_speed=predictions[0,0]
        else:
            predicted_speed=None

        return dict(ride=ride,wxdata=ride.wxdata,predicted_speed=predicted_speed)

    @view_config(route_name='rides_edit', renderer='../templates/rides_addedit.jinja2')
    def ride_edit(self):
        form=self.ride_form().render()

        dbsession=self.request.dbsession

        ride_id=int(self.request.matchdict['ride_id'])
        ride=dbsession.query(Ride).filter(Ride.id==ride_id).one()

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.ride_form().validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            ride=appstruct_to_ride(dbsession,appstruct,ride)
            
            dbsession.add(ride)

            from ..celery import after_commit_task_hook
            from ..processing.weather import update_ride_weather

            # add hook to submit update_ride_weather task after commit
            ride_id=ride.id
            self.request.tm.get().addAfterCommitHook(
                after_commit_task_hook(update_ride_weather,task_args=[ride.id]))

            url = self.request.route_url('rides')
            return HTTPFound(url)

        form=self.ride_form().render(dict(
            id=ride.id,
            startloc=ride.startloc.name if ride.startloc else '',
            endloc=ride.endloc.name if ride.endloc else '',
            distance=ride.distance,
            odometer=ride.odometer,
            rolling_time=ride.rolling_time,
            total_time=ride.total_time,
            start_time=ride.start_time,
            route=ride.route if ride.route else '',
            end_time=ride.end_time,
            avspeed=ride.avspeed,
            maxspeed=ride.maxspeed,
            trailer=ride.trailer,
            equipment=ride.equipment_id,
            surface=ride.surface_id,
            remarks=ride.remarks if ride.remarks else '',
            ridergroup=ride.ridergroup_id
        ))
        
        return dict(form=form)
    
    @view_config(route_name='last_odo', renderer='json')
    def last_odo(self):
        from datetime import datetime
        equipment_id=int(self.request.GET['equipment_id'])
        start_time=datetime.strptime(self.request.GET['start_time'],'%Y-%m-%d %H:%M:%S')
        
        ride=self.request.dbsession.query(Ride).filter(
            Ride.equipment_id==equipment_id,
            Ride.end_time<=start_time
        ).order_by(
            Ride.start_time.desc()).first()

        return dict(odometer=ride.odometer)

    def get_last_ride(self,equipment_id,start_time=None):
        
        last_ride_query=self.request.dbsession.query(Ride).filter(
            Ride.equipment_id==equipment_id
        )

        if start_time is not None:
            
            # Filter by start_time
            last_ride_query=last_ride_query.filter(
                Ride.end_time<=start_time
            )
        
        last_ride=last_ride_query.order_by(Ride.start_time.desc()).first()
        
        return last_ride

    @view_config(route_name='validate_ride_distance', renderer='json')
    def check_distance(self):
        from datetime import datetime

        equipment_id=int(self.request.POST['equipment_id'])
        
        try:
            start_time=datetime.strptime(self.request.POST['start_time'],'%Y-%m-%d %H:%M:%S')
        except ValueError:
            start_time=None

        try:
            odometer=float(self.request.POST['odometer'])
        except ValueError:
            return 'true'

        try:
            distance=float(self.request.POST['distance'])
        except ValueError:
            return 'true'

        last_ride=self.get_last_ride(equipment_id,start_time)

        if(abs(last_ride.odometer+distance-odometer)>0.1):
            return "Ride distance should be between {:0.1f} and {:0.1f} based on odometer entry".format(
                odometer-last_ride.odometer-0.1,
                odometer-last_ride.odometer+0.1
            )

        return 'true'

    
    @view_config(route_name='validate_ride_odometer', renderer='json')
    def check_odometer(self):
        from datetime import datetime
        try:
            equipment_id=int(self.request.POST['equipment_id'])
        except:
            return 'true'
        
        try:
            start_time=datetime.strptime(self.request.POST['start_time'],'%Y-%m-%d %H:%M:%S')
        except ValueError:
            start_time=None

        try:
            odometer=float(self.request.POST['odometer'])
        except:
            return 'true'

        try:
            distance=float(self.request.POST['distance'])
        except:
            return 'true'
            
        last_ride=self.get_last_ride(equipment_id,start_time)

        if(abs(last_ride.odometer+distance-odometer)>0.1):
            return "Odometer should be between {:0.1f} and {:0.1f}".format(
                last_ride.odometer+distance-0.1,
                last_ride.odometer+distance+0.1
            )

        return 'true'

    
