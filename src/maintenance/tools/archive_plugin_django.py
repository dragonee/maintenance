#!/usr/bin/env python3

"""
Read a Django settings module and describe the database it configures.

Django keeps its database in a DATABASES dict, usually in a settings
package split across several files. Where that dict is written out
literally this plugin reads it; where it is computed -- `env.db()` and
friends -- there is nothing to read, and the credentials are in an env
file that archive-plugin-env should be pointed at instead:

    archive discover /srv/example.com \\
        --env /srv/environments/example/example.env

The settings file is parsed, never imported or executed. Importing a
project's settings to find out where its database lives would run whatever
that project runs at import time, on a machine where the application is
being decommissioned; ast.literal_eval reads the dict and refuses anything
that is not a plain value.

sqlite is recognised and deliberately ignored: the database is a file
inside the directory, so the archive already contains it.
"""

VERSION = '1.0'

import ast
import sys

from pathlib import Path

from ..archive.plugin import Discovery, Plugin, run


ENGINES = {
    'django.db.backends.postgresql': 'postgresql',
    'django.db.backends.postgresql_psycopg2': 'postgresql',
    'django.contrib.gis.db.backends.postgis': 'postgresql',
    'django.db.backends.mysql': 'mysql',
    'django.contrib.gis.db.backends.mysql': 'mysql',
}

DEFAULT_PORTS = {'mysql': 3306, 'postgresql': 5432}

#: Where a DATABASES dict tends to live, in the order worth trying.
#:
#: settings/local.py is deliberately absent. By convention it is a
#: developer's own override, and it routinely names a database that only
#: exists on a laptop or inside a compose file -- HOST: 'db' and the like.
#: Reading it would aim a dump at a host that does not exist here, or
#: worse, at one that does and is something else entirely.
SETTINGS_PATTERNS = (
    '*/settings/db.py',
    '*/settings/database.py',
    '*/settings.py',
    '*/settings/base.py',
    '*/settings/production.py',
    '*/settings/__init__.py',
)

MARKERS = ('manage.py', 'manage.dist.py')


def databases_in(path):
    """The DATABASES dict from a settings file, or None.

    Returns None both when the file has no DATABASES and when it has one
    that is computed rather than written out; the caller cannot act on
    either, and the difference is reported to the user, not to the plan.
    """
    try:
        tree = ast.parse(path.read_text(errors='replace'), filename=str(path))
    except (OSError, SyntaxError):
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue

        for target in node.targets:
            if not isinstance(target, ast.Name) or target.id != 'DATABASES':
                continue

            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                return None

            if isinstance(value, dict):
                return value

    return None


def settings_files(directory):
    for pattern in SETTINGS_PATTERNS:
        for path in sorted(directory.glob(pattern)):
            if path.is_file():
                yield path


class DjangoPlugin(Plugin):
    name = 'django'

    #: A detector: it describes an installation for the database plugins
    #: to act on, and stands aside for archive-plugin-env if it cannot.
    order = 10

    version = VERSION

    def looks_like_django(self, directory):
        if any((directory / marker).exists() for marker in MARKERS):
            return True

        return any(True for _ in directory.glob('*/settings/*.py'))

    def find_database(self, directory):
        "The first settings file that spells its default database out."
        for path in settings_files(directory):
            databases = databases_in(path)

            if not databases:
                continue

            default = databases.get('default')

            if isinstance(default, dict) and default.get('NAME'):
                return path, default

        return None, None

    def discover(self, request):
        directory = request.directory

        if not self.looks_like_django(directory):
            return Discovery(score=0.0)

        path, default = self.find_database(directory)

        if default is None:
            # Django, but the database is computed. Claim the directory
            # weakly so the plan records what this is, and say why there
            # is nothing more.
            self.log("settings do not spell out a database; "
                     "point --env at the env file that does")

            return Discovery(score=0.5, data={'database': None})

        backend = default.get('ENGINE') or ''
        engine = ENGINES.get(backend)
        relative = path.relative_to(directory)

        if engine is None:
            if 'sqlite' in backend:
                self.log("{}: sqlite, already inside the archive", relative)
            else:
                self.log("{}: unsupported engine {}", relative, backend)

            return Discovery(score=0.5, data={'database': None})

        host = default.get('HOST') or 'localhost'
        port = default.get('PORT') or DEFAULT_PORTS[engine]

        try:
            port = int(port)
        except (TypeError, ValueError):
            port = DEFAULT_PORTS[engine]

        discovery = Discovery(score=1.0, data={
            'database': {'engine': engine, 'settings': str(relative)},
        })

        discovery.var('{}.databases'.format(engine), [default['NAME']])
        discovery.var('{}.host'.format(engine), host)
        discovery.var('{}.port'.format(engine), port)
        discovery.var('{}.user'.format(engine), default.get('USER'))

        if default.get('PASSWORD'):
            discovery.require_secret(
                '{}.password'.format(engine),
                source='{}:DATABASES'.format(relative),
            )

        self.log("{}: {} {} on {}:{}", relative, engine, default['NAME'], host, port)

        return discovery

    def secrets(self, request):
        described = request.data.get('database') or {}
        settings = described.get('settings')
        engine = described.get('engine')

        if not settings or not engine:
            return {}

        path = request.directory / settings

        if not path.exists():
            return {}

        databases = databases_in(path)
        default = (databases or {}).get('default') or {}

        if not default.get('PASSWORD'):
            return {}

        return {'{}.password'.format(engine): default['PASSWORD']}


def main():
    sys.exit(run(DjangoPlugin))
