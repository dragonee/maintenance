#!/usr/bin/env python3
"""
Move files from backup to another directory on remote server.

Usage:
    eternalize [options] [FILE...]
    eternalize add [options] TARGET PATH

When called without FILE arguments, displays available targets on the remote server.
The 'add' command appends a new target configuration to the remote .eternalize.ini file.

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

import json
import shutil
import codecs
import subprocess

from pathlib import Path
from pprint import pprint

from io import BytesIO

from itertools import chain, islice, repeat
from operator import itemgetter

from docopt import docopt

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


def handle_eexists(response, c, **kwargs):
    return c.run('eternalize-resolve-conflict "{}" "{}"'.format(response['from'], response['to'])).ok


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


def display_targets(conf, server):
    """Display available targets for the specified server."""
    print(f"Available targets for server '{server}':\n")

    # Filter targets that belong to this server
    server_prefix = f"{server}:"
    server_targets = {
        key[len(server_prefix):]: value
        for key, value in conf.targets.items()
        if key.startswith(server_prefix)
    }

    if not server_targets:
        print("  No targets configured for this server.")
        return

    for target_name, target_config in sorted(server_targets.items()):
        path = target_config.get('path', 'N/A')
        print(f"  {target_name:20s} -> {path}")


def add_target(c, server, target_name, target_path):
    """Add a new target configuration to the remote .eternalize.ini file."""
    from configparser import ConfigParser

    t = Transfer(c)

    # Fetch the remote .eternalize.ini file
    cache = BytesIO()
    t.get('.eternalize.ini', cache)
    cache.seek(0)

    # Parse the config file
    reader = codecs.getreader('utf-8')
    parser = ConfigParser()
    parser.read_file(reader(cache))

    # Add the new target section
    section_name = f"{server}:{target_name}"

    if parser.has_section(section_name):
        print(f"Warning: Target '{target_name}' already exists for server '{server}'.")
        print(f"Updating path to: {target_path}")
    else:
        parser.add_section(section_name)
        print(f"Adding target '{target_name}' for server '{server}'.")

    parser.set(section_name, 'path', target_path)

    # Write the updated config back to a buffer
    output = BytesIO()
    writer = codecs.getwriter('utf-8')
    wrapped_output = writer(output)
    parser.write(wrapped_output)
    output.seek(0)

    # Upload the modified file back to the remote server
    t.put(output, '.eternalize.ini')

    print(f"Successfully updated remote .eternalize.ini")
    print(f"  {target_name:20s} -> {target_path}")


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

        # Handle 'add' command
        # Check both the 'add' argument and if FILE[0] == 'add'
        if arguments.get('add') or (arguments['FILE'] and arguments['FILE'][0] == 'add'):
            if arguments.get('add'):
                target_name = arguments['TARGET']
                target_path = arguments['PATH']
            else:
                # Parse from FILE when docopt matched the first pattern
                if len(arguments['FILE']) < 3:
                    print("Error: 'add' command requires TARGET and PATH arguments")
                    return
                target_name = arguments['FILE'][1]
                target_path = arguments['FILE'][2]

            add_target(c, server, target_name, target_path)
            return

        load_targets_from_remote(c, conf)

        # If no files provided, display targets and exit
        if not arguments['FILE']:
            display_targets(conf, server)
            return

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

