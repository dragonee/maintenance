#!/usr/bin/env python3

"""
Dump and later drop the PostgreSQL databases belonging to an installation.

Works the same way as archive-plugin-mysql: a detector plugin publishes
postgresql.databases during discovery, or this plugin reads a DATABASE_URL
out of a dotenv file in the directory itself. Django, Rails and Laravel
projects are usually recognised by that alone.

pg_dump and psql are driven through a 0600 PGPASSFILE rather than a
password on the command line or in the environment.

Where a machine runs several clusters side by side, every call names its
port and uses the client binary matching that cluster's major version --
pg_dump refuses to dump a server newer than itself, and two clusters
routinely hold databases of the same name, an old application on one and
its replacement on another.

Removal needs a superuser. If a password is available -- from
ARCHIVE_POSTGRESQL_SUPERUSER_PASSWORD, from ~/.archive.ini, or from a prompt
-- it connects over TCP with it. If none is, it falls back to
`sudo -u postgres psql`, which is how a default install expects to be
administered: the postgres role uses peer authentication and has no password
to give. Set postgresql.superuser_auth in the plan to force either way.

Open connections to the database are terminated first, because PostgreSQL
refuses to drop a database anyone is still using.
"""

VERSION = '2.0'

import os
import re
import subprocess
import sys
import tempfile

from configparser import ConfigParser
from pathlib import Path

from ..archive.detect import find_dsn, read_env_file
from ..archive.plugin import Discovery, Plugin, run
from ..config.archive_database import ArchiveDatabaseConfigFile


IDENTIFIER = re.compile(r'^[A-Za-z_][A-Za-z0-9_$]*$')

DEFAULT_PORT = 5432


def quote_literal(value):
    "Single-quote a string for a statement that cannot take parameters."
    return "'{}'".format(str(value).replace("'", "''"))


def quote_identifier(name):
    "Double-quote an identifier, refusing anything that would need escaping."
    if not IDENTIFIER.match(name or ''):
        raise ValueError("Refusing to use {!r} as a PostgreSQL identifier".format(name))

    return '"{}"'.format(name)


