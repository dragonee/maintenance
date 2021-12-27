
from configparser import ConfigParser

from pathlib import Path

class CoordinateConfigFile:
    server = None

    def __init__(self):
        self.reader = ConfigParser()

        self.reader.read(self.paths())

        try:
            self.server = self.reader['Coordinate']['server']
            self.password = self.reader['Coordinate'].get('password')
        except KeyError:
            raise KeyError("Create ~/.coordinate.ini file with section [Coordinate] containing server")

    def paths(self):
        return [
            '/etc/coordinate.ini',
            Path.home() / '.coordinate.ini',
        ]
