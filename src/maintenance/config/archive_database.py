
from configparser import ConfigParser

from pathlib import Path

import re

from ..strings import _regex_splitter

class ArchiveDatabaseConfigFile:
    dbtype = None

    databases = None
    users = None

    def __init__(self):
        self.databases = tuple()
        self.users = {}

    _config = None
    def get_config(self):
        if not self._config:
            self._config = ConfigParser()

        return self._config

    def load(self, filename):
        c = self.get_config()

        c.read(filename)

        try:
            self.dbtype = c['Config']['dbtype']
            self.databases = _regex_splitter.split(c['Backup']['databases'])
        except KeyError:
            raise KeyError("This config file requires Config.dbtype and Backup.databases keys")

        try:
            self.users = dict(c['Users'])
        except KeyError:
            pass

    def write(self, fp):
        c = self.get_config()

        c['Config'] = {
            'dbtype': self.dbtype,
        }

        c['Backup'] = {
            'databases': ','.join(self.databases)
        }

        c['Users'] = self.users

        c.write(fp)


