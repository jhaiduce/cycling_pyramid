from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response

def ogimet_request(request):
    import requests
    resp=requests.get('https://ogimet.com/display_metars2.php',params=request.params)
    return Response(resp.text)

if __name__ == '__main__':
    with Configurator() as config:
        config.add_route('ogimet_request', '/')
        config.add_view(ogimet_request, route_name='ogimet_request')
        app = config.make_wsgi_app()
    server = make_server('0.0.0.0', 80, app)
    server.serve_forever()
