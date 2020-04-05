#!/usr/bin/env python3

"""
Save MySQL database dump and user info for restoration later.

Usage:
    archive-mysql [options] DATABASE DUMP_DIRECTORY
    archive-mysql [options] DATABASES... -o DUMP_DIR
    archive-mysql -h | --help
    archive-mysql --version

Options:
    -o DUMP_DIR     Put output dumps into this directory.
    -c OUT_CONFIG   Write config to the specified file [default: -]
    --user USER     Username.
    --pass PASS     Use this password.
    --host HOST     Use this host [default: localhost].
    --users USERS   A comma-separated lists of user=password pairs.
                    See USER-PASSWORD PAIRS below to
    -h, --help      Display this message.
    --version       Show version information.

USER-PASSWORD PAIRS

There are three ways to specify user-password pairs:

user1, ...          Will ask for passwords.
user1=pass1, ...    Will store passwords given.
user1=, ...         Won't ask now, will ask for a new one when unarchiving.

"""

VERSION = '1.0'

from docopt import docopt
import mysql.connector
from mysql.connector import errorcode


import subprocess

from ..config.archive_database import ArchiveDatabaseConfigFile
from ..files import smart_open
from ..console import getpass_until_valid, getpass_twice_until_valid, input_until_valid, ask_for
from ..strings import _regex_splitter

import sys, os
import getpass

from functools import reduce

class CannotDumpDatabase(RuntimeError):
    pass

class UserCancelledDumping(CannotDumpDatabase):
    pass

class DatabaseDoesNotExist(CannotDumpDatabase):
    credentials = None

def generate_credentials(credentials_list):
    credentials = None

    for credentials in credentials_list:
        yield credentials

    user = None
    password = None

    if credentials:
        user, password = credentials

    try:
        while True:
            print('Please provide valid credentials (Ctrl-C to exit).')
            user = input_until_valid(
                'User: ',
                "User cannot be empty.",
                default=user
            )

            password = getpass_until_valid(
                'Password: ',
                "Password cannot be empty.",
                default=password
            )

            yield (user, password)
    except KeyboardInterrupt:
        raise UserCancelledDumping

def check_database_access(database, host, credentials_list):
    def _check_access(creds):
        user, password = creds

        try:
            cnx = mysql.connector.connect(
                user=user,
                password=password,
                host=host,
                database=database,
            )
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                return None
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                print("Database {} does not exist.".format(database))

                exc = DatabaseDoesNotExist("{} does not exist.".format(database))
                exc.credentials = (user, password)
                raise exc
            else:
                raise
        else:
            cnx.close()

        return creds

    credentials_iterator = generate_credentials(credentials_list)

    first_matching_credentials = filter(None, map(_check_access, credentials_iterator))

    user, password = next(first_matching_credentials)

    return (user, password)


def dump_single_database(database, host, credentials_list, output_file):
    credentials = check_database_access(database, host, credentials_list)

    subprocess.check_call([
        'mysqldump',
        '--user={}'.format(credentials[0]),
        '--password={}'.format(credentials[1]),
        '--host={}'.format(host),
        '-r', output_file,
        '--databases', database,
    ])

    return credentials

def main():
    arguments = docopt(__doc__, version=VERSION)

    conf = ArchiveDatabaseConfigFile()

    conf.dbtype = 'MySQL'

    databases = arguments['DATABASES'] or [arguments['DATABASE']]
    dumped_databases = []

    def _run_dump_with_cache(last_credentials, database):
        print("mysql: dump database {}...".format(database))

        first_credentials = []
        if arguments['--user'] and arguments['--pass']:
            first_credentials = [
                (arguments['--user'], arguments['--pass'])
            ]

        if last_credentials:
            last_credentials = [last_credentials]
        else:
            last_credentials = []

        credentials = None

        try:
            credentials = dump_single_database(
                database,
                arguments['--host'],
                first_credentials + last_credentials,
                os.path.join(
                    arguments['DUMP_DIRECTORY'] or arguments['-o'],
                    "{}.sql".format(database)
                )
            )

            dumped_databases.append(database)

        except (DatabaseDoesNotExist, UserCancelledDumping) as exc:
            print("\nDo you wish to continue the dumping process?")

            if not ask_for(['y', 't'], ['n', 'f'], case_sensitive=False):
                raise UserCancelledDumping("User cancelled dumping all databases.")

            if hasattr(exc, 'credentials'):
                return exc.credentials

            return last_credentials

        return credentials

    try:
        reduce(_run_dump_with_cache, databases, False)

        conf.databases = dumped_databases

    except UserCancelledDumping:
        sys.exit(1)

    if arguments['--users']:
        for user in _regex_splitter.split(arguments['--users']):
            t = user.split('=')

            if t[0] == 'root':
                continue

            if len(t) > 1:
                conf.users[t[0]] = t[1]
            else:
                print("User {}".format(t[0]))
                conf.users[t[0]] = getpass_twice_until_valid(
                    "New password: ",
                    "Password cannot be empty."
                )

    print('')

    with smart_open(filename=arguments['-c'], pipe=sys.stdout, mode='w') as fp:
        conf.write(fp)
