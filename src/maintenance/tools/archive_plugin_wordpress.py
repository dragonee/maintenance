#!/usr/bin/env python3

"""
Recognise a classic WordPress installation and describe its database.

This plugin does not dump anything. It reads wp-config.php, publishes what
it found as mysql.* variables, and lets archive-plugin-mysql do the work.
That split is what lets one directory be a WordPress site *and* have a
Caddy vhost *and* a handful of extra config files, each handled by the
plugin that understands it.
"""

VERSION = '2.1'

import os
import sys

from pathlib import Path

from ..archive.detect import read_php_defines
from ..archive.plugin import Discovery, Plugin, run


WP_KEYS = ('DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_CHARSET', 'table_prefix')

#: How far below the top of the tree to look for an installation. A static
#: site with a blog under public/blog is an ordinary arrangement and its
#: database is easy to miss; something buried deeper than this is more
#: likely a copy, a backup or a vendored dependency than the installation
#: being archived.
MAX_DEPTH = 4

#: Directories that hold other people's code, or copies of this one.
SKIP = frozenset(('vendor', 'node_modules', 'wp-content', 'wp-includes',
                  'wp-admin', 'backup', 'backups'))


class WordpressPlugin(Plugin):
    name = 'wordpress'
    order = 10
    version = VERSION

    def config_files(self, directory):
        """Every wp-config.php that looks like a real installation.

        The top of the tree first, because that is the ordinary case and
        settles it. Otherwise walk down a little way: a WordPress serving
        the blog of an otherwise static site sits under public/blog, and
        looking only at the top misses its database entirely -- which
        produces an archive of the files with nothing to restore them
        against.
        """
        root = directory / 'wp-config.php'

        if root.exists():
            return [root]

        found = []
        depth_of = lambda path: len(Path(path).parts) - len(directory.parts)

        for base, directories, files in os.walk(str(directory)):
            if depth_of(base) >= MAX_DEPTH:
                directories[:] = []
                continue

            directories[:] = [
                d for d in directories
                if d not in SKIP and not d.startswith('.')
            ]

            if 'wp-config.php' in files:
                found.append(Path(base) / 'wp-config.php')

                # An installation found here owns its subtree; anything
                # below is its own content, not a second site.
                directories[:] = []

        return sorted(found)

    def discover(self, request):
        directory = request.directory
        found = self.config_files(directory)

        if len(found) > 1:
            # Several installations, each with its own credentials, is not
            # something to guess about: one set of mysql.* vars cannot
            # describe them all.
            self.log("{} installations found, which needs a plan each:",
                     len(found))

            for path in found:
                self.log("  {}", path.relative_to(directory))

            return Discovery(score=0.5, data={'config': None})

        if not found:
            # wp-login.php without wp-config.php is still a WordPress tree,
            # just one we cannot describe a database for.
            if (directory / 'wp-login.php').exists():
                return Discovery(score=0.5, data={'config': None})

            return Discovery(score=0.0)

        config_file = found[0]
        config = read_php_defines(config_file, WP_KEYS)
        database = config.get('DB_NAME')

        discovery = Discovery(score=1.0, data={
            'config': str(config_file.relative_to(directory)),
            # What identifies this directory as the one the plan describes.
            'markers': [str(config_file.relative_to(directory))],
        })

        if not database:
            self.log("{} has no DB_NAME", config_file.relative_to(directory))
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
            source='{}:DB_PASSWORD'.format(config_file.relative_to(directory)),
        )

        self.log("{}: {} on {}", config_file.relative_to(directory),
                 database, host or 'localhost')

        return discovery

    def secrets(self, request):
        recorded = (request.data or {}).get('config')

        if not recorded:
            return {}

        config_file = request.directory / recorded

        if not config_file.exists():
            return {}

        config = read_php_defines(config_file, WP_KEYS)

        return {'mysql.password': config.get('DB_PASSWORD')}


def main():
    sys.exit(run(WordpressPlugin))
