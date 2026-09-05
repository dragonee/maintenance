#!/usr/bin/env python3

"""
Dump and later drop the MySQL databases belonging to an installation.

The databases are not detected here. A detector plugin (wordpress, bedrock,
or anything you write) publishes mysql.databases, mysql.host and mysql.user
during discovery, and this plugin picks them up. Failing that, it will read
a DATABASE_URL out of a dotenv file in the directory itself.

Credentials never appear in argv, where every user on the machine can read
them out of ps: mysqldump is handed a 0600 defaults file instead.

By default the dump records which users existed but not their passwords, so
nothing secret is written into the archive. Set

    mysql.store_credentials: true

in the plan to embed them, for an installation you expect to restore
unattended.

Removal needs an administrator. If a password is available -- from
ARCHIVE_MYSQL_ROOT_PASSWORD, from ~/.archive.ini, or from a prompt -- it
connects with it. If none is, it falls back to `sudo mysql`, because a great
many servers authenticate root through auth_socket, where there is no
password to give and asking for one would deadlock.

Two plan vars steer this: mysql.admin_user names the administrator, and
mysql.admin_auth is auto (the above), password (insist on one) or socket
(always sudo, never ask).
"""

VERSION = '2.0'

import os
import re
import subprocess
import sys
import tempfile

from pathlib import Path

from ..archive.detect import find_dsn, read_env_file
from ..archive.plugin import Discovery, Plugin, run
from ..config.archive_database import ArchiveDatabaseConfigFile, AdministrativeUserConfigFile


IDENTIFIER = re.compile(r'^[A-Za-z0-9_$-]+$')


def administrator():
    "The administrator name from ~/.archive.ini, if one is configured."
    try:
        return AdministrativeUserConfigFile().user
    except KeyError:
        return None


def quote_identifier(name):
    """Backtick-quote a database or user name, refusing anything exotic.

    DDL cannot be parameterised, so the only safe move is to insist on
    names that need no escaping in the first place.
    """
    if not IDENTIFIER.match(name or ''):
        raise ValueError("Refusing to use {!r} as a MySQL identifier".format(name))

    return '`{}`'.format(name)


