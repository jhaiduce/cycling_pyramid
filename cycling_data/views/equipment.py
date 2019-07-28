from pyramid.view import view_config
import colander
import deform.widget
from pyramid.httpexceptions import HTTPFound

from ..models.cycling_models import Equipment

from deform.renderer import configure_zpt_renderer

from .showtable import SqlalchemyOrmPage

class EquipmentForm(colander.MappingSchema):

    name=colander.SchemaNode(colander.String())

class EquipmentViews(object):
    def __init__(self, request):
        self.request = request

    @property
    def equipment_form(self):
        schema=EquipmentForm().bind(
            request=self.request,
            )
        return deform.Form(schema,buttons=['submit'])

    @view_config(route_name='equipment_add', renderer='../templates/equipment_addedit.jinja2')
    def equipment_add(self):

        form=self.equipment_form.render()

        dbsession=self.request.dbsession

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.equipment_form.validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            dbsession.add(Equipment(
                name=appstruct['name'],
            ))

            url = self.request.route_url('equipment_table')
            return HTTPFound(url)

        return dict(form=form)
        
        

    @view_config(route_name='equipment_edit', renderer='../templates/equipment_addedit.jinja2')
    def equipment_edit(self):

        dbsession=self.request.dbsession
    
        equipment_id = int(self.request.matchdict['equipment_id'])
        equipment = dbsession.query(Equipment).filter_by(id=equipment_id).one()

        if 'submit' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.equipment_form.validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            equipment.name=appstruct['name']
            url = self.request.route_url('equipment_table')
            return HTTPFound(url)

        form=self.equipment_form.render(dict(
            name=equipment.name or '',
        ))

        return dict(form=form)

    @view_config(route_name='equipment_table', renderer='../templates/equipment_table.jinja2')
    def equipment_table(self):

        current_page = int(self.request.params.get("page",1))
        equipment=self.request.dbsession.query(Equipment).order_by(Equipment.id.desc())
        page=SqlalchemyOrmPage(equipment,page=current_page,items_per_page=30)
        return dict(equipment=equipment,page=page)
