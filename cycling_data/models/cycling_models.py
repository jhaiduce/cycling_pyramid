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
    Interval,
    Binary
)
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm import relationship
from sqlalchemy import func, orm
from sqlalchemy.orm.exc import NoResultFound

from .meta import Base

from timezonefinder import TimezoneFinder
tz=TimezoneFinder()

def register_function(raw_con, conn_record):

    if isinstance(raw_con ,pysqlite2.dbapi2.Connection):
        raw_con.create_function("cos", 1, math.cos)
        raw_con.create_function("sin", 1, math.sin)
        raw_con.create_function("acos", 1, math.acos)
        raw_con.create_function("atan2", 2, math.atan2)

class TimestampedRecord(object):
    entry_date_ = Column('entry_date', DateTime, server_default=func.now())
    modified_date_ = Column('modified_date', DateTime,
                            server_default=func.now(), onupdate=func.now())

    @hybrid_property
    def entry_date(self):
        return self.entry_date_

    @entry_date.expression
    def entry_date(self):
        return cls.entry_date_

    @hybrid_property
    def modified_date(self):
        return self.modified_date_

    @modified_date.expression
    def modified_date(cls):
        return cls.modified_date_

class PredictionModel(Base,TimestampedRecord):

    __tablename__ = 'predictionmodel'
    __table_args__={'mysql_encrypted':'yes'}

    id = Column(Integer, Sequence('predictionmodel_seq'), primary_key=True)
    weightsbuf=Column('weights',Binary)
    statsbuf_=Column('stats',Text)
    stats_=None
    predict_columns_=Column('predict_columns',Text)
    input_columns_=Column('input_columns',Text)
    train_dataset_size_=Column('train_dataset_size',Integer)
    input_size_=Column('input_size',Integer)
    training_in_progress=Column(Boolean,default=False)

    def __init__(self,*args,**kwargs):

        super(PredictionModel,self).__init__(*args,**kwargs)

        self.model_=None

    @orm.reconstructor
    def init_on_load(self):
        self.model_=None

    def __restore_weights(self):
        import io
        import h5py

        if self.model_ is not None and self.weightsbuf is not None:
            bio = io.BytesIO(self.weightsbuf)

            with h5py.File(bio,'r') as weightfile:

                weights=[]

                for key in weightfile.keys():
                    weights.append(weightfile[key])

                self.model_.set_weights(weights)

    def __save_weights(self):
        import io
        import h5py

        if self.model_ is not None:
            weights=self.model_.get_weights()

            bio = io.BytesIO()

            with h5py.File(bio,'w') as weightfile:
                for i in range(len(weights)):
                    weightfile.create_dataset('weight_{}'.format(i),data=weights[i])
            self.weightsbuf=bio.getvalue()

    @property
    def model(self):
        from .prediction import build_model

        if self.model_ is None:
            self.model_=build_model(self.train_dataset_size,self.input_size)

        if self.weightsbuf is not None:
            self.__restore_weights()

        return self.model_

    @hybrid_property
    def train_dataset_size(self):
        return self.train_dataset_size_

    @train_dataset_size.expression
    def train_dataset_size(cls):
        return cls.train_dataset_size_

    @train_dataset_size.update_expression
    def train_dataset_size(cls,new_dataset_size):
        return [
            (cls.train_dataset_size_, new_dataset_size)
        ]

    @hybrid_property
    def input_size(self):
        return self.input_size_

    @input_size.expression
    def input_size(cls):
        return cls.input_size_

    @input_size.update_expression
    def input_size(cls,new_dataset_size):
        return [
            (cls.input_size_, new_dataset_size)
        ]

    def norm(self,x):
        std=self.stats['std'].replace(0,1)
        return (x - self.stats['mean']) / std

    def train(self,train_dataset,predict_columns,epochs=2000,patience=300):
        import pandas as pd
        from .prediction import get_data
        import io
        import h5py
        from tensorflow import keras
        import tensorflow_docs as tfdocs
        import tensorflow_docs.modeling

        train_dataset=train_dataset.dropna()

        train_stats = train_dataset.describe()
        train_stats = train_stats.drop(columns=predict_columns)
        train_stats = train_stats.transpose()

        self.stats=train_stats

        train_labels=train_dataset[predict_columns]
        train_dataset = train_dataset.drop(columns=predict_columns)

        normed_train_data = self.norm(train_dataset)

        self.train_dataset_size_=train_dataset.shape[0]
        self.input_size_=train_dataset.shape[1]

        EPOCHS=epochs

        # The patience parameter is the amount of epochs to check for
        # improvement
        early_stop = keras.callbacks.EarlyStopping(
            monitor='val_loss', min_delta=1e-7, patience=patience)

        history=self.model.fit(normed_train_data, train_labels,
                          epochs=EPOCHS, validation_split = 0.2, verbose = 0,
                          callbacks=[early_stop, tfdocs.modeling.EpochDots()])

        self.predict_columns=predict_columns

        self.__save_weights()

    def predict(self,data,samples=100):
        import numpy as np

        if len(self.predict_columns)==0:
            return
        normed_data=self.norm(data.drop(columns=self.predict_columns))

        predictions=self.model.predict(normed_data)

        return predictions

    @property
    def predict_columns(self):
        import json
        if self.predict_columns_:
            return json.loads(self.predict_columns_)
        else:
            return []

    @predict_columns.setter
    def predict_columns(self,new_value):
        import json
        self.predict_columns_=json.dumps(new_value)

    @property
    def stats(self):

        import pandas as pd
        import io

        if self.statsbuf_ is None and self.stats_ is None:
            return None

        if self.stats_ is None:
            with io.StringIO(self.statsbuf_) as sio:
                self.stats_=pd.read_json(sio)

        return self.stats_

    @stats.setter
    def stats(self,newstats):
        import io
        import pandas as pd
        import tables
        import os

        self.stats_=newstats

        with io.StringIO(self.statsbuf_) as sio:
           self.stats_.to_json(sio)
           self.statsbuf_=sio.getvalue()

