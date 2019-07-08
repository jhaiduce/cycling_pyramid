from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    Text,
    Float,
    ForeignKey,
    Sequence,
    DateTime,
    Boolean,
    Interval
)
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import relationship

from .meta import Base

def register_function(raw_con, conn_record):

    if isinstance(raw_con ,pysqlite2.dbapi2.Connection):
        raw_con.create_function("cos", 1, math.cos)
        raw_con.create_function("sin", 1, math.sin)
        raw_con.create_function("acos", 1, math.acos)
        raw_con.create_function("atan2", 2, math.atan2)

class LocationType(Base):
    __tablename__ = 'locationtype'
    id = Column(Integer, Sequence('locationtype_seq'), primary_key=True)
    name = Column(String(255))
    description = Column(Text)
        
class Location(Base):
    __tablename__ = 'location'
    id = Column(Integer, Sequence('location_seq'), primary_key=True)
    name = Column(String(512),index=True)
    lat = Column(Float)
    lon = Column(Float)
    elevation = Column(Float)
    description = Column(Text)
    remarks = Column(Text)
    loctype_id = Column(Integer, ForeignKey('locationtype.id',name='fk_location_type_id'))
    loctype = relationship(LocationType,foreign_keys=loctype_id)

    @hybrid_method
    def great_circle_distance(self, other):
        """
        Tries to calculate the great circle distance between 
        the two locations by using the Haversine formula.

        If it succeeds, it will return the Haversine formula
        multiplied by 3959, which calculates the distance in miles.

        If it cannot, it will return None.

        """
        return math.acos(  math.cos(self.lat*math.pi/180)
                         * math.cos(other.lat*math.pi/180)
                         * math.cos((self.lon - other.lon)*math.pi/180)
                         + math.sin(self.lat*math.pi/180)
                         * math.sin(other.lat*math.pi/180)
                         ) * 6371

    @great_circle_distance.expression
    def great_circle_distance(cls, other):
        return sqlalchemy.func.acos(sqlalchemy.func.cos(cls.lat*math.pi/180)
                         * sqlalchemy.func.cos(other.lat*math.pi/180)
                         * sqlalchemy.func.cos((cls.lon - other.lon)*math.pi/180)
                         + sqlalchemy.func.sin(cls.lat*math.pi/180)
                         * sqlalchemy.func.sin(other.lat*math.pi/180)
                         ) * 6371

    def __repr__(self):
        return self.name

class Equipment(Base):
    __tablename__ = 'equipment'
    id = Column(Integer, Sequence('equipment_seq'), primary_key=True)
    name = Column(String(255))

    def __repr__(self):
        return self.name

class SurfaceType(Base):
    __tablename__ = 'surfacetype'
    id = Column(Integer, Sequence('surfacetype_seq'), primary_key=True)
    name = Column(String(255))

    def __repr__(self):
        return self.name

class Riders(Base):
    __tablename__ = 'rider'
    id = Column(Integer, Sequence('rider_seq'), primary_key=True)
    name = Column(String(255))

    def __repr__(self):
        return self.name

class RiderGroup(Base):
    __tablename__ = 'ridergroup'
    id = Column(Integer, Sequence('ridergroup_seq'), primary_key=True)
    name = Column(String(255))

    def __repr__(self):
        return self.name

class WeatherData(Base):
    __tablename__ = 'weatherdata'

    id = Column(Integer, Sequence('weatherdata_seq'), primary_key=True)

    windspeed = Column(Float)
    gust = Column(Float)
    winddir = Column(Float)
    temperature = Column(Float)
    dewpoint = Column(Float)
    pressure = Column(Float)
    relative_humidity = Column(Float)
    wx_station = Column(Integer, ForeignKey('location.id',name='fk_location_id'))
    station=relationship(Location)
    kind = Column(String(255))

    __mapper_args__ = {
        'polymorphic_on': kind,
        'polymorphic_identity':'weatherdata'
        }
    
class RideWeatherData(WeatherData):
    __tablename__='rideweatherdata'
    id = Column(
            Integer, 
            ForeignKey('weatherdata.id',name='fk_weatherdata_rideweatherdata_id'),  
            primary_key=True)
    rain = Column(Float)
    snow = Column(Float)
    __mapper_args__ = {
        'polymorphic_identity':'rideweatherdata'
        }

