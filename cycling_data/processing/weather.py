from ..models.cycling_models import Ride, WeatherData, StationWeatherData, RideWeatherData, Location
from metar import Metar
from datetime import datetime, timedelta

from ..celery import celery

from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

import transaction

import requests

def download_metars(station,dtstart,dtend):
    
    logger.info('Downloading METARS for {}, {} - {}'.format(station,dtstart,dtend))

    url="https://www.ogimet.com/cgi-bin/getmetar?lang=en&icao={station}&begin={yearstart}{monthstart:02d}{daystart:02d}{hourstart:02d}00&end={yearend}{monthend:02d}{dayend:02d}{hourend:02d}59".format(station=station,yearstart=dtstart.year,monthstart=dtstart.month,daystart=dtstart.day,hourstart=dtstart.hour,yearend=dtend.year,monthend=dtend.month,dayend=dtend.day,hourend=dtend.hour)

    r=requests.get(url)

    lines=r.text.splitlines()

    metars=[]
    for line in lines:
        try:
            tokens=line.split(',')
            if len(tokens)==0: continue
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

def metar_to_StationWeatherData(session,metar):
    wxdata=StationWeatherData()
    try:
        vapres=6.1121*exp((18.678-metar.temp.value(units='C')/234.5)*metar.temp.value(units='C')/(metar.temp.value(units='C')+257.14))
        vapres_dew=6.1121*exp((18.678-metar.dewpt.value(units='C')/234.5)*metar.dewpt.value(units='C')/(metar.dewpt.value(units='C')+257.14))
        rh=vapres_dew/vapres
    except:
        rh=None

    from sqlalchemy.orm.exc import NoResultFound
    try:
        location=session.query(Location).filter(
            Location.name==metar.station_id).one()
    except NoResultFound:
        location=Location(name=metar.station_id)
        session.add(location)
    
    wxdata.station=location
    wxdata.wx_report_time=metar.time
    
    try: wxdata.windspeed=metar.wind_speed.value(units='mph')
    except AttributeError: pass
    try: wxdata.winddir=metar.wind_dir.value()
    except AttributeError: pass
    try: wxdata.gust=metar.wind_gust.value(units='mph')
    except AttributeError: pass
    try: wxdata.temperature=metar.temp.value(units='C')
    except AttributeError: pass
    try: wxdata.dewpt=metar.dewpt.value(units='C')
    except AttributeError: pass
    try: wxdata.pressure=metar.press.value('hpa')
    except AttributeError: pass
    wxdata.rh=rh
    if len(metar.weather)>0:
        wxdata.weather=''.join([attr for attr in metar.weather[0] if attr!=None])
    wxdata.metar=metar.code

    session.merge(wxdata)
    
    return wxdata

def get_metars(session,station,dtstart,dtend,window_expansion=timedelta(seconds=3600*4)):

    logger.info('Getting METARS from range {} - {}'.format(dtstart,dtend))

    stored_metars=session.query(StationWeatherData).filter(
        StationWeatherData.station==station
    ).filter(
        StationWeatherData.report_time>dtstart-window_expansion
    ).filter(
        StationWeatherData.report_time>dtstart+window_expansion
    ).order_by(StationWeatherData.report_time).all()

    logger.info('Stored METARS span range {} - {}'.format(stored_metars[0].report_time,stored_metars[-1].report_time))
    
    if len(stored_metars)>0:
        data_spans_interval=stored_metars[0]<dtstart and stored_metars[-1]>dtend
    else:
        data_spans_interval=False

    if not data_spans_interval:
        fetched_metars=download_metars(station.name,dtstart-window_expansion,dtend+window_expansion)

        stored_metars=[]

        for metar in fetched_metars:
            stored_metars.append(metar_to_StationWeatherData(session,metar))

    return stored_metars

def fetch_metars_for_ride(session,ride):
    from .locations import get_nearby_locations
    lat_mid=(ride.startloc.lat+ride.endloc.lat)*0.5
    lon_mid=(ride.startloc.lon+ride.endloc.lon)*0.5
    nearby_stations=get_nearby_locations(session,lat_mid,lon_mid).filter(Location.loctype_id==2).limit(10)

    for station in nearby_stations:
        
        metars=get_metars(session,station,ride.start_time,ride.end_time)
        
        if len(metars)>0:
            return metars
        
    return []

@celery.task
def update_ride_weather(ride_id):

    from ..celery import session_factory
    from ..models import get_tm_session
    
    dbsession=get_tm_session(session_factory,transaction.manager)
    
    logger.info('Received update weather task for ride {}'.format(ride_id))

    ride=dbsession.query(Ride).filter(Ride.id==ride_id).one()

    metars=fetch_metars_for_ride(dbsession,ride)

    transaction.commit()
    
    raise NotImplementedError('Task update_ride_weather not yet implemented')
    return ride_id
