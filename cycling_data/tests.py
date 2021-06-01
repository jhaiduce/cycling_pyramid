import unittest
from unittest.mock import patch, Mock

from pyramid import testing

import pytest

import transaction

import re

import json

from datetime import datetime, timedelta

from pytz import timezone, UTC

import numpy as np

def dict_to_postdata(inputdict):

    import collections

    postdata=[]

    for key,value in inputdict.items():
        if isinstance(value,collections.Mapping):
            postdata.append(('__start__',key+':mapping'))
            postdata.extend(dict_to_postdata(value))
            postdata.append(('__end__',key+':mapping'))
        else:
            postdata.append((key,str(value)))

    return postdata

mock_task_result=Mock()
mock_task_result.task_id=0

def dummy_request(dbsession):
    return testing.DummyRequest(dbsession=dbsession)


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp(settings={
            'sqlalchemy.url': 'sqlite:///:memory:'
        })
        self.config.include('.models')
        settings = self.config.get_settings()

        from .models import (
            get_engine,
            get_session_factory,
            get_tm_session,
            )

        self.engine = get_engine(settings)
        session_factory = get_session_factory(self.engine)

        self.session = get_tm_session(session_factory, transaction.manager)

    def init_database(self):
        from .models.meta import Base
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        from .models.meta import Base

        testing.tearDown()
        transaction.abort()
        Base.metadata.drop_all(self.engine)

class RideTests(unittest.TestCase):

    def test_fraction_day(self):

        from .models import Ride, Location
        from datetime import datetime, timedelta
        from pytz import timezone

        melbourne=Location(
            name='Melbourne',
            lat=28.084,
            lon=-80.608)

        satellite_beach=Location(
            name='Satellite Beach',
            lat=28.176,
            lon=-80.5901)

        self.assertAlmostEqual(
            Ride(start_time=datetime(
                2016,8,20,10,15,
                tzinfo=timezone('America/Detroit')),
                 end_time=datetime(
                     2016,8,20,10,45,
                     tzinfo=timezone('America/Detroit')),
                 startloc=melbourne,
                 endloc=satellite_beach).fraction_day
            ,
            1
        )

        self.assertAlmostEqual(
            Ride(start_time=datetime(
                2016,8,20,10,15,
                tzinfo=timezone('America/Detroit')),
                 end_time=datetime(
                     2016,8,22,10,45,
                     tzinfo=timezone('America/Detroit')),
                 startloc=melbourne,
                 endloc=satellite_beach).fraction_day
            ,
            0.5454636626
        )

        self.assertAlmostEqual(
            Ride(start_time=datetime(
                2016,8,20,2,30,
                tzinfo=timezone('America/Detroit')),
                 end_time=datetime(
                     2016,8,20,3,30,
                     tzinfo=timezone('America/Detroit')),
                 startloc=melbourne,
                 endloc=satellite_beach).fraction_day,
            0
        )

        self.assertIsNone(
            Ride(start_time=datetime(
                2016,8,20,2,30,
                tzinfo=timezone('America/Detroit')),
                 end_time=datetime(
                     2016,8,19,3,30,
                     tzinfo=timezone('America/Detroit')),
                 startloc=melbourne,
                 endloc=satellite_beach).fraction_day
        )

class RideViewTests(BaseTest):

    def setUp(self):
        super(RideViewTests, self).setUp()
        self.init_database()

        from .models import Ride

        from datetime import datetime,timedelta
        ride = Ride(
            start_time=datetime(2005,1,1,10),
            end_time=datetime(2005,1,1,10,15),
            total_time=timedelta(minutes=15),
            rolling_time=timedelta(minutes=12),
            distance=7,
            odometer=357,
            avspeed=28,
            maxspeed=40,
            equipment_id=0,
            ridergroup_id=0,
            surface_id=0
        )
        self.session.add(ride)
        self.ride=ride

        self.ride_null_total_time=Ride(
            start_time=datetime(2005,1,1,10),
            end_time=datetime(2005,1,1,10,15),
            total_time=None,
            rolling_time=timedelta(minutes=12),
            distance=7,
            odometer=357,
            avspeed=28,
            maxspeed=40,
            equipment_id=0,
            ridergroup_id=0,
            surface_id=0
        )
        self.session.add(self.ride_null_total_time)
        self.session.flush()

    def test_ride_details(self):
        from .views.rides import RideViews

        request=dummy_request(self.session)
        request.matchdict['ride_id']=self.ride_null_total_time.id

        views=RideViews(request)

        response=views.ride_table()

    def test_ride_table(self):
        from .views.rides import RideViews

        views=RideViews(dummy_request(self.session))
        info = views.ride_table()
        self.assertEqual(info['rides'].count(),2)
        self.assertEqual(info['page'].items_per_page,30)
        self.assertEqual(info['page'].page,1)

    def test_rides_scatter(self):
        from .views.rides import RideViews
        views=RideViews(dummy_request(self.session))
        from .models import Ride

        # Runnnig a query through sqlalchemy seems to be needed to let
        # pandas see the data in sqlite
        count=self.session.query(Ride).count()
        self.assertEqual(count,2)
        import transaction
        transaction.commit()

        info = views.rides_scatter()

