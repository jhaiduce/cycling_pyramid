import unittest
from unittest.mock import patch
import requests
import configparser

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
        import re
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        ride_count=int(re.search(r'(\d+) total rides',resp.text).group(1))

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

        resp=self.session.get('http://cycling_test_cycling_web/rides')
        ride_count_after=int(re.search(r'(\d+) total rides',resp.text).group(1))

        self.assertEqual(ride_count_after,ride_count+1)

    def tearDown(self):
        resp=self.session.post('http://cycling_test_cycling_web/logout')
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://cycling_test_cycling_web/rides')
        
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://cycling_test_cycling_web/login?next=http%3A%2F%2Fcycling_test_cycling_web%2Frides')