class LocationType(Base):
    __tablename__ = 'locationtype'
    __table_args__={'mysql_encrypted':'yes'}
    
    id = Column(Integer, Sequence('locationtype_seq'), primary_key=True)
    name = Column(String(255),unique=True)
    description = Column(Text)
        
class Location(Base,TimestampedRecord):
    __tablename__ = 'location'
    __table_args__={'mysql_encrypted':'yes'}
    
    id = Column(Integer, Sequence('location_seq'), primary_key=True)
    name = Column(String(512),index=True,unique=True)
    lat = Column(Float)
    lon = Column(Float)
    elevation = Column(Float)
    description = Column(Text)
    remarks = Column(Text)
    timezone_ = None
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

    @property
    def timezone(self):

        if self.timezone_ is None \
           and self.lat is not None and self.lon is not None:
            self.timezone_ = tz.timezone_at(lat=self.lat,lng=self.lon)

        return self.timezone_

    def __str__(self):
        return self.name.__str__()

class Equipment(Base):
    __tablename__ = 'equipment'
    __table_args__={'mysql_encrypted':'yes'}
    
    id = Column(Integer, Sequence('equipment_seq'), primary_key=True)
    name = Column(String(255),unique=True)

    def __repr__(self):
        return self.name

class SurfaceType(Base):
    __tablename__ = 'surfacetype'
    __table_args__={'mysql_encrypted':'yes'}
    
    id = Column(Integer, Sequence('surfacetype_seq'), primary_key=True)
    name = Column(String(255),unique=True)

    def __repr__(self):
        return self.name

class Riders(Base):
    __tablename__ = 'rider'
    __table_args__={'mysql_encrypted':'yes'}
    
    id = Column(Integer, Sequence('rider_seq'), primary_key=True)
    name = Column(String(255),unique=True)

    def __repr__(self):
        return self.name

class RiderGroup(Base):
    __tablename__ = 'ridergroup'
    __table_args__={'mysql_encrypted':'yes'}
    
    id = Column(Integer, Sequence('ridergroup_seq'), primary_key=True)
    name = Column(String(255),unique=True)

    def __repr__(self):
        return self.name

