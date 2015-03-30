# stdlib, alphabetical
from datetime import datetime
import logging
import os
import shutil
import re
import subprocess
import tempfile

# Core Django, alphabetical
from django.db import models

# Third party dependencies, alphabetical

# This project, alphabetical
from common import utils

# This module, alphabetical
from location import Location

LOGGER = logging.getLogger(__name__)


class PipelineLocalFS(models.Model):
    """ Spaces local to the creating machine, but not to the storage service.

    Use case: currently processing locations. """
    space = models.OneToOneField('Space', to_field='uuid')

    remote_user = models.CharField(max_length=64,
        help_text="Username on the remote machine accessible via ssh")
    remote_name = models.CharField(max_length=256,
        help_text="Name or IP of the remote machine.")
    # Space.path is the path on the remote machine

    class Meta:
        verbose_name = "Pipeline Local FS"
        app_label = 'locations'

    ALLOWED_LOCATION_PURPOSE = [
        Location.AIP_RECOVERY,
        Location.AIP_STORAGE,
        Location.DIP_STORAGE,
        Location.CURRENTLY_PROCESSING,
        Location.TRANSFER_SOURCE,
        Location.BACKLOG,
    ]

    def _format_host_path(self, path, user=None, host=None):
        """Formats a remote path suitable for use with rsync."""
        if user is None:
            user = self.remote_user
        if host is None:
            host = self.remote_name

        return "{}@{}:{}".format(user, host, utils.coerce_str(path))

    def browse(self, path):
        """
        Returns information about the files and simulated-folders in Duracloud.

        See Space.browse for full documentation.

        Properties provided:
        'size': Size of the object
        'timestamp': Last modified timestamp of the object or directory
        """
        private_ssh_key = '/var/lib/archivematica/.ssh/id_rsa'
        path = os.path.join(path, '')  # Rsync requires a / on the end of dirs to list contents

        # Get entries
        command = [
            'rsync',
            '--protect-args',
            '--list-only',
            '--exclude', '.*',  # Ignore hidden files
            '--rsh', 'ssh -i ' + private_ssh_key,  # Specify identify file
            self._format_host_path(path)]
        LOGGER.info('rsync list command: %s', command)
        LOGGER.debug('"%s"', '" "'.join(command))  # For copying to shell
        try:
            output = subprocess.check_output(command)
        except Exception as e:
            LOGGER.warning("rsync list failed: %s", e, exc_info=True)
            entries = []
            directories = []
        else:
            output = output.splitlines()
            LOGGER.debug('rsync list output: %s', output)
            # Output is lines in format:
            # <type><permissions>  <size>  <date> <time> <path>
            # Eg: drwxrws---          4,096 2015/03/02 17:05:20 tmp
            # Eg: -rw-r--r--            201 2013/05/13 13:26:48 LICENSE.md
            # Eg: lrwxrwxrwx             78 2015/02/19 12:13:40 sharedDirectory
            # Parse out the path and type
            # Define groups for type, permissions, size, timestamp and name
            regex = r'^(?P<type>.)(?P<permissions>.{9}) +(?P<size>[\d,]+) (?P<timestamp>..../../.. ..:..:..) (?P<name>.*)$'
            matches = [re.match(regex, e) for e in output]
            # Take the last entry. Ignore empty lines and '.'
            entries = [e.group('name') for e in matches
                if e and e.group('name') != '.']
            # Only items whose type is not '-'. Links count as dirs.
            directories = [e.group('name') for e in matches
                if e and e.group('name') != '.' and e.group('type') != '-']
            # Generate properties for each entry
            properties = {}
            for e in matches:
                name = e.group('name')
                if name not in entries:
                    continue
                properties[name] = {}
                properties[name]['timestamp'] = datetime.isoformat(datetime.strptime(e.group('timestamp'), '%Y/%m/%d %H:%M:%S'))
                if name not in directories:
                    properties[name]['size'] = int(e.group('size').replace(',', ''))

        directories = sorted(directories, key=lambda s: s.lower())
        entries = sorted(entries, key=lambda s: s.lower())
        LOGGER.debug('entries: %s', entries)
        LOGGER.debug('directories: %s', directories)
        LOGGER.debug('properties: %s', properties)
        return {'directories': directories, 'entries': entries, 'properties': properties}

    def delete_path(self, delete_path):
        # Sync from an empty directory to delete the contents of delete_path;
        # passing --delete to rsync causes it to delete all contents from the
        # destination path that don't exist in the source which, since it's an
        # empty directory, is everything.
        temp_dir = tempfile.mkdtemp()
        dest_path = self._format_host_path(os.path.join(delete_path, ''))
        command = ['rsync', '-vv', '--itemize-changes', '--protect-args',
                   '--delete', '--dirs',
                   os.path.join(temp_dir, ''),
                   dest_path]
        LOGGER.info("rsync delete command: %s", command)
        try:
            subprocess.check_call(command)
        except Exception:
            LOGGER.warning("rsync delete failed: %s", command, exc_info=True)
            raise
        finally:
            shutil.rmtree(temp_dir)

    def move_to_storage_service(self, src_path, dest_path, dest_space):
        """ Moves src_path to dest_space.staging_path/dest_path. """
        # if dest_space == self:
        #     # If moving within same space, don't bring to storage service
        #     # FIXME dest_path is relative, and intended for staging_path, need
        #     # real destination path - memoize something and retrieve it in
        #     # move_from_storage_service?  Move to self.space.path/dest_path?
        #     command = 'mkdir -p "{dest_dir}" && mv "{src_path}" "{dest_path}"'.format(
        #         dest_dir=os.path.dirname(dest_path),
        #         src_user=self.remote_user, src_host=self.remote_name,
        #         src_path=src_path, dest_path=dest_path,
        #         )
        #     ssh_command = ["ssh", self.remote_user+"@"+self.remote_name, command]
        #     LOGGER.info("ssh+mv command: %s", ssh_command)
        #     try:
        #         subprocess.check_call(ssh_command)
        #     except subprocess.CalledProcessError as e:
        #         LOGGER.warning("ssh+mv failed: %s", e)
        #         raise
        # else:
        src_path = self._format_host_path(src_path)
        self.space._create_local_directory(dest_path)
        return self.space._move_rsync(src_path, dest_path)

    def post_move_to_storage_service(self, *args, **kwargs):
        # TODO delete original file?
        pass

    def move_from_storage_service(self, source_path, destination_path):
        """ Moves self.staging_path/src_path to dest_path. """

        # Assemble a set of directories to create on the remote server;
        # these will be created one at a time
        directories = []
        path = destination_path
        while path != '' and path != '/':
            directories.insert(0, path)
            path = os.path.dirname(path)

        # Syncing an empty directory will ensure no files get transferred
        temp_dir = os.path.join(tempfile.mkdtemp(), '')

        # Creates the destination_path directory without copying any files
        # Dir must end in a / for rsync to create it
        for directory in directories:
            path = self._format_host_path(os.path.join(os.path.dirname(directory), ''))
            cmd = ['rsync', '-vv', '--protect-args', '--recursive', temp_dir, path]
            LOGGER.info("rsync path creation command: %s", cmd)
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                shutil.rmtree(temp_dir)
                LOGGER.warning("rsync path creation failed: %s", e)
                raise

        shutil.rmtree(temp_dir)

        # Prepend user and host to destination
        destination_path = self._format_host_path(destination_path)

        # Move file
        return self.space._move_rsync(source_path, destination_path)
