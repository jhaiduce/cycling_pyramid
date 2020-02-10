import unittest
from unittest.mock import patch
import requests
import configparser
import json
from cycling_data.celery import celery
from celery import Celery
import re

class BaseTest(unittest.TestCase):

    def setUp(self):
        self.session=requests.Session()

        self.config=configparser.ConfigParser()
        self.config.read('/run/secrets/production.ini')

        self.admin_password=self.config['app:main']['admin_password']

        while True:
            try:
                resp=self.session.post('http://cycling_test_cycling_web/login',data={
                    'login':'admin',
                    'password':self.admin_password,
                    'form.submitted':'Log+In'
                })
                break
            except requests.exceptions.ConnectionError:
                print('Connection failed. Sleeping before retry.')
                import time
                time.sleep(2)

        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://cycling_test_cycling_web/rides')

    def test_rides_list(self):
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        self.assertGreater(resp.text.find('total rides'),0)

    def test_ride_add(self):
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        ride_count=int(re.search(r'(\d+) total rides',resp.text).group(1))

        # Add locations for ride
        resp=self.session.post(
            'http://cycling_test_cycling_web/locations/add',
            data=dict(
                name='Home',
                __start__='coordinates:mapping',
                lat='42.397',
                lon='-83.095',
                elevation='198',
                __end__='coordinates:mapping',
                description='',
                remarks='',
                loctype='1',
                submit='submit'
            ))

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        resp=self.session.post(
            'http://cycling_test_cycling_web/locations/add',
            data=dict(
                name='Work',
                __start__='coordinates:mapping',
                lat='42.509',
                lon='-83.233',
                elevation='198',
                __end__='coordinates:mapping',
                description='',
                remarks='',
                loctype='1',
                submit='submit'
            ))

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        resp=self.session.post(
            'http://cycling_test_cycling_web/locations/add',
            data=dict(
                name='KDTW',
                __start__='coordinates:mapping',
                lat='42.231',
                lon='-83.331',
                elevation='192.3',
                __end__='coordinates:mapping',
                description='',
                remarks='',
                loctype='2',
                submit='submit'
            ))

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        resp=self.session.post(
            'http://cycling_test_cycling_web/locations/add',
            data=dict(
                name='KONZ',
                __start__='coordinates:mapping',
                lat='42.1',
                lon='-83.167',
                elevation='180.0',
                __end__='coordinates:mapping',
                description='',
                remarks='',
                loctype='2',
                submit='submit'
            ))

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        resp=self.session.post(
            'http://cycling_test_cycling_web/rides/add',
            data=dict(
                start_time='2005-01-01 10:00:00',
                end_time='2005-01-01 10:15:00',
                total_time='00:15:00',
                rolling_time='00:12:00',
                distance='7',
                odometer='357',
                avspeed='28',
                maxspeed='40',
                equipment_id='0',
                ridergroup_id='0',
                surface_id='0',
                submit='submit',
                startloc='Home',
                endloc='Work'
            )
        )

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        # Parse metadata sent with redirect response
        submission_metadata=json.loads(resp.history[0].text)
        ride_id=submission_metadata['ride_id']
        update_weather_task_id=submission_metadata['update_weather_task_id']

        # Check redirect URL
        self.assertEqual(
            resp.history[0].headers['Location'],
            'http://cycling_test_cycling_web/rides')

        # Check that the ride shows up in the rides table
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        ride_count_after=int(re.search(r'(\d+) total rides',resp.text).group(1))

        # Wait for update_ride_weather task to complete
        from celery.result import AsyncResult
        task_result=AsyncResult(update_weather_task_id,app=celery)
        task_result.wait(10)

        # Check ride details page
        resp=self.session.get('http://cycling_test_cycling_web/rides/{:d}/details'.format(ride_id))
        self.assertEqual(resp.status_code,200)
        print(resp.text)
        p=int(re.search(r'<td>(\d+) Pa</td>',resp.text).group(1))
        self.assertGreater(p,1007)
        self.assertLess(p,1011)

        self.assertEqual(ride_count_after,ride_count+1)

    def tearDown(self):
        resp=self.session.post('http://cycling_test_cycling_web/logout')
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://cycling_test_cycling_web/rides')
        
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://cycling_test_cycling_web/login?next=http%3A%2F%2Fcycling_test_cycling_web%2Frides')

    def test_equipment_list(self):
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        equipment_count=int(re.search(r'(\d+) total',resp.text).group(1))
        self.assertGreaterEqual(equipment_count,0)

    def test_equipment_add(self):
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        equipment_count=int(re.search(r'(\d+) total rides',resp.text).group(1))

        resp=self.session.post(
            'http://cycling_test_cycling_web/rides/add',
            data=dict(
                name='Shiny new bike',
                submit='submit'
            )
        )

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        # Check that equipment was added to the list
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        equipment_count=int(re.search(r'(\d+) total',resp.text).group(1))