class AuthenticationTests(BaseTest):

    def setUp(self):
        super(AuthenticationTests, self).setUp()
        self.init_database()

        from .models import User
        
        user=User(
            name='jhaiduce'
        )

        user.set_password('password')
        self.session.add(user)
        
    def test_check_password(self):
        from .models import User

        user=self.session.query(User).filter(User.name=='jhaiduce').one()

        self.assertTrue(user.check_password('password'))
        self.assertFalse(user.check_password('pa$$word'))

class SerializeTests(BaseTest):

    def setUp(self):
        super(SerializeTests, self).setUp()

        from .models.cycling_models import Ride, Location
        from .models.security import User

        from datetime import datetime, timedelta
        
        user=User(
            name='jhaiduce'
        )

        user.set_password('password')

        self.session.add(user)
        
        ride = Ride(
            start_time=datetime(2005,1,1,10),
            end_time=datetime(2005,1,1,10,15),
            total_time=timedelta(minutes=15),
            rolling_time=timedelta(minutes=12),
            distance=7,
            odometer=357,
            avspeed=28,
            maxspeed=40,
            equipment_id=0,
            ridergroup_id=0,
            surface_id=0
        )
        self.session.add(ride)

        self.init_database()

    def test_sqlalchemy_serialize(self):

        from .views.serialize import dump_backup, load_backup

        backup=dump_backup(self.session)

        self.assertEqual(len(backup['Ride']),1)
        self.assertEqual(len(backup['User']),1)
        self.assertEqual(len(backup['Equipment']),0)

        loaded_data=load_backup(backup)

        for class_name in backup.keys():
            self.assertEqual(len(backup[class_name]),
                             len(loaded_data[class_name]))

            for instance in loaded_data[class_name]:
                self.session.merge(instance)

        from .models.cycling_models import Ride, Location
        from .models.security import User

        test_classes={'Ride':Ride,'Location':Location,'User':User}

        for class_name,cls in test_classes.items():
            
            query=self.session.query(cls)
            self.assertEqual(query.count(),len(backup[class_name]))

