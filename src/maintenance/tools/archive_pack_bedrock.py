#!/usr/bin/env python3

"""
Pack an existing Bedrock Wordpress installation.

Usage:
    archive-pack-bedrock [--db DATABASES] [-o OUTPUT] -m META_DIR DIR
    archive-pack-bedrock --check DIR
    archive-pack-bedrock -h | --help
    archive-pack-bedrock --version

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

from environs import Env

from ..strings import _regex_splitter


def check_for_existence(paths):
    if any(map(lambda x: x.exists(), paths)):
        return 1.0

    return 0.0


def get_config_from_env_file(path):
    env = Env()
    env.read_env(path)

    config = {
        'DB_NAME': env('DB_NAME'),
        'DB_HOST': env('DB_HOST', default='localhost'),
        'DB_USER': env('DB_USER'),
        'DB_PASSWORD': env('DB_PASSWORD'),
    }

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
            path/'config/application.php',
            path/'web/wp/wp-login.php'
        ])

        print(value)
        return

    meta = Path(arguments['-m'])

    if (path/'.env').exists():
        wp_config = get_config_from_env_file(path/'.env')

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

