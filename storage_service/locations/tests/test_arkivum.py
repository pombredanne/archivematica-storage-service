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
        self.package = models.Package.objects.all()[0]

    def test_has_required_attributes(self):
        assert self.arkivum_object.host
        # Both or neither of remote_user/remote_name
        assert bool(self.arkivum_object.remote_user) == bool(self.arkivum_object.remote_name)

    def test_browse(self):
        response = self.arkivum_object.browse('/mnt/arkivum/')
        assert response['directories'] == ['aips', 'ts']
        assert response['entries'] == ['aips', 'test.txt', 'ts']

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/arkivum_delete.yaml')
    def test_delete(self):
        # Verify exists
        url = 'https://' + self.arkivum_object.host + '/files/ts'
        response = requests.get(url, verify=False)
        assert 'unittest.txt' in [x['name'] for x in response.json()['files']]
        # Delete file
        self.arkivum_object.delete_path('/ts/unittest.txt')
        # Verify deleted
        url = 'https://' + self.arkivum_object.host + '/files/ts'
        response = requests.get(url, verify=False)
        assert 'unittest.txt' not in [x['name'] for x in response.json()['files']]

        # Delete folder
        # self.arkivum_object.delete_path('/ts/test/')
        # Verify deleted

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

    # @vcr.use_cassette('locations/fixtures/vcr_cassettes/arkivum_post_move_from_ss.yaml')
    def test_post_move_from_ss(self):
        # POST to Arkivum about file
        open('unittest.txt', 'w').write('test file\n')
        self.arkivum_object.post_move_from_storage_service('unittest.txt', self.package.full_path, self.package)
        assert self.package.misc_attributes['request_id']
        # Cleanup
        os.remove('unittest.txt')

    def test_move_to_ss(self):
        # Test file
        self.arkivum_object.move_to_storage_service('/mnt/arkivum/ts/test.txt', 'folder/test.txt', None)
        assert os.path.isdir('folder')
        assert os.path.isfile('folder/test.txt')
        assert open('folder/test.txt', 'r').read() == 'test file\n'
        # Cleanup
        os.remove('folder/test.txt')
        os.removedirs('folder')
        # Test folder
        self.arkivum_object.move_to_storage_service('/mnt/arkivum/ts/test/', 'folder/test/', None)
        assert os.path.isdir('folder')
        assert os.path.isdir('folder/test')
        assert os.path.isdir('folder/test/subfolder')
        assert os.path.isfile('folder/test/test.txt')
        assert os.path.isfile('folder/test/subfolder/test2.txt')
        assert open('folder/test/test.txt').read() == 'test file\n'
        assert open('folder/test/subfolder/test2.txt').read() == 'test file2\n'
        # Cleanup
        os.remove('folder/test/test.txt')
        os.remove('folder/test/subfolder/test2.txt')
        os.removedirs('folder/test/subfolder')