def cluster_version(port):
    """Major version of the local cluster listening on ``port``.

    One machine can run several clusters at once, and pg_dump refuses to
    dump a server newer than itself. Debian's /usr/bin/pg_dump is a wrapper
    that picks a binary per cluster, but only when no explicit host was
    given -- and we give one -- so the version has to be resolved here.
    """
    try:
        output = subprocess.check_output(
            ['pg_lsclusters', '--no-header'],
            universal_newlines=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    for line in output.splitlines():
        fields = line.split()

        if len(fields) >= 3 and fields[2] == str(port):
            return fields[0]

    return None


def program_for(name, port):
    "The client binary matching the cluster on ``port``, if there is one."
    version = cluster_version(port)

    if version:
        candidate = Path('/usr/lib/postgresql') / version / 'bin' / name

        if candidate.exists():
            return str(candidate)

    return name


def superuser_from_archive_ini():
    "Optional [general] postgresql_user / postgresql_password in ~/.archive.ini."
    reader = ConfigParser()
    reader.read(['/etc/archive.ini', str(Path.home() / '.archive.ini')])

    try:
        general = reader['general']
    except KeyError:
        return None, None

    return general.get('postgresql_user'), general.get('postgresql_password')


class PostgresqlPlugin(Plugin):
    name = 'postgresql'
    order = 50
    version = VERSION

    # -- discovery -------------------------------------------------------

    def discover(self, request):
        databases = request.var('postgresql.databases') or []
        host = request.var('postgresql.host') or 'localhost'
        port = request.var('postgresql.port') or DEFAULT_PORT
        user = request.var('postgresql.user')

        if not databases:
            dsn = self.from_dotenv(request.directory)

            if dsn:
                databases = [dsn['database']]
                host = dsn['host']
                port = dsn['port'] or DEFAULT_PORT
                user = dsn['user']

        if not databases:
            return Discovery(score=0.0)

        discovery = Discovery(score=1.0, data={
            'databases': list(databases),
            'host': host,
            'port': port,
            'user': user,
        })

        discovery.var('postgresql.databases', list(databases))
        discovery.var('postgresql.host', host)
        discovery.var('postgresql.port', port)
        discovery.var('postgresql.user', user)
        discovery.var('postgresql.version', cluster_version(port))
        discovery.var('postgresql.superuser', 'postgres')

        # auto  use a password if one turns up, otherwise sudo/peer
        # password  insist on a password
        # peer      always go through sudo -u, never ask for a password
        discovery.var('postgresql.superuser_auth', 'auto')
        discovery.var('postgresql.store_credentials', False)

        discovery.require_secret(
            'postgresql.password',
            source='.env:DATABASE_URL',
        )

        discovery.require_secret(
            'postgresql.superuser_password',
            stage='remove',
            source='~/.archive.ini [general] postgresql_password',
            env_var='ARCHIVE_POSTGRESQL_SUPERUSER_PASSWORD',
            prompt='PostgreSQL superuser password (empty to use sudo): ',
            optional=True,
        )

        self.log("{} on {}:{}", ', '.join(databases), host, port)

        return discovery

    def from_dotenv(self, directory):
        env_file = directory / '.env'

        if not env_file.exists():
            return None

        return find_dsn(read_env_file(env_file), engine='postgresql')

    # -- secrets ---------------------------------------------------------

    def secrets(self, request):
        wanted = request.requirements()
        found = {}

        if 'postgresql.password' in wanted:
            dsn = self.from_dotenv(request.directory)

            if dsn and dsn.get('password'):
                found['postgresql.password'] = dsn['password']

        if 'postgresql.superuser_password' in wanted:
            _, password = superuser_from_archive_ini()

            if password:
                found['postgresql.superuser_password'] = password

        return found

    # -- password file ---------------------------------------------------

    def passfile(self, directory, host, port, database, user, password):
        """A 0600 .pgpass, so nothing sensitive lands in argv or the environment."""
        handle, path = tempfile.mkstemp(dir=str(directory), prefix='pgpass-')

        def escape(field):
            return str(field).replace('\\', '\\\\').replace(':', '\\:')

        with os.fdopen(handle, 'w') as fp:
            fp.write('{}:{}:{}:{}:{}\n'.format(
                escape(host), escape(port), escape(database),
                escape(user or ''), escape(password or ''),
            ))

        return Path(path)

    def environ(self, passfile):
        env = os.environ.copy()
        env['PGPASSFILE'] = str(passfile)

        return env

    # -- packing ---------------------------------------------------------

    def pack(self, request):
        meta = request.meta_dir / 'postgresql'
        meta.mkdir(parents=True, exist_ok=True)

        data = request.data
        databases = data.get('databases') or []
        host = data.get('host') or 'localhost'
        port = data.get('port') or DEFAULT_PORT
        user = data.get('user')
        password = request.secret('postgresql.password')

        conf = ArchiveDatabaseConfigFile()
        conf.dbtype = 'PostgreSQL'

        for database in databases:
            self.log("dumping {}...", database)

            passfile = self.passfile(
                request.meta_dir, host, port, database, user, password
            )

            try:
                subprocess.check_call([
                    program_for('pg_dump', port),
                    '--host', str(host),
                    '--port', str(port),
                    '--username', user or 'postgres',
                    '--no-password',
                    '--create',
                    '--file', str(meta / '{}.sql'.format(database)),
                    database,
                ], env=self.environ(passfile))
            finally:
                passfile.unlink()

        conf.databases = list(databases)

        if user:
            conf.users = {
                user: password if request.var('postgresql.store_credentials') else ''
            }

        with (request.meta_dir / 'postgresql.ini').open('w') as fp:
            conf.write(fp)

        self.log("dumped {} database(s) to meta/postgresql/", len(databases))

        return {}

    # -- removal ---------------------------------------------------------

    def psql(self, request, statement, database='postgres'):
        """Run one statement as the superuser.

        With a password, over TCP with a 0600 PGPASSFILE. Without one,
        through `sudo -u postgres psql`, which is how a default PostgreSQL
        install expects to be administered: the postgres role uses peer
        authentication and has no password to give.
        """
        superuser = request.var('postgresql.superuser') or 'postgres'
        auth = request.var('postgresql.superuser_auth') or 'auto'
        password = request.secret('postgresql.superuser_password')

        if auth == 'password' and not password:
            raise RuntimeError(
                "postgresql.superuser_auth is 'password' but no password was "
                "resolved; set ARCHIVE_POSTGRESQL_SUPERUSER_PASSWORD or use 'peer'."
            )

        port = request.data.get('port') or DEFAULT_PORT

        if auth == 'peer' or not password:
            return self.psql_as_peer(superuser, database, statement, port)

        return self.psql_with_password(request, superuser, database, statement, password)

    def psql_with_password(self, request, superuser, database, statement, password):
        host = request.data.get('host') or 'localhost'
        port = request.data.get('port') or DEFAULT_PORT

        passfile = self.passfile(
            Path(tempfile.gettempdir()), host, port, '*', superuser, password
        )

        try:
            subprocess.check_call([
                program_for('psql', port),
                '--host', str(host),
                '--port', str(port),
                '--username', superuser,
                '--no-password',
                '--dbname', database,
                '--quiet',
                '--command', statement,
            ], env=self.environ(passfile))
        finally:
            passfile.unlink()

    def psql_as_peer(self, superuser, database, statement, port):
        """Local socket connection as the postgres OS user.

        The port is essential, not cosmetic. Where several clusters run
        side by side they routinely hold databases of the same name -- an
        old application on one and its replacement on another -- and a psql
        with no port silently talks to whichever cluster is the default.
        Dropping a database is not something to do in the wrong one.

        No --host: over a Unix socket the port still selects the cluster,
        peer authentication keeps working, and pg_wrapper picks the
        matching binary of its own accord.
        """
        command = [
            program_for('psql', port),
            '--port', str(port),
            '--dbname', database,
            '--quiet',
            '--command', statement,
        ]

        if os.geteuid() != 0 or superuser != 'postgres':
            command = ['sudo', '-u', superuser] + command

        subprocess.check_call(command)

    def remove(self, request):
        databases = request.data.get('databases') or []
        owner = request.data.get('user')

        superuser = request.var('postgresql.superuser') or 'postgres'
        auth = request.var('postgresql.superuser_auth') or 'auto'

        if auth != 'peer' and request.secret('postgresql.superuser_password'):
            self.log("connecting as {} with a password", superuser)
        else:
            self.log("going through sudo -u {} ({})", superuser,
                     'forced by postgresql.superuser_auth' if auth == 'peer'
                     else 'no password available')

        for database in databases:
            quoted = quote_identifier(database)

            self.log("dropping database {}...", database)

            # PostgreSQL will not drop a database that anyone is connected
            # to, and a web application usually still has a pool open.
            self.psql(request,
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = {} AND pid <> pg_backend_pid();".format(
                    quote_literal(database)
                ))

            self.psql(request, 'DROP DATABASE IF EXISTS {};'.format(quoted))

        if owner and owner not in ('postgres', request.var('postgresql.superuser')):
            self.log("dropping role {}...", owner)
            self.psql(request, 'DROP ROLE IF EXISTS {};'.format(
                quote_identifier(owner)
            ))

        return {}


def main():
    sys.exit(run(PostgresqlPlugin))
