#!/usr/bin/env python3

"""
Save MySQL database dump and user info for restoration later.

Usage:
    archive-mysql [options] DATABASE DUMP_DIRECTORY
    archive-mysql [options] DATABASES... -o OUT_DUMP
    archive-mysql --check DIRECTORY
    archive-mysql -h | --help
    archive-mysql --version

Options:
    -c OUT_CONFIG   Write config to the specified file [default: -]
    -o OUT_DUMP     Write dumps to the specified directory.
    --user USER     Username.
    --pass PASS     Use this password.
    --host HOST     Use this host [default: localhost].
    --users USERS   A comma-separated lists of user=password pairs.
                    See USER-PASSWORD PAIRS below to
    --check DIRECTORY   Check if this plugin can archive this directory.
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

import subprocess

from ..config.archive_database import ArchiveDatabaseConfigFile
from ..files import smart_open
from ..console import getpass_until_valid, getpass_twice_until_valid, input_until_valid
from ..strings import _regex_splitter

import sys, os
import getpass

def main():
    arguments = docopt(__doc__, version=VERSION)

    if arguments['--check']:
        print('0.0')
        return

    conf = ArchiveDatabaseConfigFile()

    conf.dbtype = 'MySQL'

    conf.databases = arguments['DATABASES'] or [arguments['DATABASE']]

    user = None
    password = None

    for database in conf.databases:
        print("mysql: dump database {}...".format(database))

        user = arguments['--user'] or input_until_valid(
            'User: ',
            "User cannot be empty.",
            default=user
        )

        password = arguments['--pass'] or getpass_until_valid(
            'Password: ',
            "Password cannot be empty.",
            default=password
        )

        subprocess.check_call([
            'mysqldump',
            '--user={}'.format(user),
            '--password={}'.format(password),
            '--host={}'.format(arguments['--host']),
            '-r', os.path.join(
                arguments['DUMP_DIRECTORY'] or arguments['-o'],
                "{}.sql".format(database)
            ),
            '--databases', database,
        ])

    if arguments['--users']:
        for user in _regex_splitter.split(arguments['--users']):
            t = user.split('=')

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
