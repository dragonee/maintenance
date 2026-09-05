#!/usr/bin/env python3

"""
Archive and remove the nginx configuration pointing at an installation.

Discovery searches the usual configuration directories for files that name
the directory being archived, and records both the sites-enabled symlink
and the file it points at, since disabling a site and deleting it are
different acts.

Packing copies the configuration into meta/nginx/, keeping the absolute
layout so a restore knows where each file belongs. Removal deletes them,
runs nginx -t, and reloads only if the remaining configuration is valid.

Configuration under /etc is not usually writable by the user running
archive, so removal shells out through sudo unless already running as root.

Set ARCHIVE_NGINX_CONFIG_PATHS to a colon-separated list to search
somewhere other than the standard locations.
"""

VERSION = '2.0'

import sys

from ..archive.plugin import run
from ..archive.webserver import WebserverPlugin


class NginxPlugin(WebserverPlugin):
    name = 'nginx'
    version = VERSION

    config_paths = (
        '/etc/nginx/sites-enabled',
        '/etc/nginx/sites-available',
        '/etc/nginx/conf.d',
        '/usr/local/etc/nginx/servers',
        '/opt/homebrew/etc/nginx/servers',
    )

    test_command = ('nginx', '-t')
    reload_command = ('nginx', '-s', 'reload')

    site_pattern = r'server_name\s+(?P<names>[^;]+);'


def main():
    sys.exit(run(NginxPlugin))
