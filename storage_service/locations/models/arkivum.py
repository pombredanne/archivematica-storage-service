# stdlib, alphabetical
import json
import logging
import os
import requests
import subprocess

# Core Django, alphabetical
from django.db import models

# Third party dependencies, alphabetical

# This project, alphabetical
from common import utils

# This module, alphabetical
from . import StorageException
from location import Location
from package import Package


class Arkivum(models.Model):
    space = models.OneToOneField('Space', to_field='uuid')

    host = models.CharField(max_length=256,
        help_text='Hostname of the Arkivum web instance. Eg. arkivum.example.com:8443')
    # Optionally be able to rsync
    remote_user = models.CharField(max_length=64, null=True, blank=True,
        help_text="Username on the remote machine accessible via passwordless ssh. (Optional)")
    remote_name = models.CharField(max_length=256, null=True, blank=True,
        help_text="Name or IP of the remote machine. (Optional)")

    class Meta:
        verbose_name = "Arkivum"
        app_label = 'locations'

    ALLOWED_LOCATION_PURPOSE = [
        Location.AIP_STORAGE,
    ]

    def browse(self, path):
        # Support browse so that the Location select works
        if self.remote_user and self.remote_name:
            return self.space._browse_ssh(path, self.remote_user, self.remote_name)
        else:
            return self.space._browse_local(path)

    def delete_path(self, delete_path):
        # Can this be done by just deleting the file on disk?
        # TODO folders
        url = url = 'https://' + self.host + '/files/' + delete_path
        print 'url', url
        response = requests.delete(url, verify=False)
        print 'response', response
        if response.status_code != 204:
            raise StorageException('Unable to delete %s', delete_path)

    def move_to_storage_service(self, src_path, dest_path, dest_space):
        """ Moves src_path to dest_space.staging_path/dest_path. """
        # Get from watched dir
        if self.remote_user and self.remote_name:
            # Rsync from remote
            src_path = "{user}@{host}:{path}".format(
                user=self.remote_user,
                host=self.remote_name,
                path=src_path)
        self.space._create_local_directory(dest_path)
        self.space._move_rsync(src_path, dest_path)

    def move_from_storage_service(self, source_path, destination_path):
        """ Moves self.staging_path/src_path to dest_path. """
        # Rsync to Arkivum watched directory
        if self.remote_user and self.remote_name:
            rsync_dest = "{user}@{host}:{path}".format(
                user=self.remote_user,
                host=self.remote_name,
                path=destination_path)
            # Create remote directories
            command = 'mkdir -p {}'.format(os.path.dirname(destination_path))
            ssh_command = ["ssh", self.remote_user + "@" + self.remote_name, command]
            logging.info("ssh+mkdir command: {}".format(ssh_command))
            try:
                subprocess.check_call(ssh_command)
            except subprocess.CalledProcessError as e:
                logging.warning("ssh+mkdir failed: {}".format(e))
                raise
        else:
            rsync_dest = destination_path
            self.space._create_local_directory(destination_path)
        self.space._move_rsync(source_path, rsync_dest)

    def post_move_from_storage_service(self, staging_path, destination_path, package):
        """ POST to Arkivum with information about the newly stored Package. """
        if package is None:
            return

        # Get size, checksum, checksum algorithm (md5sum), compression algorithm
        # TODO munge this properly
        checksum = utils.generate_checksum(staging_path, 'md5')
        payload = {
            'size': str(os.path.getsize(staging_path)),
            'checksum': checksum.hexdigest(),
            'checksumAlgorithm': 'md5',
            'compressionAlgorithm': '',
        }

        # POST to Arkivum host/api/2/files/release/relative_path
        relative_path = destination_path.replace(self.space.path, '', 1)
        url = 'https://' + self.host + '/api/2/files/release' + relative_path
        # FIXME Arkivum URL does not actually exist yet
        response = requests.post(url, data=payload, verify=False)
        if response.status_code != 200:
            logging.warning('Arkivum responded with %s: %s', response.status_code, response.text)
            raise StorageException('Unable to notify Arkivum of %s', package)
        # Response has request ID for polling status
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            raise StorageException("Could not get request ID from Arkivum's response %s", response.text)
        request_id = response_json['id']

        # Store request ID in misc_attributes
        package.misc_attributes.update({'request_id': request_id})
        package.save()

        # TODO Uncompressed: Post info about bag (really only support AIPs)

    def update_package_status(self, package):
        pass
        # Get local copy
        local_path = package.fetch_local_path()
        # If no request ID, try POSTing to Arkivum again
        if 'request_id' not in package.misc_attributes:
            self.post_move_from_storage_service(local_path, package.full_path, package)
        # If still no request ID, cannot check status
        if 'request_id' not in package.misc_attributes:
            return (None, 'Unable to contact Arkivum')

        # Ask Arkivum for replication status
        url = 'https://' + self.host + '/api/2/files/release/' + package.misc_attributes['request_id']
        response = requests.get(url, verify=False)

        if response.status_code != 200:
            return (None, 'Response from Arkivum server was {}'.format(response))

        # Look for ['fileInformation']['replicationState'] == 'green'
        resp_json = response.json()
        replication = resp_json['fileInformation'].get('replicationState')
        if replication == 'green':
            # Set status to UPLOADED
            package.status = Package.UPLOADED
            package.save()

        return (package.status, None)