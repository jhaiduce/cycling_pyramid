from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm import sessionmaker 
from sqlalchemy import engine_from_config, create_engine
from pyramid.paster import bootstrap, setup_logging
from sqlalchemy.orm.exc import NoResultFound
import argparse
import sys

from .. import models


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'config_uri',
        help='Configuration file, e.g., development.ini',
    )
    return parser.parse_args(argv[1:])

def clobber_previous_imports(session):
    session.query(models.cycling_models.Location).delete()
    session.query(models.cycling_models.LocationType).delete()
    session.query(models.cycling_models.Ride).delete()
    session.query(models.cycling_models.RideWeatherData).delete()
    session.query(models.cycling_models.WeatherData).delete()

def import_data(session,new_session):



    Base = automap_base()

    # reflect the tables
    Base.prepare(session.bind, reflect=True)
    
    # Get distinct location types
    for loctype, in session.query(Base.classes.locations.type).distinct():
        print(loctype)
        new_session.add(models.cycling_models.LocationType(name=loctype))

    locations=session.query(Base.classes.locations)

    # Import locations
    for location in locations:
        print('{} ({})'.format(location.name,location.type))
        new_location=models.cycling_models.Location()
        new_location.name=location.name
        new_location.lon=location.lon
        new_location.lat=location.lat
        new_location.elevation=location.elevation
        new_location.remarks=location.remarks
        # Find matching LocationType
        loctype=new_session.query(
            models.cycling_models.LocationType).filter(
            models.cycling_models.LocationType.name==location.type
        ).first()
        new_location.loctype=loctype
        new_session.add(new_location)

    ridergroup_ids=session.query(Base.classes.rides.rode_with_others).group_by(Base.classes.rides.rode_with_others)

    for ridergroup_id, in ridergroup_ids:
        ridergroup=models.cycling_models.RiderGroup(id=ridergroup_id+1,name=str(ridergroup_id))
        new_session.add(ridergroup)
        
    equipment_ids=session.query(Base.classes.rides.equipment_id).group_by(Base.classes.rides.equipment_id)

    for equipment_id, in equipment_ids:
        equipment=models.cycling_models.Equipment(id=equipment_id+1,name=str(equipment_id))
        new_session.add(equipment)
        
    surfacetype_ids=session.query(Base.classes.rides.surface).group_by(Base.classes.rides.surface)
    
    for surfacetype_id, in surfacetype_ids:
        if surfacetype_id is None: continue
        surface=models.cycling_models.SurfaceType(id=surfacetype_id+1,name=str(surfacetype_id))
        new_session.add(surface)
        
    rides=session.query(Base.classes.rides)

    for ride in rides:
        new_ride=models.cycling_models.Ride()
        print('{} {} - {}'.format(ride.start_time,ride.startloc,ride.endloc))
        new_ride.start_time=ride.start_time
        new_ride.end_time=ride.end_time
        new_ride.startloc=new_session.query(
            models.cycling_models.Location).filter(
            models.cycling_models.Location.name==ride.startloc
        ).first()
        new_ride.endloc=new_session.query(
            models.cycling_models.Location).filter(
            models.cycling_models.Location.name==ride.endloc
        ).first()
        new_ride.route=ride.midway_stops
        new_ride.heartrate_avg=ride.heartrate_avg
        new_ride.heartrate_max=ride.heartrate_max
        new_ride.ridergroup=new_session.query(
            models.cycling_models.RiderGroup).filter(
                models.cycling_models.RiderGroup.id==ride.rode_with_others+1
            ).one()
        new_ride.equipment=new_session.query(
            models.cycling_models.Equipment).filter(
                models.cycling_models.Equipment.id==ride.equipment_id+1
            ).one()
        new_ride.trailer=ride.trailer
        new_ride.roadwet=ride.roadWet
        new_ride.roadice=ride.roadIce
        new_ride.roadsnow=ride.roadSnow
        from sqlalchemy.orm.exc import NoResultFound
        if ride.surface is not None:
            surfacetype=new_session.query(
                models.cycling_models.SurfaceType).filter(
                    models.cycling_models.SurfaceType.id==ride.surface+1
                ).one()
        else:
            surfacetype=None
        new_ride.surface=surfacetype
        new_ride.distance=ride.distance
        
        def time_to_timedelta(timeobj):
            from datetime import datetime, date, time
            if timeobj is not None:
                return datetime.combine(date.min,timeobj)-datetime.min
            else: return None
            
        new_ride.rolling_time=time_to_timedelta(ride.ridetime)
        new_ride.total_time=time_to_timedelta(ride.total_time)
        new_ride.odometer=ride.odometer
        new_ride.estdist=ride.estdist
        new_ride.estime=ride.estime
        new_ride.avspeed=ride.avspeed
        new_ride.maxspeed=ride.maxspeed
        new_ride.badData=ride.dataSuspect
        new_ride.mechanicalFailure=ride.mechanicalFailure
        new_ride.mishapSeverity=ride.mishapSeverity
        new_ride.remarks=ride.remarks
        
        try:
            weather_station_location=new_session.query(
                models.cycling_models.Location
            ).filter(
                models.cycling_models.Location.name==ride.wx_station
            ).one()
        except NoResultFound:
            weather_station_location=None
            
        new_ride.wxdata=models.cycling_models.RideWeatherData(
            station=weather_station_location,
            windspeed=ride.windspeed,
            gust=ride.gust,
            winddir=ride.winddir,
            temperature=ride.temperature,
            dewpoint=ride.dewpt,
            pressure=ride.pressure,
            relative_humidity=ride.rh,
            rain=ride.rain,
            snow=ride.snow                        
        )
        new_session.add(new_ride)

def main(argv=sys.argv):

    args = parse_args(argv)
    setup_logging(args.config_uri)
    env = bootstrap(args.config_uri)

    engine = create_engine("mysql://cycling:cycling@172.18.0.1/cycling")
     
    # mapped classes are now created with names by default
    # matching that of the table name.

    session = sessionmaker(bind=engine)()

    with env['request'].tm:
        new_session=env['request'].dbsession
        clobber_previous_imports(new_session)
        import_data(session,new_session)
