from ..models import User

def view_with_header(view_callable):

    def wrapper(context):

        # Run view callable
        data=view_callable(context)

        request=context.request

        # Turn on the header
        data['show_header']=True

        if request.authenticated_userid is not None:
            # Get the user information
            user=request.dbsession.query(User).filter(
                User.id==request.authenticated_userid).one()
            data['username']=user.name
            data['userid']=user.id
            data['request_url']=request.url

        return data

    return wrapper