class MetarTests(BaseTest):

    ogimet_text_dca_21jul = """

##########################################################
# Query made at 05/16/2021 18:08:45 UTC
# Time interval: from 07/21/2020 19:00  to 07/22/2020 04:32  UTC
##########################################################

##########################################################
# KDCA, Washington DC, Reagan National Airport (United States)
# WMO index: 72405
# Latitude 38-50-54N. Longitude 077-02-03W. Altitude 4 m.
##########################################################

###################################
#  METAR/SPECI from KDCA
###################################
202007211952 METAR KDCA 211952Z 17005KT 10SM FEW055 SCT250 36/20 A2998 RMK AO2 SLP151 T03560200=
202007212052 METAR KDCA 212052Z 14005KT 10SM FEW060 SCT250 36/21 A2997 RMK AO2 SLP147 T03560211 58017=
202007212152 METAR KDCA 212152Z 15008KT 10SM FEW065 BKN170 BKN250 35/22 A2995 RMK AO2 SLP142 T03500222=
202007212252 METAR KDCA 212252Z 16008KT 10SM R01/5500VP6000FT TS FEW065CB BKN075 BKN180 BKN250 33/21 A2997 RMK AO2 LTG DSNT S-W TSB28 SLP148 FRQ LTGICCG VC S-SW TS S-SW MOV NE T03330211=
202007212352 METAR KDCA 212352Z VRB05KT 10SM TS SCT036CB SCT080 SCT120 BKN250 26/22 A3002 RMK AO2 WSHFT 2256 LTG DSNT ALQDS RAB2258E33 TSE37B45 PRESRR SLP167 OCNL LTGICCG VC NW-NE FRQ LTGICCG DSNT SE-SW CB VC NW-NE AND S-SW MOV E P0000 600=
202007220052 METAR KDCA 220052Z 00000KT 1SM R01/4500VP6000FT +TSRA BR BKN028CB BKN047 OVC060 24/22 A3003 RMK AO2 LTG DSNT ALQDS RAB24 TSE07B22 SLP169 FRQ LTGICCG ALQDS TS ALQDS MOV E P0038 T02440222=
202007220152 METAR KDCA 220152Z 22006KT 10SM FEW050 BKN110 BKN250 25/23 A3005 RMK AO2 LTG DSNT E-SW RAE21 TSE16 SLP176 OCNL LTGICCG DSNT NE-SE AND SW-NW CB DSNT NE-SE AND SW-NW MOV E P0008 T02500233=
202007220252 METAR KDCA 220252Z 18008KT 10SM -RA FEW110 BKN140 OVC250 25/23 A3002 RMK AO2 RAB15 SLP166 P0002 60048 T02500228 58001=
202007220352 METAR KDCA 220352Z 00000KT 10SM FEW075 SCT120 OVC250 25/23 A3004 RMK AO2 RAE51 SLP171 P0004 T02500228=
"""

    ogimet_text_dca = """##########################################################
# Query made at 01/19/2020 16:18:32 UTC
# Time interval: from 01/01/2005 10:00  to 01/01/2005 19:11  UTC
##########################################################

##########################################################
# KDCA, Washington DC, Reagan National Airport (United States)
# WMO index: 72405
# Latitude 38-50-54N. Longitude 077-02-03W. Altitude 4 m.
##########################################################

###################################
#  METAR/SPECI from KDCA
###################################
200501011051 METAR KDCA 011051Z 20007KT 5SM BR SCT250 04/03 A3031 RMK
                        AO2 SLP261 T00390028=
200501011151 METAR KDCA 011151Z 22003KT 6SM BR BKN250 04/03 A3034 RMK
                        AO2 SLP273 T00440033 10094 20033
                        53013=
200501011251 METAR KDCA 011251Z 00000KT 6SM BR BKN150 BKN250 03/02 A3035
                        RMK AO2 SLP277 T00330022=
200501011351 METAR KDCA 011351Z 20006KT 7SM BKN150 BKN250 06/04 A3037
                        RMK AO2 SLP284 T00610044=
200501011451 METAR KDCA 011451Z 19010KT 7SM FEW150 BKN250 08/05 A3039
                        RMK AO2 SLP292 T00830050 53019=
200501011551 METAR KDCA 011551Z 19009KT 7SM SCT150 BKN250 11/06 A3039
                        RMK AO2 SLP291 T01060061=
200501011651 METAR KDCA 011651Z 18009KT 10SM FEW020 BKN250 13/07 A3037
                        RMK AO2 SLP283 T01280067=
200501011751 METAR KDCA 011751Z 33008KT 10SM FEW030 SCT250 20/08 A3035
                        RMK AO2 SLP276 T02000083 10200 20033
                        58016=
200501011851 METAR KDCA 011851Z 31012G18KT 10SM FEW040 BKN250 20/08 A3035
                        RMK AO2 SLP276 T02000078=

"""

    mock_ogimet_response=Mock()
    mock_ogimet_response.text=ogimet_text_dca
    mock_ogimet_response.url='https://ogimet.com/display_metars2.php'
    mock_ogimet_response.status_code=200
    
    ogimet_text_quota_exceeded="""#Sorry, Your quota limit for slow queries rate has been reached"""

    ride_average_weather={'windspeed': 11.269047352721849, 'winddir': 190.0, 'temperature': 8.809170907242839, 'gust': None, 'dewpoint': 5.229166666666665, 'relative_humidity': 0.7822210166871647, 'rain': 0.0, 'snow': 0.0, 'pressure': 1027.706784398859}

    def setUp(self):
        super(MetarTests, self).setUp()

        from .models.cycling_models import Ride, Location
        from .models.security import User

        from datetime import datetime, timedelta
        
        self.init_database()

    @patch('cycling_data.processing.regression.train_model.delay')
    @patch('cycling_data.celery.session_factory')
    @patch('cycling_data.processing.weather.fetch_metars',return_value=mock_ogimet_response)
    def test_fetch_metars_for_ride(self,fetch_metars,session_factory,train_model):

        from .processing.weather import fetch_metars_for_ride, update_ride_weather
        from .models import Ride, Location
        from .models.cycling_models import RideWeatherData

        from datetime import datetime, timedelta
        from .models import get_session_factory

        sessionmaker=get_session_factory(self.engine)

        session=sessionmaker()

        session_factory.return_value=session

        washington_monument=Location(
                name='Washington Monument',
                lat=38.88920847908595,
                lon=-77.03452329465938,
                elevation=9.911861419677734
            )
        us_capitol=Location(
                name='US Capitol',
                lat=38.889794641870104,
                lon=-77.0102077819937,
                elevation=12.86381340026855
        )

        new_intersection=Location(
                name='New intersection'
        )

        dca=Location(
            name='KDCA',
            lat=38.86,
            lon=-77.03,
            elevation=16.076,
            loctype_id=2
        )
        bwi=Location(
            name='KBWI',
            lat=39.19,
            lon=-76.67,
            elevation=147.966,
            loctype_id=2
        )
        
        ride = Ride(
            start_time=datetime(2005,1,1,10),
            end_time=datetime(2005,1,1,10,15),
            startloc=washington_monument,
            endloc=us_capitol
        )
        ride_with_incomplete_endpoint = Ride(
            start_time=datetime(2005,1,1,10),
            end_time=datetime(2005,1,1,10,15),
            startloc=washington_monument,
            endloc=new_intersection
        )
        ride_that_produces_negative_windspeed = Ride(
            start_time=datetime(2020,7,21,18,55),
            end_time=datetime(2020,7,21,19,36),
            startloc=washington_monument,
            endloc=us_capitol
        )
        session.add(ride)
        session.add(ride_with_incomplete_endpoint)
        session.add(ride_that_produces_negative_windspeed)
        session.add(dca)
        session.add(bwi)
        session.commit()
        
        locations=self.session.query(Location)

        window_expansion=timedelta(seconds=3600*4)

        from cycling_data.processing.weather import ride_times_utc
        dtstart,dtend=ride_times_utc(ride)

        metars=fetch_metars_for_ride(session,ride)
        
        self.assertEqual(metars[0].station.name,'KDCA')
        fetch_metars.assert_called_with(
           'KDCA',
           dtstart-window_expansion,
           dtend+window_expansion,
           url='https://www.ogimet.com/display_metars2.php'
        )

        self.session.expire_on_commit=False

        mock_ogimet_response=Mock()
        mock_ogimet_response.text=MetarTests.ogimet_text_dca_21jul
        mock_ogimet_response.url='https://ogimet.com/display_metars2.php'
        mock_ogimet_response.status_code=200

        from .processing import weather

        with patch.object(weather,'fetch_metars', return_value=mock_ogimet_response) as fetch_metars_21jul:
            metars=fetch_metars_for_ride(session,ride_that_produces_negative_windspeed)

            update_ride_weather(ride_that_produces_negative_windspeed.id)

        self.assertGreater(ride_that_produces_negative_windspeed.wxdata.windspeed,0)

        from time import sleep
        sleep(1)
        
        update_ride_weather(ride.id)

        fetch_metars.assert_called_with(
            'KDCA',
            dtstart-window_expansion,
            dtend+window_expansion,
            url='https://www.ogimet.com/display_metars2.php'
        )

        train_model.assert_called()

        for key in MetarTests.ride_average_weather.keys():
            self.assertEqual(getattr(ride.wxdata,key),
                             MetarTests.ride_average_weather[key],
                             'Discrepancy for key {}'.format(key))
            query=self.session.query(RideWeatherData).with_entities(
                    getattr(RideWeatherData,key)
            ).filter(RideWeatherData.id==ride.wxdata_id)
            self.assertEqual(
                getattr(query.one(),key),
                MetarTests.ride_average_weather[key])

        # Reset call info for fetch_metars mock
        fetch_metars.reset_mock()

        # Update ride weather for ride without coordinate data for an endpoint
        update_ride_weather(ride_with_incomplete_endpoint.id)

        # Without coordinates, fetch_metars should not be called
        fetch_metars.assert_not_called()

