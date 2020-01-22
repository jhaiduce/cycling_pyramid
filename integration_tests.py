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

    def tearDown(self):
        resp=self.session.post('http://cycling_test_cycling_web/logout')
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://cycling_test_cycling_web/rides')
        
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://cycling_test_cycling_web/login?next=http%3A%2F%2Fcycling_test_cycling_web%2Frides')
