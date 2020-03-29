
from configparser import ConfigParser

from pathlib import Path

import os

class YoutubeFeedConfigFile:
    host = None
    user = None

    remote_path = None
    local_path = None

    def __init__(self):
        self.reader = ConfigParser()

        self.reader.read(self.paths())

        try:
            self.host = self.reader['Feed']['host']
            self.user = self.reader['Feed']['user']

            self.remote_path = self.reader['Feed']['remote_path']
            self.local_path = os.path.expanduser(self.reader['Feed']['local_path'])
        except KeyError:
            raise KeyError("Create ~/.youtube.ini file with section [Feed] containing host, user, remote_path and local_path")

    def paths(self):
        return [
            '/etc/youtube.ini',
            Path.home() / '.youtube.ini',
        ]