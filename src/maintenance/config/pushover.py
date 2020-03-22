
from configparser import ConfigParser

from pathlib import Path

class PushoverConfigFile:
    token = None
    user = None

    def __init__(self):
        self.reader = ConfigParser()

        self.reader.read(self.paths())

        try:
            self.token = self.reader['Pushover']['token']
            self.user = self.reader['Pushover']['user']
        except KeyError:
            raise KeyError("Create ~/.pushover.ini file with section [Pushover] containing token and user keys")

    def paths(self):
        return [
            '/etc/pushover.ini',
            Path.home() / '.pushover.ini',
        ]