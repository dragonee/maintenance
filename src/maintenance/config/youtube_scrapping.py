
from configparser import ConfigParser

from pathlib import Path

class YoutubeScrappingConfigFile:
    cookies = None
    chrome_binary = None
    chromedriver_binary = None

    def __init__(self):
        self.reader = ConfigParser()

        self.reader.read(self.paths())

        try:
            self.cookies = self.reader['Youtube']['cookies']
            self.chromedriver_binary = self.reader['Selenium']['chromedriver_binary']
            self.chrome_binary = self.reader['Selenium']['chrome_binary']
        except KeyError:
            raise KeyError("Create ~/.youtube.ini file with section [Youtube] containing cookies, and [Selenium] containing chrome_binary and chromedriver_binary")

    def paths(self):
        return [
            '/etc/youtube.ini',
            Path.home() / '.youtube.ini',
        ]