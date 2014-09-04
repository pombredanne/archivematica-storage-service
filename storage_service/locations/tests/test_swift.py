
import os
import shutil

from django.test import TestCase
import vcr

from locations import models


class TestSwift(TestCase):

    fixtures = ['base.json', 'swift.json']

    def setUp(self):
        self.swift_object = models.Swift.objects.all()[0]

    def test_has_required_attributes(self):
        assert self.swift_object.auth_url
        assert self.swift_object.auth_version
        assert self.swift_object.username
        assert self.swift_object.password
        assert self.swift_object.container
        if self.swift_object.auth_version in ("2", "2.0", 2):
            assert self.swift_object.tenant

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_move_to.yaml')
    def test_move_to_ss(self):
        self.swift_object.move_to_storage_service('/test.txt', 'test.txt', None)
        assert open('test.txt', 'r').read() == 'test file\n'
        os.remove('test.txt')

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_move_folder_to.yaml')
    def test_move_folder_to_ss(self):
        self.swift_object.move_to_storage_service('/ts/test/', 'test1234/', None)
        assert os.path.isdir('test1234')
        assert os.path.isdir('test1234/folder1')
        assert os.path.isfile('test1234/folder1/file1')
        assert open('test1234/folder1/file1', 'r').read() == 'file1\n'
        assert os.path.isfile('test1234/file2')
        assert open('test1234/file2', 'r').read() == 'file2\n'
        shutil.rmtree('test1234')

    # FIXME capturing the cassette causes an exception
    # @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_move_from.yaml')
    # def test_move_from_ss(self):
    #     # create test.txt
    #     open('test.txt', 'w').write('test file\n')
    #     self.swift_object.move_from_storage_service('test.txt', '/test.txt')
    #     # Unsure how to verify.  Will raise exception if fails?
    #     os.remove('test.txt')
    #     # Remove me
    #     self.swift_object.delete_path('/test.txt')
    #
    # @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_move_from_already_exists.yaml')
    # def test_move_from_ss_already_exists(self):
    #     open('test.txt', 'w').write('test file\n')
    #     with pytest.raises(swiftclient.exceptions.ClientException):
    #         self.swift_object.move_from_storage_service('test.txt', '/test.txt')

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_delete.yaml')
    def test_delete_path(self):
        self.swift_object.delete_path('/test.txt')

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_delete_folder.yaml')
    def test_delete_folder(self):
        self.swift_object.delete_path('/aips/c521/')

    def test_update_package_status(self):
        pass
