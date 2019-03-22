from pyramid.view import view_config
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response

from .showtable import SqlalchemyOrmPage

from ..models.cycling_models import Ride, Equipment, SurfaceType, RiderGroup, Location

def time_to_timedelta(time):
    from datetime import datetime, date
    if time is None:
        return None
    return datetime.combine(date.min,time)-datetime.min

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
    return 0

@colander.deferred
def get_default_surface(node, kw):
    return 0

@colander.deferred
def get_default_ridergroup(node, kw):
    return 0

@colander.deferred
def get_location_widget(node,kw):
    return deform.widget.AutocompleteInputWidget(
        min_length=1,
        values=kw['request'].route_path(
            'locations_autocomplete'
            )
        
    )

def get_datetime_widget():
    return deform.widget.TextInputWidget(mask='9999-99-99 99:99:99')

def get_timedelta_widget():
    return deform.widget.TextInputWidget(mask='99:99:99')

class RideForm(colander.MappingSchema):
        
    start_time=colander.SchemaNode(colander.DateTime(),
        widget=get_datetime_widget(),missing=None)
    end_time=colander.SchemaNode(colander.DateTime(),
        widget=get_datetime_widget(),missing=None)
    startloc=colander.SchemaNode(colander.String(),
        widget=get_location_widget,missing=None)
    endloc=colander.SchemaNode(colander.String(),
        widget=get_location_widget,missing=None)
    route=colander.SchemaNode(colander.String(),missing=None)
    rolling_time=colander.SchemaNode(colander.Time(),
        widget=get_timedelta_widget(),missing=None)
    total_time=colander.SchemaNode(colander.Time(),
        widget=get_timedelta_widget(),missing=None)
    distance=colander.SchemaNode(colander.Float(),missing=None)
    odometer=colander.SchemaNode(colander.Float(),missing=None)
    avspeed=colander.SchemaNode(colander.Float(),missing=None)
    maxspeed=colander.SchemaNode(colander.Float(),missing=None)
    trailer=colander.SchemaNode(colander.Boolean(),missing=None)
    equipment=colander.SchemaNode(
        colander.Integer(),
        default=get_default_equipment,
        widget=get_equipment_widget,missing=None
    )
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

class RideViews(object):
    def __init__(self, request):
        self.request = request
        
    @property
    def ride_form(self):
        all_equipment = self.request.dbsession.query(Equipment)
        equipment_choices=[(equipment.id,equipment.name) for equipment in all_equipment]
        surfacetypes = self.request.dbsession.query(SurfaceType)
        surface_choices=[(surface.id,surface.name) for surface in surfacetypes]
        ridergroups = self.request.dbsession.query(RiderGroup)
        ridergroup_choices=[(ridergroup.id,ridergroup.name) for ridergroup in ridergroups]
        schema=RideForm().bind(
            request=self.request,
            equipment_choices=equipment_choices,
            surface_choices=surface_choices,
            ridergroup_choices=ridergroup_choices,
            )
        return deform.Form(schema,buttons=['submit'])

    @view_config(route_name='rides', renderer='../templates/ride_table.jinja2')
    def ride_table(self):

        current_page = int(self.request.params.get("page",1))
        rides=self.request.dbsession.query(Ride).order_by(Ride.start_time.desc())
        page=SqlalchemyOrmPage(rides,page=current_page,items_per_page=30)
        return dict(rides=rides,page=page)

    @view_config(route_name='rides_scatter', renderer='../templates/rides_scatter.jinja2')
    def rides_scatter(self):
    
        from bokeh.plotting import figure
        from bokeh.embed import components
        
        xvar=self.request.params.get('x','start_time')
        yvar=self.request.params.get('y','avspeed')
        
        from sqlalchemy import inspect
        mapper=inspect(Ride)
        
        computed_vars=['avspeed_est']
        
        # List of valid variable names
        valid_vars=Ride.__table__.columns.keys()+computed_vars
        
        # Make sure xvar is a valid column name
        if xvar not in valid_vars:
            raise ValueError('Invalid field {0}'.format(xvar))
        
        # Make sure yvar is a valid column name
        if yvar not in valid_vars:
            raise ValueError('Invalid field {0}'.format(yvar))

        # Build list of columns to fetch
        fetch_entities=[Ride.distance,Ride.rolling_time]
        for var in xvar,yvar:
            if var in Ride.__table__.columns.keys():
                fetch_entities.append(getattr(Ride,var))

        # Fetch the data
        rides=self.request.dbsession.query(Ride).with_entities(*fetch_entities)
        
        # Convert data to pandas
        import pandas as pd
        import numpy as np
        df=pd.read_sql_query(rides.statement,rides.session.bind)
        
        # Fill in missing average speeds
        if 'avspeed_est' in [xvar,yvar] or 'avspeed' in [xvar,yvar]:
            rolling_time_hours=df['rolling_time']/np.timedelta64(1,'h')
            df['avspeed_est']=pd.Series(df['distance']/rolling_time_hours,index=df.index)
        if 'avspeed' in list(df.columns)+[xvar,yvar]:
            df['avspeed'].fillna(df['avspeed_est'])

        for column in 'rolling_time', 'total_time':
            if column in df:
                df[column]=df[column].dt.total_seconds()/60

        # Get x and y data
        x=df[xvar]
        y=df[yvar]

        bokeh_kwargs={}
        if xvar in ('start_time','end_time'):
            bokeh_kwargs['x_axis_type']='datetime'
        if yvar in ('start_time','end_time'):
            bokeh_kwargs['y_axis_type']='datetime'
            
        plot=figure(**bokeh_kwargs)
        
        plot.circle(x,y)
        
        bokeh_script,bokeh_div=components(plot)
        
        return dict(bokeh_script=bokeh_script,bokeh_div=bokeh_div)
        
        

    @view_config(route_name='rides_add', renderer='../templates/rides_addedit.jinja2')
    def ride_add(self):
        form=self.ride_form.render()

        dbsession=self.request.dbsession

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.ride_form.validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            startloc=get_location_by_name(dbsession,appstruct['startloc'])
            endloc=get_location_by_name(dbsession,appstruct['endloc'])

            dbsession.add(Ride(
                startloc=startloc,
                endloc=endloc,
                distance=appstruct['distance'],
                odometer=appstruct['odometer'],
                rolling_time=time_to_timedelta(appstruct['rolling_time']),
                total_time=time_to_timedelta(appstruct['total_time']),
                start_time=appstruct['start_time'],
                end_time=appstruct['end_time'],
                avspeed=appstruct['avspeed'],
                maxspeed=appstruct['maxspeed'],
                trailer=appstruct['trailer'],
                equipment_id=appstruct['equipment'],
                ridergroup_id=appstruct['ridergroup'],
                surface_id=appstruct['surface']
            ))


            url = self.request.route_url('rides')
            return HTTPFound(url)

        return dict(form=form)

    @view_config(route_name='last_odo', renderer='json')
    def last_odo(self):
        equipment_id=int(self.request.GET['equipment_id'])
        
        ride=self.request.dbsession.query(Ride).filter(
            Ride.equipment_id==equipment_id).order_by(
            Ride.start_time.desc()).first()

        return dict(odometer=ride.odometer)

