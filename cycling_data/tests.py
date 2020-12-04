import unittest
from unittest.mock import patch, Mock

from pyramid import testing

import pytest

import transaction

import re

import json

from datetime import datetime, timedelta

from pytz import timezone, UTC

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
        self.session.query(Ride).count()

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
    
    ogimet_text_quota_exceeded="""#Sorry, Your quota limit for slow queries rate has been reached"""

    ride_average_weather={'windspeed': 11.404188732967256, 'winddir': 190.0, 'temperature': 8.539095149667082, 'gust': None, 'dewpoint': 5.1000000000000005, 'relative_humidity': 0.789787919515681, 'rain': 0.0, 'snow': 0.0, 'pressure': 1027.7054318855933}

    def setUp(self):
        super(MetarTests, self).setUp()

        from .models.cycling_models import Ride, Location
        from .models.security import User

        from datetime import datetime, timedelta
        
        self.init_database()

    @patch('cycling_data.models.get_tm_session')
    @patch('cycling_data.processing.weather.fetch_metars',return_value=ogimet_text_dca)
    def test_fetch_metars_for_ride(self,fetch_metars,get_tm_session):

        from .processing.weather import fetch_metars_for_ride, update_ride_weather
        from .models import Ride, Location

        from datetime import datetime, timedelta

        get_tm_session.return_value=self.session

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
        self.session.add(ride)
        self.session.add(dca)
        self.session.add(bwi)
        self.session.flush()
        
        locations=self.session.query(Location)

        window_expansion=timedelta(seconds=3600*4)

        from cycling_data.processing.weather import ride_times_utc
        dtstart,dtend=ride_times_utc(ride)
        
        metars=fetch_metars_for_ride(self.session,ride)
        
        self.assertEqual(metars[0].station.name,'KDCA')
        fetch_metars.assert_called_with(
            'KDCA',
            dtstart-window_expansion,
            dtend+window_expansion,
            url='https://www.ogimet.com/display_metars2.php'
        )

        self.session.expire_on_commit=False

        update_ride_weather(ride.id)
        
        fetch_metars.assert_called_with(
            'KDCA',
            dtstart-window_expansion,
            dtend+window_expansion,
            url='https://www.ogimet.com/display_metars2.php'
        )

        for key in MetarTests.ride_average_weather.keys():
            self.assertEqual(getattr(ride.wxdata,key),
                             MetarTests.ride_average_weather[key],
                             'Discrepancy for key {}'.format(key))

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
                lon=random.gauss(-80.5901,0.05))
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
                    relative_humidity=random.uniform(0,1),
                    rain=0,
                    snow=0
                )
            )

            self.session.add(ride)

        transaction.commit()

    def test_train_model(self):

        from .processing.regression import train_model
        from .models.cycling_models import Ride, PredictionModel
        from . import models
        from . import celery
        from .models import get_session_factory, get_tm_session
        from .models.prediction import prepare_model_dataset
        import numpy as np

        with patch.object(
                celery,'session_factory',
                wraps=get_session_factory(self.engine)) as session_factory:
            train_dataset_size=train_model(epochs=10)

        self.assertEqual(train_dataset_size,self.rideCount)

        with transaction.manager:
            session=get_tm_session(get_session_factory(self.engine),transaction.manager)
            rides=session.query(Ride)
            dataset=prepare_model_dataset(rides,session,['avspeed'])

        with transaction.manager:
            session=get_tm_session(get_session_factory(self.engine),transaction.manager)
            model=session.query(PredictionModel).one()
            weights=model.model.get_weights()

            self.assertIsNotNone(model.weightsbuf)

            dataset_copy=dataset.copy()
            normed_data=model.norm(dataset)
            predictions=model.predict(dataset)
            stats=model.stats
            self.assertTrue(np.allclose(dataset,dataset_copy))
            for a,b in zip(weights,model.model.get_weights()):
                self.assertTrue(np.allclose(a,b))
            self.assertEqual(predictions.shape,(self.rideCount,1))
            self.assertEqual(np.isnan(predictions).sum(),0)
            predictions_new=model.predict(dataset)
            normed_data_new=model.norm(dataset)
            self.assertTrue(np.allclose(stats,model.stats))
            self.assertTrue(np.allclose(
                normed_data_new.drop(columns=['avspeed']),
                normed_data.drop(columns=['avspeed'])))
            self.assertTrue(np.allclose(dataset,dataset_copy))
            self.assertTrue(np.allclose(predictions_new,predictions))

            from .models.prediction import get_ride_predictions

            # Check that get_ride_predictions returns the same results
            ride_predictions=get_ride_predictions(session,rides)
            self.assertEqual(ride_predictions.shape,(self.rideCount,1))
            self.assertTrue(np.allclose(predictions,ride_predictions))
            single_prediction=get_ride_predictions(session,[session.query(Ride).first()])
            self.assertEqual(single_prediction.shape,(1,1))
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
        self.assertEqual(ride_count,2)

    @patch(
        'cycling_data.models.prediction.get_ride_predictions',
        return_value={'avspeed':19.4}
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

    @patch(
        'cycling_data.processing.regression.train_model.delay',
        return_value=mock_task_result)
    @patch(
        'cycling_data.processing.weather.update_ride_weather.delay',
        return_value=mock_task_result)
    def test_ride_addedit(self,update_ride_weather,train_model):
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
        train_model.assert_called()
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
        train_model.assert_called()
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
        train_model.assert_called()
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
