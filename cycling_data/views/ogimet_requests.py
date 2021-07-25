from pyramid.view import view_config
from .header import view_with_header

from ..models.cycling_models import SentRequestLog

class ogimet_views(object):

    def __init__(self, request):
        self.request = request

    @view_with_header
    @view_config(route_name='ogimet_requests', renderer='../templates/ogimet_rate_limiting_plot.jinja2')
    def ogimet_rate_limiting(self):

        import pandas as pd
        import numpy as np
        import plotly
        import json

        # Fetch the data
        request_log_query=self.request.dbsession.query(
            SentRequestLog
        ).with_entities(
            SentRequestLog.time,SentRequestLog.rate_limited)

        request_log=pd.read_sql_query(
            request_log_query.statement,request_log_query.session.bind)

        request_log=request_log.set_index('time')

        #windows=np.arange(np.timedelta64(5,'m'),np.timedelta64(125,'m'),np.timedelta64(5,'m'))
        windows=np.arange(5,1440,5)

        counts=np.zeros([len(windows),len(request_log)],dtype=int)
        rate_limited=np.zeros([len(windows),len(request_log)])
        offsets=np.zeros([len(windows),len(request_log)])

        if request_log.shape[0]>0:
            for i,window in enumerate(windows):

                offset='{}min'.format(int(window))
            
                offset_counts=request_log.rolling(offset).count()
                counts[i,:]=offset_counts['rate_limited']
                rate_limited[i,counts[i,:]-1]=request_log.rolling(offset).mean()['rate_limited']
                offsets[i,:]=window


        max_count=counts.max()
        rate_limited[:,:max_count]

        graphs=[
            {
                'data':[{
                    'x':np.arange(1,max_count+1),
                    'y':windows,
                    'z':rate_limited,
                    'type':'heatmap',
                }],
                'layout':{
                    'xaxis':{
                        'title':'Requests'
                    },
                    'yaxis':{
                        'title':'Window (minutes)'
                    },
                },
                'config':{'responsive':True},
                'showlegend':True
            }
        ]
        
        # Add "ids" to each of the graphs to pass up to the client
        # for templating
        ids = ['graph-{}'.format(i) for i, _ in enumerate(graphs)]

        # Convert the figures to JSON
        # PlotlyJSONEncoder appropriately converts pandas, datetime, etc
        # objects to their JSON equivalents
        graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)

        return {'graphJSON':graphJSON, 'ids':ids}
