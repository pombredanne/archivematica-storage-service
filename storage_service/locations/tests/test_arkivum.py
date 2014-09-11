
from django.test import TestCase

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

