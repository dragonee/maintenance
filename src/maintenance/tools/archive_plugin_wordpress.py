#!/usr/bin/env python3

"""
Recognise a classic WordPress installation and describe its database.

This plugin does not dump anything. It reads wp-config.php, publishes what
it found as mysql.* variables, and lets archive-plugin-mysql do the work.
That split is what lets one directory be a WordPress site *and* have a
Caddy vhost *and* a handful of extra config files, each handled by the
plugin that understands it.
"""

VERSION = '2.0'

import sys

from ..archive.detect import read_php_defines
from ..archive.plugin import Discovery, Plugin, run


WP_KEYS = ('DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_CHARSET', 'table_prefix')


class WordpressPlugin(Plugin):
    name = 'wordpress'
    order = 10
    version = VERSION

    def config_file(self, directory):
        return directory / 'wp-config.php'

    def discover(self, request):
        directory = request.directory
        config_file = self.config_file(directory)

        if not config_file.exists():
            # wp-login.php without wp-config.php is still a WordPress tree,
            # just one we cannot describe a database for.
            if (directory / 'wp-login.php').exists():
                return Discovery(score=0.5, data={'config': None})

            return Discovery(score=0.0)

        config = read_php_defines(config_file, WP_KEYS)
        database = config.get('DB_NAME')

        discovery = Discovery(score=1.0, data={
            'config': str(config_file.relative_to(directory)),
            # What identifies this directory as the one the plan describes.
            'markers': [str(config_file.relative_to(directory))],
        })

        if not database:
            self.log("{} has no DB_NAME", config_file.name)
            return discovery

        host, _, port = (config.get('DB_HOST') or 'localhost').partition(':')

        discovery.var('mysql.databases', [database])
        discovery.var('mysql.host', host or 'localhost')
        discovery.var('mysql.user', config.get('DB_USER'))

        if port.isdigit():
            discovery.var('mysql.port', int(port))

        # The site's own user is recreated when the archive is restored, so
        # its password has to survive; it is fetched from wp-config.php
        # again at pack time rather than stored in the plan.
        discovery.require_secret(
            'mysql.password',
            source='{}:DB_PASSWORD'.format(config_file.name),
        )

        self.log("{} on {}", database, host or 'localhost')

        return discovery

    def secrets(self, request):
        config_file = self.config_file(request.directory)

        if not config_file.exists():
            return {}

        config = read_php_defines(config_file, WP_KEYS)

        return {'mysql.password': config.get('DB_PASSWORD')}


def main():
    sys.exit(run(WordpressPlugin))
