from ..models.cycling_models import Ride, WeatherData, StationWeatherData, RideWeatherData, Location
from metar import Metar
from datetime import datetime, timedelta

import requests

def download_metars(station,dtstart,dtend):
    
    url="https://www.ogimet.com/display_metars2.php?lang=en&lugar={station}&tipo=ALL&ord=REV&nil=SI&fmt=txt&ano={yearstart}&mes={monthstart}&day={daystart}&hora={hourstart}&anof={yearend}&mesf={monthend}&dayf={dayend}&horaf={hourend}&minf=59&send=send".format(station=station,yearstart=dtstart.year,monthstart=dtstart.month,daystart=dtstart.day,hourstart=dtstart.hour,yearend=dtend.year,monthend=dtend.month,dayend=dtend.day,hourend=dtend.hour)

    r=requests.get(url)

    html=r.text

    print(html)

    import re
    matches=re.findall(r'(\d+) ((METAR|SPECI)[^=,]*)',html)

    metars=[]
    for match in matches:
        try:
            timestamp=match[0]
            metar=Metar.Metar(match[1],
                              year=int(timestamp[:4]),
                              month=int(timestamp[4:6]),utcdelta=0)
            if metar.time is None:
                print('METAR time invalid')
                print(match)
                continue
            metars.append(metar)
        except (Metar.ParserError,e):
            print(match[0])
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

    stored_metars=session.query(StationWeatherData).filter(
        StationWeatherData.station==station
    ).filter(
        StationWeatherData.report_time>dtstart-window_expansion
    ).filter(
        StationWeatherData.report_time>dtstart+window_expansion
    ).order_by(StationWeatherData.report_time).all()

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
