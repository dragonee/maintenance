#!/usr/bin/env python3

"""
Read an env file and describe the database it points at.

Applications keep their credentials in a dotenv file, and often not inside
the directory being archived: a shared environments directory beside the
docroot is a common arrangement, and a site archived without it is a site
that cannot be restored. Point this plugin at the file:

    archive discover /srv/example.com \\
        --env /srv/environments/example/example.env

The file is copied into the archive, and removed with the installation when
it lives outside the directory. A dotenv usually holds far more than a
database password -- API tokens, mail credentials, signing keys -- so the
archive is only as safe as wherever you store it. The plan itself stays
clean: it records the path and the database settings, never a value.

Two shapes are understood, which between them cover most frameworks:

    DATABASE_URL=postgres://user:pass@localhost:5433/example
    DB_CONNECTION=mysql, DB_DATABASE, DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT

A `.env` in the archived directory is picked up automatically, but only
when no earlier plugin has already described a database -- a detector that
understands the application knows better than a generic reader.

Set ARCHIVE_ENV_PATHS to a colon-separated list to always search the same
locations without passing --env every time.
"""

VERSION = '1.0'

import os
import subprocess
import shutil
import sys

from pathlib import Path

from ..archive.detect import find_dsn, read_env_file
from ..archive.plugin import Discovery, Plugin, needs_privilege, remove_command, run


ENGINES = {
    'mysql': 'mysql',
    'mariadb': 'mysql',
    'pgsql': 'postgresql',
    'postgres': 'postgresql',
    'postgresql': 'postgresql',
}

#: Where a name, user or password may be written, most specific first.
NAME_KEYS = ('DB_DATABASE', 'DB_NAME', 'POSTGRES_DB', 'MYSQL_DATABASE')
USER_KEYS = ('DB_USERNAME', 'DB_USER', 'POSTGRES_USER', 'MYSQL_USER')
PASSWORD_KEYS = ('DB_PASSWORD', 'DB_PASS', 'POSTGRES_PASSWORD', 'MYSQL_PASSWORD')
HOST_KEYS = ('DB_HOST', 'POSTGRES_HOST', 'MYSQL_HOST')
PORT_KEYS = ('DB_PORT', 'POSTGRES_PORT', 'MYSQL_PORT')

DEFAULT_PORTS = {'mysql': 3306, 'postgresql': 5432}


def first(config, keys):
    for key in keys:
        value = config.get(key)

        if value:
            return key, value

    return None, None


def database_from(config):
    """Work out what database an env file describes, and how we know.

    Returns the settings plus the key they came from, so the plan can say
    `example.env:DATABASE_URL` rather than merely asserting a password
    exists somewhere.
    """
    dsn = find_dsn(config)

    if dsn and dsn.get('database'):
        return {
            'engine': dsn['engine'],
            'database': dsn['database'],
            'host': dsn['host'] or 'localhost',
            'port': dsn['port'] or DEFAULT_PORTS[dsn['engine']],
            'user': dsn['user'],
            'password': dsn['password'],
            'source_key': 'DATABASE_URL',
        }

    _, name = first(config, NAME_KEYS)

    if not name:
        return None

    connection = (config.get('DB_CONNECTION') or '').lower()

    # No engine named anywhere: DB_NAME with a bare user is the WordPress
    # and Bedrock idiom, so MySQL is the least surprising reading.
    engine = ENGINES.get(connection, 'mysql')

    _, host = first(config, HOST_KEYS)
    _, port = first(config, PORT_KEYS)
    _, user = first(config, USER_KEYS)
    password_key, password = first(config, PASSWORD_KEYS)

    try:
        port = int(port) if port else DEFAULT_PORTS[engine]
    except ValueError:
        port = DEFAULT_PORTS[engine]

    return {
        'engine': engine,
        'database': name,
        'host': host or 'localhost',
        'port': port,
        'user': user,
        'password': password,
        'source_key': password_key or 'DB_PASSWORD',
    }


