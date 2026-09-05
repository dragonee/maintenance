#!/usr/bin/env python3

"""
Recognise a Bedrock-flavoured WordPress installation.

Bedrock keeps its credentials in a dotenv file and its WordPress under
web/wp, so it needs its own detector, but it publishes the same mysql.*
variables as archive-plugin-wordpress and is handled identically downstream.
"""

VERSION = '2.0'

import sys

from ..archive.detect import find_dsn, read_env_file
from ..archive.plugin import Discovery, Plugin, run


class BedrockPlugin(Plugin):
    name = 'bedrock'
    order = 10
    version = VERSION

    def env_file(self, directory):
        return directory / '.env'

    def looks_like_bedrock(self, directory):
        return (directory / 'config/application.php').exists() \
            or (directory / 'web/wp/wp-login.php').exists()

    def settings(self, directory):
        env_file = self.env_file(directory)

        if not env_file.exists():
            return {}

        config = read_env_file(env_file)
        dsn = find_dsn(config, engine='mysql')

        if dsn:
            return {
                'DB_NAME': dsn['database'],
                'DB_USER': dsn['user'],
                'DB_PASSWORD': dsn['password'],
                'DB_HOST': dsn['host'],
                'DB_PORT': dsn['port'],
            }

        return {
            'DB_NAME': config.get('DB_NAME'),
            'DB_USER': config.get('DB_USER'),
            'DB_PASSWORD': config.get('DB_PASSWORD'),
            'DB_HOST': config.get('DB_HOST') or 'localhost',
            'DB_PORT': None,
        }

    def discover(self, request):
        directory = request.directory

        if not self.looks_like_bedrock(directory):
            return Discovery(score=0.0)

        env_file = self.env_file(directory)

        discovery = Discovery(score=1.0, data={
            'config': env_file.name if env_file.exists() else None,
            'markers': [
                marker for marker in ('config/application.php', 'web/wp/wp-login.php')
                if (directory / marker).exists()
            ],
        })

        settings = self.settings(directory)
        database = settings.get('DB_NAME')

        if not database:
            self.log("no database configured in {}", env_file.name)
            return discovery

        discovery.var('mysql.databases', [database])
        discovery.var('mysql.host', settings.get('DB_HOST') or 'localhost')
        discovery.var('mysql.user', settings.get('DB_USER'))

        if settings.get('DB_PORT'):
            discovery.var('mysql.port', int(settings['DB_PORT']))

        if (directory / '.env').exists():
            discovery.require_secret('mysql.password', source='.env:DB_PASSWORD')

        self.log("{} on {}", database, settings.get('DB_HOST') or 'localhost')

        return discovery

    def secrets(self, request):
        return {'mysql.password': self.settings(request.directory).get('DB_PASSWORD')}


def main():
    sys.exit(run(BedrockPlugin))
