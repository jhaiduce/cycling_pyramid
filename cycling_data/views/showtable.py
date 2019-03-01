import paginate

class SqlalchemyOrmWrapper(object):
    """Wrapper class to access elements of a collection."""
    def __init__(self, obj):
        self.obj = obj

    def __getitem__(self, range):
        # Return a range of objects of an sqlalchemy.orm.query.Query object
        return self.obj[range]

    def __len__(self):
        # Count the number of objects in an sqlalchemy.orm.query.Query object
        return self.obj.count()

class SqlalchemyOrmPage(paginate.Page):
    """A pagination page that deals with SQLAlchemy ORM objects."""
    def __init__(self, *args, **kwargs):
        super(SqlalchemyOrmPage, self).__init__(*args, wrapper_class=SqlalchemyOrmWrapper, **kwargs)

