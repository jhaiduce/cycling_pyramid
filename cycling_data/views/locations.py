from pyramid.view import view_config
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound

from ..models.cycling_models import Location, Ride, LocationType

@colander.deferred
def get_loctype_widget(node, kw):

    loctypes = kw['request'].dbsession.query(
        LocationType).order_by(LocationType.id)
    choices=[(loctype.id,loctype.name) for loctype in loctypes]
    return deform.widget.SelectWidget(values=choices)

class LocationCoordinatesMapping(colander.MappingSchema):

    lat=colander.SchemaNode(colander.Float())
    lon=colander.SchemaNode(colander.Float())
    elevation=colander.SchemaNode(colander.Float())

class LocationForm(colander.MappingSchema):

    name=colander.SchemaNode(colander.String())
    coordinates=LocationCoordinatesMapping()
    description=colander.SchemaNode(colander.String(),missing=None)
    remarks=colander.SchemaNode(colander.String(),missing=None)
    loctype=colander.SchemaNode(
        colander.Integer(),default=1,widget=get_loctype_widget
        )

class LocationViews(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name='locations_autocomplete', renderer='json')
    def locations_autocomplete(self):
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

    @property
    def location_form(self):
        schema=LocationForm().bind(
            request=self.request,
            )
        return deform.Form(schema,buttons=['submit'])

    @view_config(route_name='location_add', renderer='../templates/location_addedit.jinja2')
    def location_add(self):

        form=self.location_form.render()

        dbsession=self.request.dbsession

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.location_form.validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            dbsession.add(Location(
                name=appstruct['name'],
                lat=appstruct['coordinates']['lat'],
                lon=appstruct['coordinates']['lon'],
                elevation=appstruct['coordinates']['elevation'],
                description=appstruct['description'],
                remarks=appstruct['remarks'],
                loctype_id=appstruct['loctype']
            ))


            url = self.request.route_url('rides')
            return HTTPFound(url)

        return dict(form=form)