class MysqlPlugin(Plugin):
    name = 'mysql'
    order = 50
    version = VERSION

    # -- discovery -------------------------------------------------------

    def discover(self, request):
        databases = request.var('mysql.databases') or []
        host = request.var('mysql.host') or 'localhost'
        user = request.var('mysql.user')

        if not databases:
            dsn = self.from_dotenv(request.directory)

            if dsn:
                databases = [dsn['database']]
                host, user = dsn['host'], dsn['user']

        if not databases:
            return Discovery(score=0.0)

        discovery = Discovery(score=1.0, data={
            'databases': list(databases),
            'host': host,
            'user': user,
        })

        discovery.var('mysql.databases', list(databases))
        discovery.var('mysql.host', host)
        discovery.var('mysql.user', user)
        discovery.var('mysql.store_credentials', False)

        if not request.has_secret('mysql.password'):
            discovery.require_secret(
                'mysql.password',
                source='mysql://{}@{}'.format(user or '?', host),
            )

        discovery.var('mysql.admin_user', administrator() or 'root')

        # auto   use a password if one turns up, otherwise sudo/socket
        # password  insist on a password
        # socket    always go through sudo, never ask for a password
        discovery.var('mysql.admin_auth', 'auto')

        # Dropping a database and its owner is an administrative act, and
        # the credentials for it are deliberately asked for at removal
        # time rather than carried around in the plan.
        #
        # Optional, because a great many servers authenticate their
        # administrator through auth_socket, where no password exists to
        # give and `sudo mysql` is the only way in.
        discovery.require_secret(
            'mysql.root_password',
            stage='remove',
            source='~/.archive.ini [general] mysql_password',
            env_var='ARCHIVE_MYSQL_ROOT_PASSWORD',
            prompt='MySQL administrator password (empty to use sudo): ',
            optional=True,
        )

        self.log("{} on {}", ', '.join(databases), host)

        return discovery

    def from_dotenv(self, directory):
        env_file = directory / '.env'

        if not env_file.exists():
            return None

        return find_dsn(read_env_file(env_file), engine='mysql')

    # -- secrets ---------------------------------------------------------

    def secrets(self, request):
        "Only the administrator password; the site's own comes from its config."
        if 'mysql.root_password' not in request.requirements():
            return {}

        try:
            conf = AdministrativeUserConfigFile()
        except KeyError:
            return {}

        return {'mysql.root_password': conf.password}

    # -- packing ---------------------------------------------------------

    def defaults_file(self, directory, user, password, host, port=None):
        """A 0600 my.cnf, so the password never reaches the command line."""
        handle, path = tempfile.mkstemp(dir=str(directory), prefix='my-', suffix='.cnf')

        with os.fdopen(handle, 'w') as fp:
            fp.write('[client]\n')
            fp.write('user={}\n'.format(user or ''))
            fp.write('password={}\n'.format(password or ''))
            fp.write('host={}\n'.format(host or 'localhost'))

            if port:
                fp.write('port={}\n'.format(port))

        return Path(path)

    def pack(self, request):
        meta = request.meta_dir / 'mysql'
        meta.mkdir(parents=True, exist_ok=True)

        databases = request.data.get('databases') or []
        host = request.data.get('host') or 'localhost'
        user = request.data.get('user')
        password = request.secret('mysql.password')

        defaults = self.defaults_file(
            request.meta_dir, user, password, host, request.var('mysql.port')
        )

        conf = ArchiveDatabaseConfigFile()
        conf.dbtype = 'MySQL'

        try:
            for database in databases:
                self.log("dumping {}...", database)

                subprocess.check_call([
                    'mysqldump',
                    '--defaults-extra-file={}'.format(defaults),
                    '--databases', database,
                    '-r', str(meta / '{}.sql'.format(database)),
                ])

            conf.databases = list(databases)

            if user:
                conf.users = {
                    user: password if request.var('mysql.store_credentials') else ''
                }
        finally:
            defaults.unlink()

        with (request.meta_dir / 'mysql.ini').open('w') as fp:
            conf.write(fp)

        self.log("dumped {} database(s) to meta/mysql/", len(databases))

        return {}

    # -- removal ---------------------------------------------------------

    def statements(self, request):
        "The SQL that tears this installation down, in order."
        databases = request.data.get('databases') or []
        owner = request.data.get('user')

        for database in databases:
            yield ("dropping database {}...".format(database),
                   'DROP DATABASE IF EXISTS {};'.format(quote_identifier(database)))

        if owner and owner != 'root':
            for host in ("'%'", "'localhost'"):
                yield ("dropping user {}@{}...".format(owner, host.strip("'")),
                       "DROP USER IF EXISTS {}@{};".format(
                           quote_identifier(owner), host))

    def remove_with_password(self, request, statements, admin_user, password):
        import mysql.connector

        connection = mysql.connector.connect(
            host=request.data.get('host') or 'localhost',
            user=admin_user,
            password=password,
        )

        try:
            cursor = connection.cursor()

            for message, statement in statements:
                self.log(message)
                cursor.execute(statement)

            connection.commit()
        finally:
            if connection.is_connected():
                connection.close()

    def remove_with_socket(self, request, statements, admin_user):
        """Drop through `sudo mysql`, for servers using auth_socket.

        The statements go in on stdin rather than through --execute, so
        nothing about the installation shows up in ps either.
        """
        script = ''

        for message, statement in statements:
            self.log(message)
            script += statement + '\n'

        if not script:
            return

        command = ['mysql', '--user={}'.format(admin_user), '--batch']

        if os.geteuid() != 0:
            command = ['sudo'] + command

        process = subprocess.Popen(command, stdin=subprocess.PIPE,
                                   universal_newlines=True)
        process.communicate(script)

        if process.returncode != 0:
            raise RuntimeError(
                "{} exited with status {}".format(command[0], process.returncode)
            )

    def remove(self, request):
        admin_user = request.var('mysql.admin_user') or administrator() or 'root'
        auth = request.var('mysql.admin_auth') or 'auto'
        password = request.secret('mysql.root_password')

        if auth == 'password' and not password:
            raise RuntimeError(
                "mysql.admin_auth is 'password' but no password was resolved; "
                "set ARCHIVE_MYSQL_ROOT_PASSWORD or use 'socket'."
            )

        statements = list(self.statements(request))

        if auth != 'socket' and password:
            self.log("connecting as {} with a password", admin_user)
            self.remove_with_password(request, statements, admin_user, password)
        else:
            self.log("going through sudo mysql as {} ({})", admin_user,
                     'forced by mysql.admin_auth' if auth == 'socket'
                     else 'no password available')
            self.remove_with_socket(request, statements, admin_user)

        return {}


def main():
    sys.exit(run(MysqlPlugin))
