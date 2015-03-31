# stdlib, alphabetical
import logging
import os

# Core Django, alphabetical
from django.db import models

# Third party dependencies, alphabetical
import swiftclient

# This project, alphabetical

# This module, alphabetical
from . import StorageException
from location import Location

LOGGER = logging.getLogger(__name__)


class Swift(models.Model):
    space = models.OneToOneField('Space', to_field='uuid')
    auth_url = models.CharField(max_length=256,
        help_text='URL to authenticate against')
    auth_version = models.CharField(max_length=8, default='2',
        help_text='OpenStack auth version')
    username = models.CharField(max_length=64,
        help_text='Username to authenticate as')
    # HELP how do I store the password?  Has to be plaintext to send to Swift, but that seems like a bad idea
    password = models.CharField(max_length=256,
        help_text='Password to authenticate with')
    container = models.CharField(max_length=64)
    tenant = models.CharField(max_length=64, null=True, blank=True,
        help_text='The tenant/account name, required when connecting to an auth 2.0 system.')
    region = models.CharField(max_length=64, null=True, blank=True,
        help_text='Optional: Region in Swift')

    class Meta:
        verbose_name = "Swift"
        app_label = 'locations'

    ALLOWED_LOCATION_PURPOSE = [
        Location.AIP_STORAGE,
        Location.DIP_STORAGE,
        Location.TRANSFER_SOURCE,
        Location.BACKLOG,
    ]

    def __init__(self, *args, **kwargs):
        super(Swift, self).__init__(*args, **kwargs)
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = swiftclient.client.Connection(
                authurl=self.auth_url,
                user=self.username,
                key=self.password,
                tenant_name=self.tenant,
                auth_version=self.auth_version,
                os_options={'region_name': self.region}
            )
        return self._connection

    def browse(self, path):
        pass

    def delete_path(self, delete_path):
        pass

    def move_to_storage_service(self, src_path, dest_path, dest_space):
        """ Moves src_path to dest_space.staging_path/dest_path. """
        # TODO find a way to stream content to dest_path, instead of having to put it in memory
        try:
            _, content = self.connection.get_object(self.container, src_path)
            self.space._create_local_directory(dest_path)
            with open(dest_path, 'wb') as f:
                f.write(content)
        except swiftclient.exceptions.ClientException:
            # Swift only stores objects and fakes having folders. If src_path
            # doesn't exist, assume it is supposed to be a folder and fetch all
            # items with that prefix.
            _, content = self.connection.get_container(self.container, prefix=src_path)
            to_get = [x['name'] for x in content if x.get('name')]
            if not to_get:
                # If nothing found, try normalizing src_path to remove possible
                # extra characters like / /* /.  These glob-match on a
                # filesystem, but do not character-match in Swift.
                # Normalize dest_path as well, so replace continues to work
                src_path = os.path.normpath(src_path)
                dest_path = os.path.normpath(dest_path)
                _, content = self.connection.get_container(self.container, prefix=src_path)
                to_get = [x['name'] for x in content if x.get('name')]
            for entry in to_get:
                dest = entry.replace(src_path, dest_path, 1)
                self.space._create_local_directory(dest)
                _, content = self.connection.get_object(self.container, entry)
                with open(dest, 'wb') as f:
                    f.write(content)

    def move_from_storage_service(self, source_path, destination_path):
        """ Moves self.staging_path/src_path to dest_path. """
        if os.path.isdir(source_path):
            # Both source and destination paths should end with /
            destination_path = os.path.join(destination_path, '')
            # Swift does not accept folders, so upload each file individually
            for path, _, files in os.walk(source_path):
                for basename in files:
                    entry = os.path.join(path, basename)
                    dest = entry.replace(source_path, destination_path, 1)
                    with open(entry, 'rb') as f:
                        self.connection.put_object(
                            self.container,
                            obj=dest,
                            contents=f,
                        )
        elif os.path.isfile(source_path):
            with open(source_path, 'rb') as f:
                self.connection.put_object(
                    self.container,
                    obj=destination_path,
                    contents=f,
                )
        else:
            raise StorageException('%s is neither a file nor a directory, may not exist' % source_path)
