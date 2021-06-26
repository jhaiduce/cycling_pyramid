import unittest
from unittest.mock import patch
import requests
import configparser
import json
from cycling_data.celery import celery
from celery import Celery
import re

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
                name='Church',
                __start__='coordinates:mapping',
                lat='',
                lon='',
                elevation='',
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

        # Post the ride
        resp=self.session.post(
            'http://cycling_test_cycling_web/rides/add',
            data=dict_to_postdata(dict(
                start_time={'date':'2005-01-01','time':'10:00:00'},
                end_time={'date':'2005-01-01','time':'10:15:00'},
                total_time=str(15*60),
                rolling_time=str(12*60),
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
            ))
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

        # Make sure we can load the ride details page
        resp=self.session.get('http://cycling_test_cycling_web/rides/{:d}/details'.format(ride_id))
        self.assertEqual(resp.status_code,200)

        # Wait for update_ride_weather task to complete
        from celery.result import AsyncResult
        task_result=AsyncResult(update_weather_task_id,app=celery)
        task_result.wait(40)

        # Check the weather data in the ride details page
        resp=self.session.get('http://cycling_test_cycling_web/rides/{:d}/details'.format(ride_id))
        self.assertEqual(resp.status_code,200)
        p=int(re.search(r'<td>(\d+) Pa</td>',resp.text).group(1))
        self.assertGreater(p,1007)
        self.assertLess(p,1011)

        self.assertEqual(ride_count_after,ride_count+1)

        # Post the ride
        resp=self.session.post(
            'http://cycling_test_cycling_web/rides/add',
            data=dict_to_postdata(dict(
                start_time={'date':'2005-01-01','time':'10:00:00'},
                end_time={'date':'2005-01-01','time':'10:15:00'},
                total_time=str(15*60),
                rolling_time=str(12*60),
                distance='7',
                odometer='357',
                avspeed='28',
                maxspeed='40',
                equipment_id='0',
                ridergroup_id='0',
                surface_id='0',
                submit='submit',
                startloc='Home',
                endloc='Church'
            ))
        )

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        # Parse metadata sent with redirect response
        submission_metadata=json.loads(resp.history[0].text)
        ride_id=submission_metadata['ride_id']
        update_weather_task_id=submission_metadata['update_weather_task_id']

        # Check that we can load the ride details page for the newly created ride
        resp=self.session.get('http://cycling_test_cycling_web/rides/{}/details'.format(ride_id))
        self.assertEqual(resp.status_code,200)

        # Wait for update_ride_weather task to complete
        from celery.result import AsyncResult
        task_result=AsyncResult(update_weather_task_id,app=celery)
        task_result.wait(40)

        # Check that we can load the ride details page for the newly created ride
        resp=self.session.get('http://cycling_test_cycling_web/rides/{}/details'.format(ride_id))
        self.assertEqual(resp.status_code,200)

        # Post a ride with new locations referenced by name
        resp=self.session.post(
            'http://cycling_test_cycling_web/rides/add',
            data=dict_to_postdata(dict(
                start_time={'date':'2005-01-01','time':'10:00:00'},
                end_time={'date':'2005-01-01','time':'10:15:00'},
                total_time=str(15*60),
                rolling_time=str(12*60),
                distance='7',
                odometer='357',
                avspeed='28',
                maxspeed='40',
                equipment_id='0',
                ridergroup_id='0',
                surface_id='0',
                submit='submit',
                startloc='Home 1',
                endloc='Church 2'
            ))
        )

        # Check that we got redirected
        self.assertEqual(resp.history[0].status_code,302)

        # Parse metadata sent with redirect response
        submission_metadata=json.loads(resp.history[0].text)
        ride_id=submission_metadata['ride_id']
        update_weather_task_id=submission_metadata['update_weather_task_id']

        # Check that the locations were created
        resp=self.session.get('http://cycling_test_cycling_web/locations/list')
        self.assertIn('>Home 1</a></td>', resp.text)
        self.assertIn('>Church 2</a></td>', resp.text)

        # Get the location id for Home 1
        location_id=int(re.search(r'<td><a href="/locations/(\d+)/edit">Home 1</a></td>',resp.text).group(1))

        # Check that we can load the location edit page for Home 1
        resp=self.session.get('http://cycling_test_cycling_web/locations/{}/edit'.format(location_id))
        self.assertEqual(resp.status_code,200)

        # Check that we can load the ride details page for the newly created ride
        resp=self.session.get('http://cycling_test_cycling_web/rides/{}/details'.format(ride_id))
        self.assertEqual(resp.status_code,200)

        # Wait for update_ride_weather task to complete
        from celery.result import AsyncResult
        task_result=AsyncResult(update_weather_task_id,app=celery)
        task_result.wait(40)

    def tearDown(self):
        resp=self.session.post('http://cycling_test_cycling_web/logout')
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://cycling_test_cycling_web/rides')
        
        resp=self.session.get('http://cycling_test_cycling_web/rides')
        self.assertEqual(resp.history[0].status_code,302)
        self.assertEqual(resp.history[0].headers['Location'],'http://cycling_test_cycling_web/login?next=http%3A%2F%2Fcycling_test_cycling_web%2Frides')

    def test_fill_missing_weather(self):

        # Trigger a fill_missing_weather task and get its id
        resp=self.session.get('http://cycling_test_cycling_web/fill_missing_weather')
        task_id=json.loads(resp.text)['fill_missing_weather_task_id']

        from celery.result import AsyncResult
        task_result=AsyncResult(task_id,app=celery)
        task_result.wait(40)

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
        new_equipment_count=int(re.search(r'(\d+) total',resp.text).group(1))

        self.assertEqual(new_equipment_count,equipment_count+1)
