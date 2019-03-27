from pyramid.security import Allow, Everyone, Authenticated

class Root(object):
    __acl__ = [(Allow, Authenticated, 'view')]

    def __init__(self,request):
        pass
