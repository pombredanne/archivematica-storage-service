# stdlib, alphabetical
import json
import logging
import os
import requests

# Core Django, alphabetical
from django.db import models

# Third party dependencies, alphabetical

# This project, alphabetical
from common import utils

# This module, alphabetical
from location import Location


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
        # This is AIP storage only - do not support browse
        logging.warning('Arkivum does not support browsing')
        return {'directories': [], 'entries': []}

    def delete_path(self, delete_path):
        pass

    def move_to_storage_service(self, src_path, dest_path, dest_space):
        """ Moves src_path to dest_space.staging_path/dest_path. """
        pass

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


    def update_package_status(self, package):
        pass
