from ..models.cycling_models import Ride, WeatherData, StationWeatherData, RideWeatherData, Location, SentRequestLog
from metar import Metar
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy.orm.exc import NoResultFound
from ..celery import celery

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

import transaction

import requests

from time import sleep

update_weather_group_max=50

def random_delay(min_delay=1,random_scale=None):

    import random
    from math import log

    if random_scale is None:
        random_scale=min_delay
    elif random_scale<=0:
        raise ValueError(
            'random_scale must be >=0 (got {})'.format(random_scale))

    random_max=random.uniform((random_scale)*3,(random_scale)*5)

    return min_delay+min(random.lognormvariate(log(random_scale),1),random_max)


def fetch_metars(station,dtstart,dtend,url='https://www.ogimet.com/display_metars2.php'):

    params={
        'lang':'en',
        'lugar':station,
        'tipo':'SA',
        'ord':'DIR',
        'nil':'NO',
        'fmt':'txt',
        'ano':dtstart.year,
        'mes':'{:02d}'.format(dtstart.month),
        'day':'{:02d}'.format(dtstart.day),
        'hora':'{:02d}'.format(dtstart.hour),
        'anof':dtend.year,
        'mesf':'{:02d}'.format(dtend.month),
        'dayf':'{:02d}'.format(dtend.day),
        'horaf':'{:02d}'.format(dtend.hour),
        'minf':'{:02d}'.format(dtend.minute),
        'send':'send'
    }

    r=requests.get(url,params=params)

    r.raise_for_status()

    return r

def extract_metars_from_ogimet(text):

    dates=[]
    metars=[]

    while True:

        # Find next METAR
        head,sep,text=text.partition('=\n')

        # Check whether we reached the end of the string
        if len(head)==0: break

        # Skip comments and empty lines
        if head.startswith('#') or head.startswith('\n'):
            head,sep,text=text.partition('\n')

        # Parse METAR
        if head[:12].isdigit():
            date=datetime.strptime(head[:12],'%Y%m%d%H%M%S')
            dates.append(date)
            metar=head[13:]
            if(metar.endswith('$')): metar=metar[:-1]
            metars.append(metar)

    return dates,metars

def download_metars(station,dtstart,dtend,dbsession=None,task=None):

    import random
    import transaction
    from pytz import utc

    logger.info('Downloading METARS for {}, {} - {}'.format(station,dtstart,dtend))

    slow_query=((datetime.utcnow().replace(tzinfo=utc)-dtstart).days > 84)

    tm=transaction.manager

    from pyramid.paster import bootstrap
    try:
        settings = bootstrap('/run/secrets/production.ini')['registry'].settings
        ogimet_url=settings['ogimet_url']
    except:
        ogimet_url='https://www.ogimet.com/display_metars2.php'

    with tm:
        try:
            last_request=dbsession.query(SentRequestLog).order_by(SentRequestLog.time.desc()).first()
        except NoResultFound:
            last_request=None
        recent_request_count=dbsession.query(SentRequestLog).filter(
        SentRequestLog.time>datetime.now()-timedelta(seconds=3600*2)).count()

    min_delay_seconds=60*2
    random_delay_scale=60*2
    retry_delay=random_delay(min_delay_seconds,random_delay_scale)

    rate_limited_retry_delay=random_delay(3600*3,3600*3)

    if slow_query and last_request is not None and (datetime.now()-last_request.time).total_seconds() < rate_limited_retry_delay and last_request.rate_limited:
        raise RuntimeError('Last OGIMET request was {} minutes ago and was rate limited'.format((datetime.now()-last_request.time).total_seconds()/60))

    if recent_request_count>=55:
        if task is not None:
            raise task.retry(
                exc=RuntimeError('Too many recent OGIMET queries. Retrying in {} seconds'.format(retry_delay)),countdown=retry_delay)
        else:
            sleep(retry_delay)

    if slow_query and last_request is not None and \
       (datetime.now()-last_request.time).total_seconds() < min_delay_seconds:
        if task is not None:
            raise task.retry(
                exc=RuntimeError('Too soon since last OGIMET query. Retrying in {} seconds'.format(retry_delay)),countdown=retry_delay)
        else:
            sleep(retry_delay)

    # Download METARs
    ogimet_result=fetch_metars(station,dtstart,dtend,url=ogimet_url)

    with tm:
        requestlog=SentRequestLog(
            time=datetime.now(),
            status_code=ogimet_result.status_code,
            url=ogimet_result.url)

        ogimet_text=ogimet_result.text
        dbsession.add(requestlog)

    try:
        if(ogimet_text.find('#Sorry')>-1):
            e=ValueError('OGIMET quota limit reached, response was: "{}"'.format(ogimet_text))
            e.text=ogimet_text
            requestlog.rate_limited=True
            if task is not None:
                raise task.retry(exc=e,countdown=retry_delay)
            else:
                raise e
        if(ogimet_text.find('SELECT command denied')>-1):
            e=ValueError('OGIMET internal database error')
            e.text=ogimet_text
            if task is not None:
                raise task.retry(exc=e,countdown=retry_delay)
            else:
                raise e
    finally:
        with tm:
            dbsession.merge(requestlog)

    # Get dates and METAR codes from returned text
    dates,metar_codes=extract_metars_from_ogimet(ogimet_text)

    if len(metar_codes)==0:
        logger.warn('No METARS found for {}, {} - {}, OGIMET response was {}'.format(station,dtstart,dtend,ogimet_text))

    # Parse metar codes
    metars=[
        Metar.Metar(metar_code,year=date.year,month=date.month,utcdelta=0)
        for date,metar_code in zip(dates,metar_codes)]

    # Sort in chronological order
    metars=sorted(metars,key=lambda m: m.time)
    
    return metars

