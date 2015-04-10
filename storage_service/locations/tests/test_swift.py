# -*- coding: utf-8 -*-
import os
import shutil

from django.test import TestCase
import pytest
import swiftclient
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

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_browse.yaml')
    def test_browse(self):
        resp = self.swift_object.browse('transfers/SampleTransfers')
        assert resp
        assert resp['directories'] == ['badNames', 'Images']
        assert resp['entries'] == ['badNames', 'BagTransfer.zip', 'Images']
        assert resp['properties']['BagTransfer.zip']['size'] == 13187
        assert resp['properties']['BagTransfer.zip']['timestamp'] == '2015-04-10T21:52:09.559240'

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_browse_unicode.yaml')
    def test_browse_unicode(self):
        resp = self.swift_object.browse('transfers/SampleTransfers/Images')
        assert resp
        assert resp['directories'] == ['pictures']
        assert resp['entries'] == ['799px-Euroleague-LE Roma vs Toulouse IC-27.bmp', 'BBhelmet.ai', 'G31DS.TIF', 'lion.svg', 'Nemastylis_geminiflora_Flower.PNG', 'oakland03.jp2', 'pictures', 'Vector.NET-Free-Vector-Art-Pack-28-Freedom-Flight.eps', 'WFPC01.GIF', u'エブリンの写真.jpg']
        assert resp['properties'][u'エブリンの写真.jpg']['size'] == 158131
        assert resp['properties'][u'エブリンの写真.jpg']['timestamp'] == '2015-04-10T21:56:43.264560'

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_move_to.yaml')
    def test_move_to_ss(self):
        test_file = 'test/%percent.txt'
        # Not here already
        try:
            os.remove(test_file)
        except OSError:
            pass
        assert not os.path.exists(test_file)
        # Test
        self.swift_object.move_to_storage_service('transfers/SampleTransfers/badNames/objects/%percent.txt', test_file, None)
        # Verify
        assert os.path.isdir('test')
        assert os.path.isfile(test_file)
        assert open(test_file, 'r').read() == '%percent\n'
        # Cleanup
        os.remove(test_file)

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_move_to_not_exist.yaml')
    def test_move_to_ss_not_exist(self):
        test_file = 'test/dne.txt'
        assert not os.path.exists(test_file)
        self.swift_object.move_to_storage_service('transfers/SampleTransfers/does_not_exist.txt', test_file, None)
        assert not os.path.exists(test_file)

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_move_to_folder.yaml')
    def test_move_to_ss_folder(self):
        test_dir = 'test/subdir/'
        try:
            shutil.rmtree(test_dir)
        except (OSError, shutil.Error):
            pass
        assert not os.path.exists(test_dir)
        self.swift_object.move_to_storage_service('transfers/SampleTransfers/badNames/objects/%/', test_dir, None)
        # Verify
        assert os.path.isdir(test_dir)
        assert os.path.isfile(os.path.join(test_dir, '@at.txt'))
        assert open(os.path.join(test_dir, '@at.txt'), 'r').read() == 'data\n'
        assert os.path.isfile(os.path.join(test_dir, 'control.txt'))
        assert open(os.path.join(test_dir, 'control.txt'), 'r').read() == 'data\n'
        # Cleanup
        shutil.rmtree(test_dir)

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_move_from.yaml')
    def test_move_from_ss(self):
        # create test.txt
        open('test.txt', 'w').write('test file\n')
        # Test
        self.swift_object.move_from_storage_service('test.txt', 'transfers/SampleTransfers/test.txt')
        # Verify
        resp = self.swift_object.browse('transfers/SampleTransfers/')
        assert 'test.txt' in resp['entries']
        assert resp['properties']['test.txt']['size'] == 10
        # Cleanup
        os.remove('test.txt')
        self.swift_object.delete_path('transfers/SampleTransfers/test.txt')

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_move_from_already_exists.yaml')
    def test_move_from_ss_already_exists(self):
        # Setup
        test_file = 'transfers/SampleTransfers/badNames/objects/%/control.txt'
        resp = self.swift_object.browse('transfers/SampleTransfers/badNames/objects/%/')
        assert 'control.txt' in resp['entries']
        open('test.txt', 'w').write('test file\n')
        # Test
        with pytest.raises(swiftclient.exceptions.ClientException):
            self.swift_object.move_from_storage_service('test.txt', test_file)

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_delete.yaml')
    def test_delete_path(self):
        self.swift_object.delete_path('/test.txt')

    @vcr.use_cassette('locations/fixtures/vcr_cassettes/swift_delete_folder.yaml')
    def test_delete_folder(self):
        self.swift_object.delete_path('/aips/c521/')