class EnvPlugin(Plugin):
    name = 'env'

    #: After the application detectors, before the database plugins that
    #: act on what either of them found.
    order = 20

    version = VERSION

    def candidates(self, request):
        "Every env file we were told about, plus the obvious one."
        paths = []

        for entry in list(request.options.get('env') or []):
            paths.append(Path(entry).expanduser())

        for entry in (os.environ.get('ARCHIVE_ENV_PATHS') or '').split(os.pathsep):
            if entry:
                paths.append(Path(entry).expanduser())

        # An in-tree .env only if nothing better has spoken for it.
        already_described = any(
            request.var('{}.databases'.format(engine))
            for engine in ('mysql', 'postgresql')
        )

        if not already_described:
            in_tree = request.directory / '.env'

            if in_tree.exists():
                paths.append(in_tree)

        found = []

        for path in paths:
            if not path.exists():
                self.log("{} does not exist, skipping", path)
                continue

            resolved = str(path.resolve())

            if resolved not in found:
                found.append(resolved)

        return found

    def discover(self, request):
        files = self.candidates(request)

        if not files:
            return Discovery(score=0.0)

        discovery = Discovery(score=1.0, data={'files': files})
        described = False

        for path in files:
            settings = database_from(read_env_file(Path(path)))

            if settings is None:
                self.log("{}: no database settings found", Path(path).name)
                continue

            if described:
                # Two env files each naming a database is not something to
                # guess about; the first one wins and the rest are reported.
                self.log("{}: also names {}, ignoring", Path(path).name,
                         settings['database'])
                continue

            engine = settings['engine']

            discovery.var('{}.databases'.format(engine), [settings['database']])
            discovery.var('{}.host'.format(engine), settings['host'])
            discovery.var('{}.port'.format(engine), settings['port'])
            discovery.var('{}.user'.format(engine), settings['user'])

            if settings['password']:
                discovery.require_secret(
                    '{}.password'.format(engine),
                    source='{}:{}'.format(Path(path).name, settings['source_key']),
                )

            discovery.data['database'] = {
                'engine': engine,
                'file': path,
            }

            self.log("{}: {} {} on {}:{}", Path(path).name, engine,
                     settings['database'], settings['host'], settings['port'])

            described = True

        return discovery

    def secrets(self, request):
        described = request.data.get('database') or {}
        path = described.get('file')
        engine = described.get('engine')

        if not path or not Path(path).exists():
            return {}

        settings = database_from(read_env_file(Path(path)))

        if not settings or not settings.get('password'):
            return {}

        return {'{}.password'.format(engine): settings['password']}

    def pack(self, request):
        """Copy each env file into meta/env/, keeping its absolute layout.

        This is the only copy of some of these files, so a failure to read
        one is worth saying loudly rather than passing over.
        """
        meta = request.meta_dir / 'env'
        meta.mkdir(parents=True, exist_ok=True)

        for entry in request.data.get('files') or []:
            source = Path(entry)

            if not source.exists():
                self.log("{} has gone missing, skipping", source)
                continue

            target = meta / source.relative_to(source.anchor)
            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.copy2(str(source), str(target))
            except OSError as e:
                self.log("could not copy {} ({}) -- the archive will be "
                         "incomplete", source, e)
                continue

            self.log("saved {}", source)

        return {}

    def remove(self, request):
        """Delete env files that live outside the archived directory.

        One inside it needs no help: removing the directory takes it too.
        """
        directory = request.directory

        for entry in request.data.get('files') or []:
            path = Path(entry)

            if not path.exists():
                continue

            try:
                path.relative_to(directory)
            except ValueError:
                pass
            else:
                continue

            try:
                command = remove_command(path)
            except ValueError as e:
                self.log("{}", e)
                continue

            self.log("removing {}", path)

            if os.geteuid() != 0 and needs_privilege(path):
                command = ['sudo'] + command

            if subprocess.call(command) != 0:
                self.log("failed to remove {}", path)

        return {}


def main():
    sys.exit(run(EnvPlugin))