def get_metars(session,station,dtstart,dtend,window_expansion=timedelta(seconds=3600*4),task=None):

    from pytz import utc
    import transaction

    logger.debug('Getting METARS from range {} - {}'.format(dtstart,dtend))

    tm=transaction.manager

    with tm:
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
        fetched_metars=download_metars(station.name,dtstart-window_expansion,dtend+window_expansion,dbsession=session,task=task)

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
                with tm:
                    session.add(wxdata)
            stored_metars.append(wxdata)

    return stored_metars

def fetch_metars_for_ride(session,ride,task=None):
    from .locations import get_nearby_locations
    import transaction

    tm = transaction.manager

    if (
            ride.start_time_ is None
            or ride.end_time_ is None
            or ride.startloc.lat is None
            or ride.endloc.lat is None
            or ride.startloc.lon is None
            or ride.endloc.lon is None
    ):
        # Incomplete time/location data, can't search for METARS
        return []

    lat_mid=(ride.startloc.lat+ride.endloc.lat)*0.5
    lon_mid=(ride.startloc.lon+ride.endloc.lon)*0.5

    with tm:
        dtstart,dtend=ride_times_utc(ride)

    with tm:
        nearby_stations=get_nearby_locations(session,lat_mid,lon_mid).filter(Location.loctype_id==2).limit(10)

    for station in nearby_stations:

        metars=get_metars(session,station,dtstart,dtend,task=task)
        
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

    from scipy.interpolate import interp1d

    from pytz import utc
    import numpy as np

    metars=sorted(metars, key=lambda metar: metar.report_time)
    
    total_time=min(metars[-1].report_time.replace(tzinfo=utc),dtend)-max(metars[0].report_time.replace(tzinfo=utc),dtstart)

    values={
        'wind_e':0,
        'wind_n':0,
        'temperature':0,
        'gust':0,
        'dewpoint':0,
        'rain':0,
        'snow':0,
        'pressure':0
    }
    
    logger.debug('Averaging {} METARS'.format(len(metars)))

    logger.info('Ride time: {} - {}'.format(dtstart,dtend))

    dtstart64=np.datetime64(dtstart.astimezone(utc))
    dtend64=np.datetime64(dtend.astimezone(utc))

    times=np.array([np.datetime64(metar.report_time.replace(tzinfo=utc)) for metar in metars])
    start_ind=np.searchsorted(times,dtstart64)
    end_ind=np.searchsorted(times,dtend64)

    rainsnow = [weather_to_numeric(
                Metar.Metar(metar.metar,
                            year=metar.report_time.year,
                            month=metar.report_time.month,
                            utcdelta=0).weather) for metar in metars]

    winddir=np.array([metar.winddir for metar in metars],dtype=float)
    windspeed=np.array([metar.windspeed for metar in metars],dtype=float)

    for key in values.keys():

        if key == 'rain':
            obs = np.array([precip[0] for precip in rainsnow]).astype(float)
        elif key == 'snow':
            obs = np.array([precip[1] for precip in rainsnow]).astype(float)
        elif key=='wind_e':
            obs=np.cos((90-winddir)*np.pi/180)*windspeed
        elif key=='wind_n':
            obs=np.sin((90-winddir)*np.pi/180)*windspeed
        else:
            obs=np.array([getattr(metar.weather_at_altitude(altitude),key) for metar in metars]).astype(float)

        obs_valid=np.isfinite(obs)

        if np.count_nonzero(obs_valid)<2:
            values[key] = None
            continue

        if times[obs_valid][0]>dtstart64 or times[obs_valid][-1]<dtend64:
            values[key] = None
            continue

        interpolator=interp1d(times[obs_valid].astype(float),obs[obs_valid])

        obs_start=interpolator(dtstart64.astype(float))
        obs_end=interpolator(dtend64.astype(float))

        # Observations taken during interval
        mid_mask=np.logical_and(obs_valid,np.logical_and(times>dtstart64,times<dtend64))

        obs_avg=np.trapz(
            np.concatenate([[obs_start],obs[mid_mask],[obs_end]]),
            np.concatenate([[dtstart64],times[mid_mask],[dtend64]]).astype(float)
        )/(dtend64-dtstart64).astype(float)

        values[key] = obs_avg

    # Convert wind components to polar coordinates
    winddir=(90-np.arctan2(values['wind_n']*180/np.pi,values['wind_e']))%360
    values['winddir']=winddir
    values['windspeed']=np.sqrt(values['wind_n']**2+values['wind_e']**2)

    # Delete Cartesian wind components
    del values['wind_n']
    del values['wind_e']

    return values

