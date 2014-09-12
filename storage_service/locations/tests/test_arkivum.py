import os
import requests
import shutil

from django.test import TestCase
import vcr

from locations import models


class TestArkivum(TestCase):

    fixtures = ['initial_data.json', 'arkivum.json']

    def setUp(self):
        self.arkivum_object = models.Arkivum.objects.all()[0]

    def test_has_required_attributes(self):
        assert self.arkivum_object.host
        # Both or neither of remote_user/remote_name
        assert bool(self.arkivum_object.remote_user) == bool(self.arkivum_object.remote_name)

    def test_browse(self):
        response = self.arkivum_object.browse('/')
        assert response['directories'] == []
        assert response['entries'] == []

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/arkivum_move_from_ss.yaml')
    def test_move_from_ss(self):
        # Create test.txt
        open('unittest.txt', 'w').write('test file\n')
        # Upload
        self.arkivum_object.move_from_storage_service('unittest.txt', '/mnt/arkivum/test/unittest.txt')
        # Verify
        url = 'https://' + self.arkivum_object.host + '/files/'
        response = requests.get(url, verify=False)
        assert 'test' in [x['name'] for x in response.json()['files']]
        url += 'test'
        response = requests.get(url, verify=False)
        assert 'unittest.txt' in [x['name'] for x in response.json()['files']]
        # Cleanup
        os.remove('unittest.txt')
        shutil.rmtree('/mnt/arkivum/test')

        # TODO test folder
