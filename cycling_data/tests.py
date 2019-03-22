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
