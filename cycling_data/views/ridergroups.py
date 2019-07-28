from pyramid.view import view_config
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound

from ..models.cycling_models import RiderGroup

from deform.renderer import configure_zpt_renderer

from .showtable import SqlalchemyOrmPage

class RiderGroupForm(colander.MappingSchema):

    name=colander.SchemaNode(colander.String())

class RiderGroupViews(object):
    def __init__(self, request):
        self.request = request

    @property
    def ridergroup_form(self):
        schema=RiderGroupForm().bind(
            request=self.request,
            )
        return deform.Form(schema,buttons=['submit'])

    @view_config(route_name='ridergroup_add', renderer='../templates/ridergroup_addedit.jinja2')
    def ridergroup_add(self):

        form=self.ridergroup_form.render()

        dbsession=self.request.dbsession

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.ridergroup_form.validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            dbsession.add(RiderGroup(
                name=appstruct['name'],
            ))

            url = self.request.route_url('ridergroups_table')
            return HTTPFound(url)

        return dict(form=form)
        
        

    @view_config(route_name='ridergroup_edit', renderer='../templates/ridergroup_addedit.jinja2')
    def ridergroup_edit(self):

        dbsession=self.request.dbsession
    
        ridergroup_id = int(self.request.matchdict['ridergroup_id'])
        ridergroup = dbsession.query(RiderGroup).filter_by(id=ridergroup_id).one()

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.ridergroup_form.validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            ridergroup.name=appstruct['name']
            url = self.request.route_url('ridergroups_table')
            return HTTPFound(url)

        form=self.ridergroup_form.render(dict(
            name=ridergroup.name or '',
        ))

        return dict(form=form)

    @view_config(route_name='ridergroups_table', renderer='../templates/ridergroup_table.jinja2')
    def ridergroups_table(self):

        current_page = int(self.request.params.get("page",1))
        ridergroups=self.request.dbsession.query(RiderGroup).order_by(RiderGroup.id.desc())
        page=SqlalchemyOrmPage(ridergroups,page=current_page,items_per_page=30)
        return dict(ridergroups=ridergroups,page=page)
