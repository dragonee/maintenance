
from configparser import ConfigParser

from pathlib import Path

import os

class YoutubePipelineConfigFile:
    cookies = None

    def __init__(self):
        self.reader = ConfigParser()

        self.reader.read(self.paths())

        try:
            self.cookies = os.path.expanduser(self.reader['Youtube']['cookies'])
            self.download_path = os.path.expanduser(self.reader['Youtube']['download_path'])

            self.eternalize_target = self.reader['Eternalize']['target']
        except KeyError:
            raise KeyError("Create ~/.youtube.ini file with section [Youtube] containing cookies and download_path, and [Eternalize] containing target")

    def paths(self):
        return [
            '/etc/youtube.ini',
            Path.home() / '.youtube.ini',
        ]