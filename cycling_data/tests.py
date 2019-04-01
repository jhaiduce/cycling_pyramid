import unittest

from pyramid import testing

import transaction


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

    def test_ride_table(self):
        from .views.rides import RideViews

        views=RideViews(dummy_request(self.session))
        info = views.ride_table()
        self.assertEqual(info['rides'].count(),1)
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
