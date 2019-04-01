from pyramid.view import view_config
import colander
import deform.widget
import deform
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.response import Response

from .showtable import SqlalchemyOrmPage

from ..models import cycling_models, security

cycling_classes=['Ride', 'Location', 'LocationType', 'Equipment', 'SurfaceType', 'Riders', 'RiderGroup', 'WeatherData', 'RideWeatherData', 'StationWeatherData']
security_classes=['User']

def dump_backup(session):
    from sqlalchemy.ext.serializer import dumps

    dumpdata={}

    for module, classes in [
            (cycling_models,cycling_classes),
            (security,security_classes)]:
        
        for class_name in classes:
            
            # Get the class
            cls=getattr(module,class_name)

            # Get the marshmallow schema for this class
            cls_marshmallow_schema=getattr(cls,'__marshmallow__')()
            
            # Query all instances
            query=session.query(cls)

            # Serialize
            serialized=[cls_marshmallow_schema.dump(instance).data
                        for instance in query]

            dumpdata[class_name]=serialized

    return dumpdata

def load_backup(backup):
    from sqlalchemy.ext.serializer import loads
    from ..models.meta import metadata

    loaded_data={}

    for module, classes in [
            (cycling_models,cycling_classes),
            (security,security_classes)]:
        
        for class_name in classes:
            if class_name not in backup.keys(): continue

            # Get the class
            cls=getattr(module,class_name)

            # Get the marshmallow schema for this class
            cls_marshmallow_schema=getattr(cls,'__marshmallow__')()

            objlist=loaded_data.get(class_name,[])
            for serialized_dict in backup[class_name]:
                obj=cls_marshmallow_schema.load(serialized_dict).data
                objlist.append(obj)
                
            loaded_data[class_name]=objlist

    return loaded_data

class MemoryTmpStore(dict):
        """ Instances of this class implement the
        :class:`deform.interfaces.FileUploadTempStore` interface"""

        def preview_url(self, uid):
            return None

tmpstore=MemoryTmpStore()

class RestoreUploadFormSchema(colander.MappingSchema):
    file = colander.SchemaNode(
        deform.FileData(),
        widget=deform.widget.FileUploadWidget(tmpstore),
        title='Backup data to restore'
    )

class SaveRestoreViews(object):
    
    def __init__(self, request):
        self.request = request

    @view_config(route_name='backup', renderer='json')
    def backup(self):
        
        return dump_backup(self.request.dbsession)

    @property
    def restore_form(self):
        schema=RestoreUploadFormSchema().bind(
            request=self.request,
            )
        return deform.Form(schema,buttons=['Restore'])

    @view_config(route_name='restore',renderer='../templates/restore.jinja2')
    def restore(self):
        
        form=self.restore_form.render()

        dbsession=self.request.dbsession

        if 'Restore' in self.request.params:
            controls=self.request.POST.items()
            try:
                appstruct=self.restore_form.validate(controls)
            except deform.ValidationFailure as e:
                return dict(form=e.render())

            input_file=appstruct['file']

            loaded_data=load_backup(input_file)

            for class_name in loaded_data.keys():
                self.assertEqual(len(backup[class_name]),
                                 len(loaded_data[class_name]))

                for instance in loaded_data[class_name]:
                    self.session.merge(instance)

            url = self.request.route_url('home')
            return HTTPFound(url)

                    
        return dict(form=form)
