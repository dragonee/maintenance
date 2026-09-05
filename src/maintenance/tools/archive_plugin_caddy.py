#!/usr/bin/env python3

"""
Archive and remove the Caddy configuration pointing at an installation.

Behaves exactly like archive-plugin-nginx, differing only in where Caddy
keeps its files and how a site address is written. A Caddyfile that serves
several unrelated sites is copied whole and reported, but removing it would
take the other sites down too, so check what discovery found before running
archive remove.

Set ARCHIVE_CADDY_CONFIG_PATHS to a colon-separated list to search
somewhere other than the standard locations.
"""

VERSION = '2.0'

import sys

from ..archive.plugin import run
from ..archive.webserver import WebserverPlugin


class CaddyPlugin(WebserverPlugin):
    name = 'caddy'
    version = VERSION

    config_paths = (
        '/etc/caddy/Caddyfile',
        '/etc/caddy/conf.d',
        '/etc/caddy/sites-enabled',
        '/usr/local/etc/caddy',
        '/opt/homebrew/etc/caddy',
    )

    test_command = ('caddy', 'validate', '--config', '/etc/caddy/Caddyfile')
    reload_command = ('caddy', 'reload', '--config', '/etc/caddy/Caddyfile')

    #: A site block header: "example.com, www.example.com {"
    site_pattern = r'(?m)^(?P<names>[^\s#{][^{\n]*?)\s*\{'


def main():
    sys.exit(run(CaddyPlugin))
