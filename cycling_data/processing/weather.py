from ..models.cycling_models import Ride, WeatherData, StationWeatherData, RideWeatherData, Location
from metar import Metar
from datetime import datetime, timedelta

from ..celery import celery

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

import transaction

import requests

def fetch_metars(station,dtstart,dtend,url='https://www.ogimet.com/cgi-bin/getmetar'):
    
    params={
        'lang':'en',
        'icao':station,
        'begin':dtstart.strftime('%Y%m%d%H%M%S'),
        'end':dtend.strftime('%Y%m%d%H%M%S'),
    }

    r=requests.get(url,params=params)

    r.raise_for_status()

    return r.text

def download_metars(station,dtstart,dtend):
    
    logger.info('Downloading METARS for {}, {} - {}'.format(station,dtstart,dtend))

    metar_text=fetch_metars(station,dtstart,dtend)

    lines=metar_text.splitlines()

    metars=[]
    for line in lines:
        try:
            tokens=line.split(',')
            if len(tokens)==0: continue
            if len(tokens)<7:
                logger.warning('Unexpected line format: {}'.format(line))
                continue
            metar_code=tokens[6]
            year=int(tokens[1])
            month=int(tokens[2])
            metar=Metar.Metar(metar_code,
                              year=year,
                              month=month,utcdelta=0)
            if metar.time is None:
                print('METAR time invalid')
                print(match)
                continue
            metars.append(metar)
        except Metar.ParserError as e:
            print(line)
            print(e)

    metars=sorted(metars,key=lambda m: m.time)
    
    return metars

def get_metars(session,station,dtstart,dtend,window_expansion=timedelta(seconds=3600*4)):

    from pytz import utc

    logger.debug('Getting METARS from range {} - {}'.format(dtstart,dtend))

    stored_metars=session.query(StationWeatherData).filter(
        StationWeatherData.station==station
    ).filter(
        StationWeatherData.report_time>dtstart-window_expansion
    ).filter(
        StationWeatherData.report_time<dtend+window_expansion
    ).order_by(StationWeatherData.report_time).all()

    if len(stored_metars)>0:
        logger.debug('Stored METARS span range {} - {}'.format(stored_metars[0].report_time,stored_metars[-1].report_time))

        data_spans_interval=stored_metars[0].report_time.replace(tzinfo=utc)<dtstart and stored_metars[-1].report_time.replace(tzinfo=utc)>dtend
    else:
        logger.debug('No stored METARS found')
        data_spans_interval=False

    if not data_spans_interval:
        fetched_metars=download_metars(station.name,dtstart-window_expansion,dtend+window_expansion)

        stored_metars=[]

        for metar in fetched_metars:
            wxdata=StationWeatherData(session,metar)

            q=session.query(StationWeatherData).filter(
                StationWeatherData.station==wxdata.station
            ).filter(
                StationWeatherData.report_time==wxdata.report_time
            ).filter(
                StationWeatherData.metar==wxdata.metar
            )

            if q.count()>=1:
                wxdata=q.first()
            else:
                session.add(wxdata)
            stored_metars.append(wxdata)

    return stored_metars

def fetch_metars_for_ride(session,ride):
    from .locations import get_nearby_locations
    lat_mid=(ride.startloc.lat+ride.endloc.lat)*0.5
    lon_mid=(ride.startloc.lon+ride.endloc.lon)*0.5
    nearby_stations=get_nearby_locations(session,lat_mid,lon_mid).filter(Location.loctype_id==2).limit(10)

    dtstart,dtend=ride_times_utc(ride)

    for station in nearby_stations:
        
        metars=get_metars(session,station,dtstart,dtend)
        
        if len(metars)>0:
            return metars
        
    return []

