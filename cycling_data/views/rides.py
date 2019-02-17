from pyramid.view import view_config
import colander
import deform.widget

from ..models.cycling_models import Ride, Equipment, SurfaceType, RiderGroup

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

class RideForm(colander.MappingSchema):
        
    start_time=colander.SchemaNode(colander.DateTime())
    end_time=colander.SchemaNode(colander.DateTime())
    startloc=colander.SchemaNode(colander.String(),
        widget=get_location_widget)
    endloc=colander.SchemaNode(colander.String(),
        widget=get_location_widget)
    route=colander.SchemaNode(colander.String())
    rolling_time=colander.SchemaNode(colander.Time())
    total_time=colander.SchemaNode(colander.Time())
    distance=colander.SchemaNode(colander.Float())
    odometer=colander.SchemaNode(colander.Float())
    avspeed=colander.SchemaNode(colander.Float())
    maxpeed=colander.SchemaNode(colander.Float())
    trailer=colander.SchemaNode(colander.Boolean())
    equipment=colander.SchemaNode(
        colander.Integer(),
        default=get_default_equipment,
        widget=get_equipment_widget
    )
    surface=colander.SchemaNode(
        colander.Integer(),
        default=get_default_surface,
        widget=get_surface_widget
    )
    ridergroup=colander.SchemaNode(
        colander.Integer(),
        default=get_default_ridergroup,
        widget=get_ridergroup_widget
    )
    remarks=colander.SchemaNode(colander.String())

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
        rides=self.request.dbsession.query(Ride)
        return dict(rides=rides)

    @view_config(route_name='rides_add', renderer='../templates/rides_addedit.jinja2')
    def ride_add(self):
        form=self.ride_form.render()
        return dict(form=form)
