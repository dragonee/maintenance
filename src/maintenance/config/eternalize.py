"""
[General]
server = TARGET

[server:TARGET]
host = IP_OR_HOSTNAME
local_path = ~
remote_path = ~/Backups/local_machine

[TARGET:destination]
path = ~/remote-directory
"""


from configparser import ConfigParser

from pathlib import Path

from functools import partial
from itertools import repeat

def remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]

class EternalizeConfigFile:
    server = None

    servers = None

    def __init__(self):
        self.servers = {}

        self.reader = ConfigParser()

        self.reader.read(self.paths())

        try:
            self.server = self.reader['General']['server']

            self.servers = {remove_prefix(k, 'server:'): self.validate_server(v) for (k, v) in self.reader.items() if k.startswith('server:')}

            self.update_targets()

        except KeyError:
            raise KeyError(__doc__)

    def validate_server(self, server):
        """Throws KeyError if a setting is not set."""

        return {
            'host': server['host'],
            'user': server['user'],
            'port': int(server.get('port', '22')),
            'local_path': server['local_path'],
            'remote_path': server['remote_path'],
        }

    def validate_target(self, target):
        return {
            'path': target['path']
        }

    def add_target_file(self, file):
        self.reader.readfp(file)

        self.update_targets()

    def update_targets(self):
        def starts_with_a_valid_key(valid_keys, x):
            return any(map(
                lambda valid, candidate: candidate.startswith("{}:".format(valid)),
                valid_keys,
                repeat(x)
            ))

        starts_with_a_server_key = partial(starts_with_a_valid_key, self.servers.keys())

        self.targets = {k: self.validate_target(v) for (k, v) in self.reader.items() if starts_with_a_server_key(k)}

    def target(self, host, name):
        return self.targets['{}:{}'.format(host, name)]

    def paths(self):
        return [
            '/etc/eternalize.ini',
            Path.home() / '.eternalize.ini',
        ]