class StationWeatherData(WeatherData):
    __tablename__='stationweatherdata'
    id = Column(
            Integer, 
            ForeignKey('weatherdata.id',name='fk_weatherdata_stationweatherdata_id'),  
            primary_key=True)
    metar = Column(Text)
    report_time = Column(DateTime)
    weather = Column(String(255))
    __mapper_args__ = {
        'polymorphic_identity':'stationweatherdata'
        }

    def weather_at_altitude(self,loc):
        assert(isinstance(loc,Location))
        wx=self.copy()
        wx.pressure=wx.pressure*math.exp(-loc.elevation/(wx.temperature*29.263))
        wx.temperature=wx.temperature-(loc.elevation-wx.station.elevation)*6.4/1000
        return wx

    def copy(self):
        wx=StationWeatherData()
        fields=['windspeed','gust','winddir','temperature','dewpoint','pressure','relative_humidity','wx_station','station','kind']
        for field in fields:
            setattr(wx,field,getattr(self,field))
        return wx
    
    def __init__(self,session=None,obs=None,*args,**kwargs):

        super(StationWeatherData,self).__init__(*args,**kwargs)

        if obs!=None:
            assert(isinstance(obs,Metar.Metar))
            self.station=session.query(Location).filter(and_(Location.name==obs.station_id,Location.loctype==1)).one()
            self.report_time=obs.time
            try:
                vapres=6.1121*math.exp((18.678-obs.temp.value(units='C')/234.5)*obs.temp.value(units='C')/(obs.temp.value(units='C')+257.14))
                vapres_dew=6.1121*math.exp((18.678-obs.dewpt.value(units='C')/234.5)*obs.dewpt.value(units='C')/(obs.dewpt.value(units='C')+257.14))
                rh=vapres_dew/vapres
            except:
                rh=None
            self.windspeed=obs.wind_speed.value(units='mph')
            try: self.winddir=obs.wind_dir.value()
            except AttributeError: self.winddir=None
            try: self.gust=obs.wind_gust.value(units='mph')
            except AttributeError: self.gust=None
            try: self.temperature=obs.temp.value(units='C')
            except AttributeError: self.temperature=None
            try: self.dewpt=obs.dewpt.value(units='C')
            except AttributeError: self.dewpt=None
            try: self.pressure=obs.press.value('hpa')
            except AttributeError: self.pressure=None
            self.relative_humidity=rh
            self.metar=obs.code
        
    

class Ride(Base):
    __tablename__ = 'ride'

    id = Column(Integer, Sequence('ride_seq'), primary_key=True)

    # Date and time fields
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    start_timezone = Column(String(255))
    end_timezone = Column(String(255))

    # Location fields
    startloc_id = Column(
        Integer, ForeignKey('location.id',name='fk_startloc_id'))
    startloc=relationship(Location,foreign_keys=startloc_id)
    endloc_id = Column(Integer, ForeignKey('location.id',name='fk_endloc_id'))
    endloc=relationship(Location,foreign_keys=endloc_id)
    route = Column(Text)
    timezone = Column(String(255))

    # Rider fields
    rider = Column(
        Integer, ForeignKey('rider.id',name='fk_rider_id'))
    heartrate_avg = Column(Float)
    heartrate_min = Column(Float)
    heartrate_max = Column(Float)
    ridergroup_id = Column(Integer, ForeignKey('ridergroup.id'))
    ridergroup=relationship(RiderGroup,foreign_keys=ridergroup_id)

    # Equipment fields
    equipment_id = Column(
        Integer, ForeignKey('equipment.id',name='fk_equipment_id'))
    equipment = relationship(Equipment, foreign_keys=equipment_id)
    payloadweight = Column(Float)
    trailer = Column(Boolean)

    # Surface conditions
    roadWet = Column(Float)
    roadIce = Column(Float)
    roadSnow = Column(Float)
    surface_id = Column(Integer, 
        ForeignKey('surfacetype.id',name='fk_surface_id'))
    surface = relationship(SurfaceType,foreign_keys=surface_id)

    # Ride data
    distance = Column(Float)
    rolling_time = Column(Interval)
    total_time = Column(Interval)
    odometer = Column(Float)
    estdist = Column(Boolean)
    esttime = Column(Boolean)
    avspeed = Column(Float)
    maxspeed = Column(Float)
    badData = Column(Boolean)
    mechanicalFailure = Column(Float)
    mishapSeverity = Column(Float)
    remarks = Column(Text)

    # Weather conditions
    wxdata_id = Column(Integer,
        ForeignKey('weatherdata.id',name='fk_weatherdata_ride_id'))
    wxdata=relationship('RideWeatherData')