def weather_to_numeric(weathers):
    totalrain=0
    totalsnow=0
    for weather in weathers:
        rain=0
        if weather[2]=='BR':rain+=0.1
        elif weather[2]=='DZ':rain+=0.3
        elif weather[2]=='RA':rain+=0.3
        
        if rain>0:
            if weather[0]=='+': rain+=0.1
            if weather[0]=='-': rain-=0.1
        
        snow=0
        if weather[2]=='SN':snow+=0.5
        elif weather[2]=='SG':snow+=0.5
        elif weather[2]=='IC':snow+=0.5
        elif weather[2]=='PL':snow+=0.5
        
        if snow>0:
            if weather[0]=='+': snow+=0.2
            if weather[0]=='-': snow-=0.2
        totalrain+=rain
        totalsnow+=snow
    return totalrain,totalsnow

def average_weather(metars,dtstart,dtend,altitude):

    from pytz import utc
    
    total_time=min(metars[-1].report_time.replace(tzinfo=utc),dtend)-max(metars[0].report_time.replace(tzinfo=utc),dtstart)
    
    values={
        'windspeed':0,
        'winddir':0,
        'temperature':0,
        'gust':0,
        'dewpoint':0,
        'relative_humidity':0,
        'rain':0,
        'snow':0,
        'pressure':0
    }
    
    from copy import copy
    from math import exp

    logger.debug('Averaging {} METARS'.format(len(metars)))

    total_weights=copy(values)
    logger.info('Ride time: {} - {}'.format(dtstart,dtend))
    
    for i,metar in enumerate(metars):
        
        if i==len(metars)-1:
            logger.debug('End of METAR array, not averaging.')
            break
        
        report_time=metar.report_time.replace(tzinfo=utc)
        next_report_time=metars[i+1].report_time.replace(tzinfo=utc)

        logger.debug('METAR time: {}'.format(report_time))
        if next_report_time<dtstart:
            logger.debug('Next METAR precedes dtstart, skipping.')
            continue
        if report_time>dtend:
            logger.debug('METAR time follows dtend, skipping.')
            break
        
        if report_time<dtstart:
            dt=dtstart-report_time
            weights=[0,0]
            weights[1]=dt.total_seconds()/(next_report_time-dtstart).total_seconds()
            weights[0]=1-weights[1]
        elif next_report_time>dtend:
            dt=dtend-report_time
            weights=[0,0]
            weights[0]=dt.total_seconds()/(dtend-report_time).total_seconds()
            weights[1]=1-weights[0]
        else:
            dt=next_report_time-report_time
            weights=[0.5,0.5]
        interval_weight=dt.total_seconds()
        weights=[weight*interval_weight for weight in weights]

        if metars[i].windspeed!=None:
            values['windspeed']+=metars[i].windspeed*weights[0]
            total_weights['windspeed']+=weights[0]
        if metars[i+1].windspeed!=None:
            values['windspeed']+=metars[i+1].windspeed*weights[1]
            total_weights['windspeed']+=weights[1]

        if metars[i].winddir!=None:
            values['winddir']+=metars[i].winddir*weights[0]
            total_weights['winddir']+=weights[0]
        if metars[i+1].winddir!=None:
            values['winddir']+=metars[i+1].winddir*weights[1]
            total_weights['winddir']+=weights[1]

        if metars[i].gust!=None:
            values['gust']+=metars[i].gust*weights[0]
            total_weights['gust']+=weights[0]
        if metars[i+1].gust!=None:
            values['gust']+=metars[i+1].gust*weights[1]
            total_weights['gust']+=weights[1]

        if metars[i].temperature!=None:
            values['temperature']+=metars[i].temperature*weights[0]
            total_weights['temperature']+=weights[0]
        if metars[i+1].temperature!=None:
            values['temperature']+=metars[i+1].temperature*weights[1]
            total_weights['temperature']+=weights[1]

        if metars[i].dewpoint!=None:
            values['dewpoint']+=metars[i].dewpoint*weights[0]
            total_weights['dewpoint']+=weights[0]
        if metars[i+1].dewpoint!=None:
            values['dewpoint']+=metars[i+1].dewpoint*weights[1]
            total_weights['dewpoint']+=weights[1]

        if metars[i].pressure!=None and metars[i].temperature!=None:
            obs=metars[i]
            pressure=obs.pressure*exp(-altitude/((obs.temperature+273.15)*29.263))
            values['pressure']+=pressure*weights[0]
            total_weights['pressure']+=weights[0]
        if metars[i+1].pressure!=None and metars[i+1].temperature!=None:
            obs=metars[i+1]
            pressure=obs.pressure*exp(-altitude/((obs.temperature+273.15)*29.263))
            values['pressure']+=pressure*weights[1]
            total_weights['pressure']+=weights[1]

        if metars[i].temperature!=None and metars[i].dewpoint!=None:
            temperature=metars[i].temperature
            vapres=6.1121*exp((18.678-temperature/234.5)*temperature/(temperature+257.14))
            dewpt=metars[i].dewpoint
            vapres_dew=6.1121*exp((18.678-dewpt/234.5)*dewpt/(dewpt+257.14))
            rh=vapres_dew/vapres
            values['relative_humidity']+=rh*weights[0]
            total_weights['relative_humidity']+=weights[0]
        if metars[i+1].temperature!=None and metars[i+1].dewpoint!=None:
            temperature=metars[i+1].temperature
            vapres=6.1121*exp((18.678-temperature/234.5)*temperature/(temperature+257.14))
            dewpt=metars[i+1].dewpoint
            vapres_dew=6.1121*exp((18.678-dewpt/234.5)*dewpt/(dewpt+257.14))
            rh=vapres_dew/vapres
            values['relative_humidity']+=rh*weights[1]
            total_weights['relative_humidity']+=weights[1]

        this_metar=Metar.Metar(metars[i].metar,
                         year=metar.report_time.year,
                         month=metar.report_time.month, utcdelta=0)
        rain,snow=weather_to_numeric(this_metar.weather)
        values['rain']+=rain*weights[0]
        values['snow']+=snow*weights[0]
        total_weights['rain']+=weights[0]
        total_weights['snow']+=weights[0]
        next_metar=Metar.Metar(metars[i+1].metar,
                         year=metars[i+1].report_time.year,
                         month=metars[i+1].report_time.month, utcdelta=0)
        rain,snow=weather_to_numeric(next_metar.weather)
        values['rain']+=rain*weights[1]
        values['snow']+=snow*weights[1]
        total_weights['rain']+=weights[1]
        total_weights['snow']+=weights[1]

    for key,weight in total_weights.items():
        try:
            values[key]=values[key]/weight
        except ZeroDivisionError:
            del(values[key])

    return values