class WeatherData(Base,TimestampedRecord):
    __tablename__ = 'weatherdata'
    __table_args__={'mysql_encrypted':'yes'}    

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
    __table_args__={'mysql_encrypted':'yes'}
    
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
    __table_args__={'mysql_encrypted':'yes'}
    
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

        from math import exp

        if isinstance(loc,Location):
            altitude=loc.elevation
        else:
            altitude=loc

        wx=self.copy()
        wx.pressure=wx.pressure*exp(-altitude/((wx.temperature+273.15)*29.263))
        wx.temperature=wx.temperature-(altitude-wx.station.elevation)*6.4/1000
        return wx

    def copy(self):
        wx=StationWeatherData()
        fields=['windspeed','gust','winddir','temperature','dewpoint','pressure','relative_humidity','wx_station','station','kind']
        for field in fields:
            setattr(wx,field,getattr(self,field))
        return wx
    
    def __init__(self,session=None,obs=None,*args,**kwargs):

        super(StationWeatherData,self).__init__(*args,**kwargs)
        from metar import Metar

        if obs!=None:
            assert(isinstance(obs,Metar.Metar))
            from sqlalchemy import and_
            
            try:
                self.station=session.query(Location).filter(and_(Location.name==obs.station_id,Location.loctype_id==2)).one()
                self.report_time=obs.time
            except NoResultFound:
                location=Location(name=obs.station_id,loctype_id=2)
                session.add(location)

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
            try: self.dewpoint=obs.dewpt.value(units='C')
            except AttributeError: self.dewpoint=None
            try: self.pressure=obs.press.value('hpa')
            except AttributeError: self.pressure=None
            self.relative_humidity=rh
            self.metar=obs.code

