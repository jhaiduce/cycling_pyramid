from wsgiref.simple_server import make_server
from pyramid.config import Configurator
from pyramid.response import Response
import os
import json
import logging
log = logging.getLogger(__name__)

class ogimet_proxy(object):

    cache_file='/app/ogimet-cache/ogimet-cache.json'

    def __init__(self):
        self.cache={}
        if os.path.isfile('ogimet-cache.json'):
            with open(self.cache_file,'r') as fh:
                stored_cache=json.load(fh)

                for item in stored_cache:
                    self.cache[frozenset(item['params'].items())]=item.text

    def write_cache(self):
        with open(self.cache_file,'w') as fh:
            stored_cache=[{'params':dict(params),'text':text}
                          for params,text in self.cache.items()]
            json.dump(stored_cache,fh,indent=4)

    def ogimet_request(self,request):
        import requests

        log.info('Cache contents: {}'.format(self.cache))

        try:
            text=self.cache[frozenset(request.params.items())]
        except KeyError:
            log.info('Fetching OGIMET data for {}'.format(request.params))
            text=requests.get('https://ogimet.com/display_metars2.php',params=request.params).text
            if 'METAR' in text:
                self.cache[frozenset(request.params.items())]=text
                self.write_cache()
        return Response(text)

if __name__ == '__main__':
    with Configurator() as config:
        config.add_route('ogimet_request', '/')
        proxy=ogimet_proxy()
        config.add_view(proxy.ogimet_request, route_name='ogimet_request')
        app = config.make_wsgi_app()
    server = make_server('0.0.0.0', 80, app)
    server.serve_forever()
