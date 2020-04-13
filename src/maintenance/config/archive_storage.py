
from configparser import ConfigParser

from pathlib import Path

class SSHConfigFile:
    server = None

    default_server = None
    default_user = None
    default_directory = None

    configs = None

    def __init__(self, remote=None):
        self.reader = ConfigParser()

        self.configs = {}

        self.reader.read(self.paths())

        try:
            for key, value in self.reader.items():
                if key.startswith('ssh:'):
                    self.configs[key[4:]] = value

            self.server = self.reader['SSH']['default_server']

            config = self.config(remote or self.server)

            self.default_server = config['server']
            self.default_user = config['user']
            self.default_directory = config['directory']

        except KeyError:
            raise KeyError("Create ~/.archive.ini file with section [SSH] containing default_server and [ssh:<server>] config")

    def config(self, host):
        return self.configs[host]

    def paths(self):
        return [
            '/etc/archive.ini',
            Path.home() / '.archive.ini',
        ]