class ModelTests(BaseTest):

    rideCount=50
    locationCount=5

    def setUp(self):
        super(ModelTests, self).setUp()
        self.init_database()

        from .models.cycling_models import Ride, Location, RideWeatherData, RiderGroup, SurfaceType, Equipment
        import random

        random.seed(100)

        locations=[]
        for i in range(self.locationCount):
            location=Location(
                name='Location {}'.format(i),
                lat=random.gauss(28.084,0.05),
                lon=random.gauss(-80.5901,0.05),
                elevation=100*random.lognormvariate(0,1)
            )
            locations.append(location)
            self.session.add(location)

        self.session.flush()

        self.session.add(RiderGroup(id=1,name='Solo'))
        self.session.add(SurfaceType(id=1,name='Pavement'))
        self.session.add(Equipment(id=1,name='Bike'))

        lastloc=random.choice(locations)
        odo=0
        for i in range(self.rideCount):
            start_time=datetime(2005,1,1,tzinfo=timezone('America/Detroit')) \
                + timedelta(
                    seconds=random.random()*24*365*3600*20)
            end_time=start_time+timedelta(
                seconds=1800*random.lognormvariate(0,1))
            distance=random.lognormvariate(0,1)*10
            odo+=distance
            temperature=random.gauss(25,5)
            ride = Ride(
                startloc=random.choice(locations),
                endloc=random.choice(locations),
                start_time=start_time,
                end_time=end_time,
                total_time=end_time-start_time,
                rolling_time=(end_time-start_time)*0.9,
                avspeed=random.gauss(18,8),
                maxspeed=random.gauss(30,8),
                distance=distance,
                odometer=odo,
                equipment_id=1,
                ridergroup_id=1,
                surface_id=1,
                wxdata=RideWeatherData(
                    temperature=temperature,
                    dewpoint=temperature-random.uniform(0,10),
                    winddir=random.uniform(0,360),
                    windspeed=5*random.lognormvariate(0,1),
                    pressure = random.gauss(1000,10),
                    rain=0,
                    snow=0
                )
            )

            self.session.add(ride)

        ride_null_total_time=Ride(
            start_time=datetime(2005,1,1,20),
            end_time=datetime(2005,1,1,20,15),
            startloc=locations[0],
            endloc=locations[1],
            total_time=None,
            rolling_time=timedelta(seconds=60*12),
            distance=7,
            odometer=357,
            avspeed=28,
            maxspeed=40,
            equipment_id=0,
            ridergroup_id=0,
            surface_id=0,
            wxdata=RideWeatherData(
                temperature=22,
                dewpoint=12,
                winddir=250,
                windspeed=12,
                pressure = 1050,
                rain=0,
                snow=0
            )
        )
        self.session.add(ride_null_total_time)
        self.rideCount+=1

        self.useable_ride_count=self.rideCount

        ride_null_end_time=Ride(
            start_time=datetime(2005,1,1,10),
            end_time=None,
            total_time=timedelta(minutes=15),
            rolling_time=None,
            distance=7,
            odometer=357,
            avspeed=28,
            maxspeed=40,
            equipment_id=0,
            ridergroup_id=0,
            surface_id=0
        )
        self.session.add(ride_null_end_time)
        self.rideCount+=1

        transaction.commit()

    def test_train_model(self):

        from .processing.regression import train_model
        from .models.cycling_models import Ride, PredictionModel
        from . import models
        from . import celery
        from .models import get_session_factory, get_tm_session
        from .models.prediction import prepare_model_dataset
        import numpy as np

        transaction.commit()

        session_factory=get_session_factory(self.engine)
        session=session_factory()

        with patch.object(
                celery,'session_factory',
                return_value=session) as session_factory:
            train_dataset_size=train_model(epochs=10)

        self.assertEqual(train_dataset_size,self.useable_ride_count)

        with transaction.manager:
            rides=session.query(Ride)
            dataset=prepare_model_dataset(rides,session,['avspeed'])
            dataset=dataset.drop(columns=['id'])

        with transaction.manager:
            model=session.query(PredictionModel).one()
            weights=model.model.get_weights()

            self.assertIsNotNone(model.weightsbuf)

            dataset_copy=dataset.copy()
            normed_data=model.norm(dataset)
            predictions=model.predict(dataset)
            stats=model.stats

            num_outputs=3

            self.assertEqual(dataset.dropna().shape[0],dataset_copy.dropna().shape[0])
            self.assertEqual(dataset.dropna().shape[0],self.useable_ride_count)
            self.assertTrue(np.allclose(dataset.dropna(),dataset_copy.dropna()))
            for a,b in zip(weights,model.model.get_weights()):
                self.assertTrue(np.allclose(a,b))
            self.assertEqual(predictions.shape,(self.rideCount,num_outputs))
            self.assertEqual(np.isnan(predictions).sum(),num_outputs)
            predictions_new=model.predict(dataset)
            normed_data_new=model.norm(dataset)
            self.assertEqual(np.sum(np.isfinite(predictions)),self.useable_ride_count*num_outputs)
            self.assertEqual(np.sum(np.isfinite(predictions_new)),self.useable_ride_count*num_outputs)
            self.assertTrue(np.allclose(stats,model.stats))
            self.assertTrue(np.allclose(
                normed_data_new.drop(columns=['avspeed']).dropna(),
                normed_data.drop(columns=['avspeed']).dropna()))
            self.assertTrue(np.allclose(dataset.dropna(),dataset_copy.dropna()))
            self.assertTrue(np.allclose(predictions_new[np.isfinite(predictions_new)],predictions[np.isfinite(predictions)]))

            from .models.prediction import get_ride_predictions

            # Check that get_ride_predictions returns the same results
            ride_predictions=get_ride_predictions(session,rides)
            self.assertEqual(np.sum(np.isfinite(predictions)),self.useable_ride_count*num_outputs)
            self.assertEqual(np.sum(np.isfinite(ride_predictions)),self.useable_ride_count*num_outputs)
            self.assertEqual(ride_predictions.shape,(self.rideCount,num_outputs))
            self.assertTrue(np.allclose(predictions[np.isfinite(predictions)],
                                        ride_predictions[np.isfinite(ride_predictions)]))
            single_prediction=get_ride_predictions(session,[session.query(Ride).first()])
            self.assertEqual(single_prediction.shape,(1,num_outputs))
            self.assertTrue(np.allclose(single_prediction[0],ride_predictions[0]))
