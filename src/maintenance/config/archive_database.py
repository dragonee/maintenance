
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
            self.databases = list(filter(lambda x: x != '', _regex_splitter.split(c['Backup']['databases'])))
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


class AdministrativeUserConfigFile:
    user = None
    password = None

    def __init__(self, remote=None):
        self.reader = ConfigParser()

        self.reader.read(self.paths())

        try:
            self.password = self.reader['general']['mysql_password']
            self.user = self.reader['general']['mysql_user']

        except KeyError:
            raise KeyError("Create ~/.archive.ini file with section [general] containing mysql_user and mysql_password")

    def paths(self):
        return [
            '/etc/archive.ini',
            Path.home() / '.archive.ini',
        ]