def ride_times_utc(ride):
    from pytz import timezone,utc

    dtstart=ride.start_time.replace(
        tzinfo=timezone(ride.start_timezone)
    ).astimezone(utc)
    
    dtend=ride.end_time.replace(
        tzinfo=timezone(ride.end_timezone)
    ).astimezone(utc)

    return dtstart,dtend

@celery.task(ignore_result=True)
def update_ride_weather(ride_id):

    from ..celery import session_factory
    from ..models import get_tm_session
    
    dbsession=get_tm_session(session_factory,transaction.manager)
    
    logger.debug('Received update weather task for ride {}'.format(ride_id))

    ride=dbsession.query(Ride).filter(Ride.id==ride_id).one()

    metars=fetch_metars_for_ride(dbsession,ride)

    dtstart,dtend=ride_times_utc(ride)
    altitude=(ride.startloc.elevation+ride.endloc.elevation)*0.5
    averages=average_weather(metars,dtstart,dtend,altitude)
    logger.debug('Ride weather average values: {}'.format(averages))
    if len(averages)>0:
        if ride.wxdata is None:
            ride.wxdata=RideWeatherData()
        ride.wxdata.station=metars[0].station
        for key,value in averages.items():
            setattr(ride.wxdata,key,value)

    transaction.commit()

    return ride_id
