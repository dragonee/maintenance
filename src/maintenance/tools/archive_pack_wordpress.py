#!/usr/bin/env python3

"""
Pack an existing Wordpress installation.

Usage:
    archive-pack-wordpress [--db DATABASES] [-o OUTPUT] -m META_DIR DIR
    archive-pack-wordpress --check DIR
    archive-pack-wordpress -h | --help
    archive-pack-wordpress --version

Options:
    --check         Check if directory is a Wordpress instalation, return 0..1.
    -m META_DIR     Use this directory for meta storage.
    -o OUTPUT       Write archive to this file.
    --db DATABASES  A comma-separated list of databases.
    -h, --help      Display this message.
    --version       Show version information.
"""

VERSION = '1.0'

from docopt import docopt

from pathlib import Path
import sys

import subprocess
import re

from ..strings import _regex_splitter

def check_for_existence(paths):
    if any(map(lambda x: x.exists(), paths)):
        return 1.0

    return 0.0

regex = re.compile(r'define\s*\([\s\'"]+(?P<name>\w+)[\'",\s]+(?P<value>[^"\']+)[\'",\s]+\)')

def get_config_from_wp_config_file(path):
    config = {
        'DB_NAME': None,
        'DB_HOST': None,
        'DB_USER': None,
        'DB_PASSWORD': None,
    }

    with path.open() as f:
        for line in f:
            m = regex.match(line.strip())

            if not m:
                continue

            if m.group(1) not in config.keys():
                continue

            config[m.group(1)] = m.group(2)

    return config

def arg_from_config(config, key, arg):
    if config[key]:
        return [arg, config[key]]

    return []

def main():
    arguments = docopt(__doc__, version=VERSION)

    path = Path(arguments['DIR']).resolve()

    if arguments['--check']:
        value = check_for_existence([
            path/'wp-config.php',
            path/'wp-login.php'
        ])

        print(value)
        return

    meta = Path(arguments['-m'])

    if (path/'wp-config.php').exists():
        wp_config = get_config_from_wp_config_file(path/'wp-config.php')

        users_args = []
        if 'DB_USER' in wp_config and 'DB_PASSWORD' in wp_config:
            users_args = ['--users', "{}={}".format(wp_config['DB_USER'], wp_config['DB_PASSWORD'])]

        additional_dbs = []
        if arguments['--db']:
            additional_dbs = _regex_splitter.split(arguments['--db'])

        dbs = set([wp_config['DB_NAME']] + additional_dbs)

        subprocess.check_call([
            'archive-mysql',
            '-c', str(meta/'mysql.ini'),
        ] + arg_from_config(wp_config, 'DB_HOST', '--host') \
        + arg_from_config(wp_config, 'DB_USER', '--user') \
        + arg_from_config(wp_config, 'DB_PASSWORD', '--pass') \
        + users_args + list(dbs) + [
            '-o', str(meta),
        ])

    output = arguments['-o'] or path.parent/"{}.tar.gz".format(path.name)

    print('compress: create archive at {}'.format(output))

    subprocess.check_call([
        'archive-compress', '-v',
        '-f', 'gz',
        '-m', str(meta),
        str(path),
        str(output)
    ])

