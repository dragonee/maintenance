#!/usr/bin/env python3
"""
Move files from backup to another directory on remote server.

Usage:
    eternalize [options] FILE...

TARGET can be:
    Folder
    Folder/Directory, which will create a directory and put file inside
    Folder/*, which will try to match the closest directory

Options:
    -p          Preserve the file on the computer.
    -s SERVER   Specify server configuration.
    -d          Dry run (use this for testing).
    -h, --help  Display this text.
    --version   Display version information.
"""

VERSION = '1.0'

import re
import os
import sys
import json
import shutil
import telnetlib
import subprocess
from pathlib import Path
from pprint import pprint

import codecs

from io import BytesIO

from docopt import docopt

from itertools import chain, islice, repeat
from operator import itemgetter

from fabric import Connection
from ..transfer import Transfer

from ..config.eternalize import EternalizeConfigFile


def mapresponse(getter, default=None, args=[], kwargs={}, **funcs):
    def _default(x, *a, **k):
        raise RuntimeError(getter(x).lower())
    default_handler = default or _default
    return lambda x: funcs.get(getter(x).lower(), default_handler)(x, *args, **kwargs)

def handle_ok(response, c, file=None, **kwargs):
    print("from: {}\nto: {}".format(response['from'], response['to']))

    t = Transfer(c)

    if not response['directory_exists']:
        c.run('mkdir -p "{}"'.format(response['directory']))

    if file.is_dir():
        t.rsync_put(file, Path(response['from']))

    return c.run('mv "{}" "{}"'.format(response['from'], response['to'])).ok

def handle_emoved(response, c, file=None, **kwargs):
    print("from: {}\nto: {}".format(response['from'], response['to']))

    t = Transfer(c)

    if file.is_dir():
        t.rsync_put(file, Path(response['to']))

    return True

def handle_enoent(response, c, file=None, **kwargs):
    print("from: {}\nto: {}".format(response['from'], response['to']))

    c.run('mkdir -p "{}"'.format(response['directory']))

    t = Transfer(c)

    if file.is_dir():
        t.rsync_put(file, response['to'])
    else:
        t.rsync_put(file, response['directory'])

    return True

# XXX should do three-way merge
def handle_eexists(response, c, **kwargs):
    if response['files_differ']:
        print("EEXIST: There is another file in {}.".format(response['to']))
        return False

    # do not delete remote file, next synchronization will handle it

    return True

def handle_einval(response, c, **kwargs):
    print("EINVAL: Couldn't find matching path for {}.".format(response['from']))

    return False

def handle_unknown(response, c, **kwargs):
    print("Unknown status {}".format(response['status']))

    return False

def perform_move_command(
    c, file, local_base_path,
    remote_backup_path, remote_target_path, remote_pattern,
    dry=False
):

    relative_path = file.relative_to(local_base_path)

    if remote_pattern:
        command = 'eternalize-locate -f json -p "{pattern}" -b "{base}" "{file}" "{tgt}"'
    else:
        command = 'eternalize-locate -f json -b "{base}" "{file}" "{tgt}"'

    result = c.run(command.format(
        base=remote_backup_path,
        file=relative_path,
        tgt=remote_target_path,
        pattern=remote_pattern
    ), hide='stdout')

    response = json.loads(result.stdout)

    print(response['status'])

    if dry:
        handler = pprint
    else:
        handler = mapresponse(
            itemgetter('status'),
            args=[c],
            kwargs={'file': file},
            ok=handle_ok,
            enoent=handle_enoent,
            eexist=handle_eexists,
            einval=handle_einval,
            emoved=handle_emoved,
            default=handle_unknown,
        )

    return handler(response)


def remove_file(p):
    if p.is_dir():
        shutil.rmtree(str(p))
    else:
        p.unlink()


def n(iter, n=2):
    return islice(chain(iter, repeat(None)), n)


def target_config_from_argument(conf, server, argument):
    """Return full target config with keys (path, pattern)."""

    target, pattern = n(argument.split('/', 1))

    dct = conf.target(server, target)
    dct.update({
        'pattern': pattern
    })

    return dct


def load_targets_from_remote(c, conf):
    t = Transfer(c)

    cache = BytesIO()

    t.get('.eternalize.ini', cache)

    cache.seek(0)

    reader = codecs.getreader('utf-8')

    conf.add_target_file(reader(cache))


def main():
    arguments = docopt(__doc__, version=VERSION)

    conf = EternalizeConfigFile()

    server = arguments['-s'] or conf.server

    server_config = conf.servers[server]

    with Connection(
        server_config['host'],
        user=server_config['user'],
        port=server_config['port']
    ) as c:

        load_targets_from_remote(c, conf)

        for name in arguments['FILE'][:-1]:
            p = Path(name).expanduser().resolve(strict=True)
            base = Path(server_config['local_path']).expanduser().resolve(strict=True)

            target_config = target_config_from_argument(conf, server, arguments['FILE'][-1])

            status = perform_move_command(
                c,
                p,
                local_base_path=base,
                remote_backup_path=server_config['remote_path'],
                remote_target_path=target_config['path'],
                remote_pattern=target_config['pattern'],
                dry=arguments['-d'],
            )

            if status:
                print("Would delete file.")

            if status and not any([arguments['-p'], arguments['-d']]):
                remove_file(p)