class Ride(Base,TimestampedRecord):
    __tablename__ = 'ride'
    __table_args__={'mysql_encrypted':'yes'}
    
    id = Column(Integer, Sequence('ride_seq'), primary_key=True)

    # Date and time fields
    start_time_ = Column('start_time',DateTime)
    end_time_ = Column('end_time',DateTime)
    start_timezone_ = Column('start_timezone',String(255))
    end_timezone_ = Column('end_timezone',String(255))

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

    @hybrid_property
    def start_time(self):
        import pytz

        if self.start_time_ is None:
            return None

        if self.start_timezone:
            return self.start_time_.replace(
                tzinfo=pytz.timezone(self.start_timezone))
        elif self.end_timezone:
            return self.start_time_.replace(
                tzinfo=pytz.timezone(self.end_timezone)
            )
        else:
            return self.start_time_.replace(
                tzinfo=pytz.timezone('UTC')
            )

    @start_time.setter
    def start_time(self,new_start_time):
        self.start_time_=new_start_time

    @start_time.expression
    def start_time(cls):
        return cls.start_time_

    @start_time.update_expression
    def start_time(cls,new_start_time):
        return [
            (cls.start_time_, new_start_time)
        ]

    @hybrid_property
    def end_time(self):
        import pytz
        if self.end_timezone:
            return self.end_time_.replace(
                tzinfo=pytz.timezone(self.end_timezone))
        elif self.start_timezone:
            return self.end_time_.replace(
                tzinfo=pytz.timezone(self.start_timezone))
        else:
            return self.end_time_.replace(
                tzinfo=pytz.timezone('UTC')
            )

    @end_time.setter
    def end_time(self,new_end_time):
        self.end_time_=new_end_time

    @end_time.update_expression
    def end_time(cls,new_end_time):
        return [
            (cls.end_time_, new_end_time)
        ]

    @end_time.expression
    def end_time(cls):
        return cls.end_time_

    @property
    def average_speed(self):
        if self.avspeed:
            return self.avspeed
        elif self.distance and self.rolling_time:
            return self.distance/self.rolling_time.total_seconds()*3600

    @property
    def start_timezone(self):

        if self.startloc is None:
            if self.endloc is not None:
                return self.end_timezone
            else:
                return None

        if not self.start_timezone_:
            self.start_timezone_=self.startloc.timezone
            
        return self.start_timezone_

    @start_timezone.setter
    def start_timezone(self,value):
        self.start_timezone_=value

    @property
    def end_timezone(self):

        if self.endloc is None:
            if self.start_timezone is not None:
                return self.start_timezone
            else:
                return None

        if not self.end_timezone_:
            self.end_timezone_=self.endloc.timezone
            
        return self.end_timezone_

    @end_timezone.setter
    def end_timezone(self,value):
        self.end_timezone_=value

    @property
    def grade(self):
        if self.distance is None or \
           self.startloc is None or self.endloc is None \
           or self.startloc.elevation is None or self.endloc.elevation is None:
            return None
        distance_m=self.distance/1000
        return (self.endloc.elevation-self.startloc.elevation)/distance_m

    @property
    def azimuth(self):
        """
        Azimuth from self.startloc to self.endloc
        """

        if self.startloc is None or self.endloc is None \
           or self.startloc.lon is None or self.startloc.lat is None \
           or self.endloc.lon is None or self.endloc.lon is None:
            return None

        from math import atan2

        return atan2(self.endloc.lon - self.startloc.lon,
                     self.endloc.lat - self.startloc.lat)

    @property
    def tailwind(self):
        from math import cos

        if self.wxdata is None: return None

        if self.azimuth is None or self.wxdata.winddir is None:
            return None

        return cos((self.azimuth-180)-self.wxdata.winddir)*self.wxdata.windspeed

    @property
    def crosswind(self):
        from math import sin

        if self.wxdata is None: return None

        if self.azimuth is None or self.wxdata.winddir is None:
            return None

        return sin((self.azimuth-180)-self.wxdata.winddir)*self.wxdata.windspeed

    @property
    def fraction_day(self):
        from astral import LocationInfo
        from astral.sun import sun
        from datetime import timedelta, time, datetime

        def location_to_locationinfo(loc):
            return LocationInfo(
                name=loc.name,
                timezone=loc.timezone,
                latitude=loc.lat,
                longitude=loc.lon)

        if (self.startloc is not None
            and self.startloc.lat is not None
            and self.startloc.lon is not None):
            loc=location_to_locationinfo(self.startloc)
        elif (self.endloc is not None
              and self.endloc.lat is not None
              and self.endloc.lon is not None):
            loc=location_to_locationinfo(self.endloc)
        else:
            return None

        if self.start_time is None or self.end_time is None:
            return None

        if self.end_time < self.start_time:
            return None

        numdays=(self.end_time.date()-self.start_time.date()).days+1

        time_day=timedelta(0)
        time_night=timedelta(0)

        for i in range(numdays):

            day=self.start_time.date()+timedelta(i)
            daystart=datetime.combine(day,time(tzinfo=self.start_time.tzinfo))

            s=sun(loc.observer,date=day)

            # Portion of ride before sunrise
            predawn_segment = (
                min(max(s['sunrise'], self.start_time), self.end_time)
                - max(self.start_time, daystart)
            )

            # Daytime part of ride
            day_segment = (
                max(min(s['sunset'], self.end_time),self.start_time) -
                min(max(s['sunrise'], self.start_time), self.end_time)
            )

            # Part of ride after sunset
            postdusk_segment = (
                min(self.end_time, daystart + timedelta(1) ) -
                max(min(s['sunset'], self.end_time), self.start_time)
            )

            if i>0 and i<numdays-1:
                if abs((
                        predawn_segment+day_segment+postdusk_segment
                        -timedelta(1)
                ).total_seconds()) > 5:
                    raise ValueError(
                        'On ride {}: Segments do not fill day'.format(self.id))

            time_day+=day_segment
            time_night+=predawn_segment+postdusk_segment

        total_time = self.end_time - self.start_time
        accounted_time = time_night + time_day

        if abs((total_time - accounted_time).total_seconds()) > 5:
            raise ValueError(
                'On ride {}: Day/night times do not cover duration of ride.'.format(self.id))

        if total_time==timedelta(0):
           return None

        return time_day.total_seconds()/total_time.total_seconds()

    @property
    def crowdist(self):
        if self.endloc is None or self.startloc is None \
           or self.endloc.lat is None or self.startloc.lat is None \
           or self.endloc.lon is None or self.startloc.lon is None:
            return None

        if self.endloc.elevation is None or self.startloc.elevation is None:
            dalt=0
        else:
            dalt=self.endloc.elevation-self.startloc.elevation

        from math import sqrt
        return sqrt(1.2391e4 * ((self.endloc.lat - self.startloc.lat)**2
                                + (self.endloc.lon - self.startloc.lon)**2)
                    + dalt**2)