def ride_times_utc(ride):
    from pytz import timezone,utc

    dtstart=ride.start_time.replace(
        tzinfo=timezone(ride.start_timezone)
    ).astimezone(utc) if (ride.start_time is not None and
                          ride.start_timezone is not None) else None
    
    dtend=ride.end_time.replace(
        tzinfo=timezone(ride.end_timezone)
    ).astimezone(utc) if (ride.end_time is not None and
                          ride.end_timezone is not None) else None

    return dtstart,dtend

@celery.task()
def update_location_rides_weather(location_id):
    from ..celery import session_factory
    import transaction

    dbsession=session_factory()
    dbsession.expire_on_commit=False
    tm=transaction.manager

    with tm:

        logger.debug('Received update location rides weather task for location {}'.format(location_id))

        location_rides=dbsession.query(Ride).filter(
            ( Ride.startloc_id == location_id ) |
            ( Ride.endloc_id == location_id ) ).order_by(func.random()).limit(update_weather_group_max)

    from celery import chord

    # Update ride weather for all rides and re-train prediction model when
    # finished
    chord(
       update_ride_weather.signature((ride.id,),dict(train_model=False), countdown=random_delay(i*2+1)) for i,ride in enumerate(location_rides)
    )(after_fetch_tasks.s())

    return location_id

@celery.task(ignore_result=False)
def fill_missing_weather():
    from ..celery import session_factory
    from sqlalchemy import or_

    import transaction
    dbsession=session_factory()
    dbsession.expire_on_commit=False
    tm=transaction.manager

    with tm:
        rides_without_weather=dbsession.query(Ride).filter(
            or_(Ride.wxdata==None, RideWeatherData.wx_station==None)
        ).outerjoin(
            RideWeatherData,Ride.wxdata_id == RideWeatherData.id
        ).order_by(func.random()).limit(update_weather_group_max)

        from celery import chord, group

        ride_ids=[ride.id for ride in rides_without_weather]

        if rides_without_weather.count()>0:
            # Update ride weather for all rides and re-train prediction model when
            # finished
            chord(
                update_ride_weather.signature((ride_id,), dict(train_model=False), countdown=random_delay(i*2+1)) for i,ride_id in enumerate(ride_ids)
            )(after_fetch_tasks.s())

    return ride_ids

@celery.on_after_finalize.connect
def schedule_fill_missing_weather(sender,**kwargs):
    from celery.schedules import crontab
    sender.add_periodic_task(crontab(minute=5), fill_missing_weather.s())

@celery.task(bind=True,ignore_result=False,rate_limit='1/s',max_retries=3,retry_backoff=True)
def update_ride_weather(self,ride_id, train_model=True):

    from pytz import utc
    from ..celery import session_factory
    import transaction

    logger.debug('Received update weather task for ride {}'.format(ride_id))

    tm=transaction.manager

    dbsession=session_factory()
    dbsession.expire_on_commit=False

    with tm:

        ride=dbsession.query(Ride).filter(Ride.id==ride_id).one()
        dtstart,dtend=ride_times_utc(ride)
        if dtstart is None or dtend is None:
            return

    metars=fetch_metars_for_ride(dbsession,ride,task=self)

    if len(metars)==0: return

    metar_times=[metar.report_time.replace(tzinfo=utc) for metar in metars]

    if max(metar_times)<dtend or min(metar_times)>dtstart:
        # METARs do not span time of ride
        return

    with tm:

        metars=[dbsession.query(type(metar)).get(metar.id) for metar in metars]

        altitude=(ride.startloc.elevation+ride.endloc.elevation)*0.5

        averages=average_weather(metars,dtstart,dtend,altitude)
        logger.debug('Ride weather average values: {}'.format(averages))

        if len(averages)>0:
            ride=dbsession.query(Ride).filter(Ride.id==ride_id).one()
            if ride.wxdata is None:
                ride.wxdata=RideWeatherData()
            for key,value in averages.items():
                setattr(ride.wxdata,key,value)
            ride.wxdata.station=metars[0].station

    if train_model:
        from .regression import train_all_models
        train_all_models.delay()

    return ride_id

@celery.task(ignore_result=False)
def after_fetch_tasks(ride_ids):

    if len(ride_ids)==0:
        return

    if all(ride_id is None for ride_id in ride_ids):
        return

    from .regression import train_all_models
    train_all_models.delay()

    return ride_ids