import webtest

class FunctionalTests(unittest.TestCase):
    admin_login = dict(login='admin', password='admin')

    def setUp(self):
        """
        Add some dummy data to the database.
        Note that this is a session fixture that commits data to the database.
        Think about it similarly to running the ``initialize_db`` script at the
        start of the test suite.
        This data should not conflict with any other data added throughout the
        test suite or there will be issues - so be careful with this pattern!
        """

        from . import main

        from .models import (
            get_engine,
            get_session_factory,
            get_tm_session,
            )

        self.config={
            'admin_password':self.admin_login['password'],
            'sqlalchemy.url':'sqlite://',
            'auth.secret':'secret'
            }

        self.app = main({}, **self.config)
        self.init_database()
        self.testapp=webtest.TestApp(self.app)

    def get_session(self):
        from .models import get_session_factory,get_tm_session
        session_factory = self.app.registry['dbsession_factory']
        session=get_tm_session(session_factory,transaction.manager)
        return session

    def init_database(self):

        session=self.get_session()

        from . import models

        models.Base.metadata.create_all(session.bind)

        user=models.User(
            name='admin'
        )

        user.set_password(self.config['admin_password'])
        session.add(user)

        from datetime import datetime,timedelta
        ride = models.Ride(
            start_time=datetime(2005,1,1,10),
            end_time=datetime(2005,1,1,10,15),
            total_time=timedelta(minutes=15),
            rolling_time=timedelta(minutes=12),
            distance=7,
            odometer=357,
            avspeed=28,
            maxspeed=40,
            equipment_id=0,
            ridergroup_id=0,
            surface_id=0
        )
        session.add(ride)
        
        ride_null_total_time=models.Ride(
            start_time=datetime(2005,1,1,10),
            end_time=datetime(2005,1,1,10,15),
            total_time=None,
            rolling_time=timedelta(minutes=12),
            distance=7,
            odometer=357,
            avspeed=28,
            maxspeed=40,
            equipment_id=0,
            ridergroup_id=0,
            surface_id=0
        )
        session.add(ride_null_total_time)
        session.flush()
        self.ride_id=ride.id
        self.ride_null_total_time_id=ride_null_total_time.id
        transaction.commit()

        ride_null_rolling_time=models.Ride(
            start_time=datetime(2005,1,1,10),
            end_time=datetime(2005,1,1,10,15),
            total_time=timedelta(minutes=15),
            rolling_time=None,
            distance=7,
            odometer=357,
            avspeed=28,
            maxspeed=40,
            equipment_id=0,
            ridergroup_id=0,
            surface_id=0
        )
        session.add(ride_null_rolling_time)
        session.flush()
        self.ride_null_rolling_time_id=ride_null_rolling_time.id
        transaction.commit()

        ride_null_end_time=models.Ride(
            start_time=datetime(2005,1,1,10),
            end_time=None,
            total_time=timedelta(minutes=15),
            rolling_time=None,
            distance=7,
            odometer=357,
            avspeed=28,
            maxspeed=40,
            equipment_id=0,
            ridergroup_id=0,
            surface_id=0
        )
        session.add(ride_null_end_time)
        session.flush()
        self.ride_null_end_time_id=ride_null_end_time.id
        transaction.commit()

    def login(self):
        res=self.testapp.post('http://localhost/login',{**self.admin_login,'form.submitted':'true'})

    def test_successful_login(self):
        res=self.testapp.post('http://localhost/login',{**self.admin_login,'form.submitted':'true'})

        # Verify that we got redirected to the default page
        self.assertEqual(res.status_code,302)
        self.assertEqual(res.location,'http://localhost/rides')

        # Verify that we can load a page
        res=self.testapp.get('http://localhost/rides')
        self.assertEqual(res.status_code,200)

    def test_failed_login(self):

        # Try to login with wrong password
        res=self.testapp.post('http://localhost/login',{'login':'admin','password':'wrong_password','form.submitted':'true'})
        
        # Verify that we stay at the login page with a "Failsed login" message
        self.assertEqual(res.status_code,200)
        self.assertTrue(isinstance(re.search('Failed login',res.text),re.Match))

        # Verify that attempts to access restricted content are
        # redirected to the login page with the request URL passed
        # in the GET data
        res=self.testapp.get('http://localhost/rides')
        self.assertEqual(res.status_code,302)
        self.assertEqual(res.location,'http://localhost/login?next=http%3A%2F%2Flocalhost%2Frides')

    def test_rides_table(self):
        self.login()
        res=self.testapp.get('http://localhost/rides')
        self.assertEqual(res.status_code,200)
        ride_count=int(re.search(r'(\d+) total rides',res.text).group(1))
        self.assertEqual(ride_count,4)

    @patch(
        'cycling_data.models.prediction.get_ride_predictions',
        return_value=np.array([[19.4]])
    )
    def test_ride_details(self,get_ride_predictions):
        self.login()
        from .models import Ride
        session=self.get_session()
        url='http://localhost/rides/{}/details'.format(self.ride_id)
        ride=session.query(Ride).filter(Ride.id==self.ride_id).one()
        res=self.testapp.get(url)
        get_ride_predictions.assert_called()
        self.assertEqual(res.status_code,200)

        url='http://localhost/rides/{}/details'.format(self.ride_null_rolling_time_id)
        ride=session.query(Ride).filter(Ride.id==self.ride_null_rolling_time_id).one()
        res=self.testapp.get(url)
        get_ride_predictions.assert_called()
        self.assertEqual(res.status_code,200)

        url='http://localhost/rides/{}/details'.format(self.ride_null_end_time_id)
        ride=session.query(Ride).filter(Ride.id==self.ride_null_end_time_id).one()
        res=self.testapp.get(url)
        get_ride_predictions.assert_called()
        self.assertEqual(res.status_code,200)

    @patch(
        'cycling_data.processing.weather.update_ride_weather.delay',
        return_value=mock_task_result)
    def test_ride_addedit(self,update_ride_weather):
        self.login()
        from .models import Ride
        session=self.get_session()
        add_url='http://localhost/rides/add'
        edit_url='http://localhost/rides/{}/edit'
        res=self.testapp.post(
            add_url,
            params=dict_to_postdata(dict(
                start_time={'date':'2005-01-01', 'time':'10:00:00'},
                end_time={'date':'2005-01-01','time':'10:15:00'},
                total_time=str(15*60),
                rolling_time=str(12*60),
                distance='7',
                odometer='357',
                avspeed='28',
                maxspeed='40',
                equipment='0',
                ridergroup='0',
                surface='0',
                submit='submit',
                startloc='Home',
                endloc='Work'
            ))
        )
        self.assertEqual(res.status_code,302)
        created_ride_id=json.loads(res.text)['ride_id']
        created_ride=session.query(Ride).filter(Ride.id==created_ride_id).one()
        update_ride_weather.assert_called_with(created_ride_id)
        self.assertEqual(created_ride.equipment_id,0)
        self.assertEqual(created_ride.surface_id,0)
        self.assertEqual(created_ride.startloc.name,'Home')
        self.assertEqual(created_ride.endloc.name,'Work')
        self.assertEqual(created_ride.total_time,timedelta(minutes=15))
        self.assertEqual(created_ride.rolling_time,timedelta(minutes=12))
        self.assertEqual(created_ride.start_time,
                         datetime(2005,1,1,10,
                                  tzinfo=created_ride.start_time.tzinfo))
        self.assertEqual(created_ride.end_time,
                         datetime(
                             2005,1,1,10,15,
                             tzinfo=created_ride.end_time.tzinfo))
        res=self.testapp.get(
            edit_url.format(created_ride.id)
            )

        self.assertEqual(res.status_code,200)
        update_ride_weather.assert_called_with(created_ride_id)

        res=self.testapp.post(
            add_url,
            params=dict_to_postdata(dict(
                start_time={'date':'2005-01-01','time':'10:00:00'},
                end_time={'date':'2005-01-01','time':'10:15:00'},
                total_time='',
                rolling_time=str(12*60),
                distance='7',
                odometer='357',
                avspeed='28',
                maxspeed='40',
                equipment='0',
                ridergroup='0',
                surface='0',
                submit='submit',
                startloc='Home',
                endloc='Work'
            ))
        )
        self.assertEqual(res.status_code,302)
        created_ride_id=json.loads(res.text)['ride_id']
        created_ride=session.query(Ride).filter(Ride.id==created_ride_id).one()
        update_ride_weather.assert_called_with(created_ride_id)
        self.assertEqual(created_ride.equipment_id,0)
        self.assertEqual(created_ride.surface_id,0)
        self.assertEqual(created_ride.startloc.name,'Home')
        self.assertEqual(created_ride.endloc.name,'Work')
        self.assertEqual(created_ride.total_time,None)
        self.assertEqual(created_ride.rolling_time,timedelta(minutes=12))
        self.assertEqual(created_ride.start_time,
                         datetime(
                             2005,1,1,10,
                             tzinfo=created_ride.start_time.tzinfo))
        self.assertEqual(created_ride.end_time,
                         datetime(
                             2005,1,1,10,15,
                             tzinfo=created_ride.end_time.tzinfo))

        res=self.testapp.get(
            edit_url.format(created_ride.id)
            )

        self.assertEqual(res.status_code,200)

    def test_equipment_table(self):
        self.login()
        res=self.testapp.get('http://localhost/equipment/list')
        self.assertEqual(res.status_code,200)
        count=int(re.search(r'(\d+) total',res.text).group(1))
        self.assertGreaterEqual(count,0)

    def test_locations_table(self):
        self.login()
        res=self.testapp.get('http://localhost/locations/list')
        self.assertEqual(res.status_code,200)
        count=int(re.search(r'(\d+) total locations',res.text).group(1))
        self.assertGreaterEqual(count,0)

    @patch(
        'cycling_data.processing.weather.update_location_rides_weather.delay',
        return_value=mock_task_result)
    def test_location_addedit(self,update_location_rides):
        import json
        from .models import Location

        self.login()
        session=self.get_session()

        res=self.testapp.post(
            'http://localhost/locations/add',
            params=dict_to_postdata(dict(
                name='New Location',
                coordinates=dict(
                    lat=str(42.479703643392526),
                    lon=str(-83.11677199999998),
                    elevation=str(193.9267883300781)),
                loctype=1,
                submit='submit'
            ))
        )
        self.assertEqual(res.status_code,302)
        created_location_id=json.loads(res.text)['location_id']
        created_location=session.query(Location).filter(Location.id==created_location_id).one()

        self.assertEqual(created_location.name,'New Location')
        self.assertAlmostEqual(created_location.lat,42.479703643392526)
        self.assertAlmostEqual(created_location.lon,-83.11677199999998)
        self.assertAlmostEqual(created_location.elevation,193.9267883300781)

        res=self.testapp.post(
            'http://localhost/locations/{}/edit'.format(created_location_id),
            params=dict_to_postdata(dict(
                name='New Location 1',
                coordinates=dict(
                    lat=str(42.0),
                    lon=str(-83.0),
                    elevation=str(195.7)),
                loctype=1,
                submit='submit'
            ))
        )
        self.assertEqual(res.status_code,302)
        update_location_rides.assert_called_with(created_location_id)

        created_location=session.query(Location).filter(Location.id==created_location_id).one()

        self.assertEqual(created_location.name,'New Location 1')
        self.assertAlmostEqual(created_location.lat,42.0)
        self.assertAlmostEqual(created_location.lon,-83.0)
        self.assertAlmostEqual(created_location.elevation,195.7)
