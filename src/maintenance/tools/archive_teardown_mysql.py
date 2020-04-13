"""
Drop MySQL databases for this archive.

Usage:
    archive-teardown-mysql [options] META_DIR
    archive-teardown-mysql --help
    archive-teardown-mysql --version

Options:
    -r REMOTE  Put file in the.
    --help     Display this message.
    --version  Display version information.
"""

VERSION = '1.0'


from pathlib import Path

from docopt import docopt

import mysql.connector

from ..config.archive_database import ArchiveDatabaseConfigFile, AdministrativeUserConfigFile

class database(object):
    def __init__(self, host, user, password):
        self.host, self.user, self.password = host, user, password

    def __enter__(self):
        self.connection = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            raise_on_warnings=True
        )

        return self.connection.cursor()

    def __exit__(self, *args, **kwargs):
        if self.connection and self.connection.is_connected():
            self.connection.close()


def main():
    arguments = docopt(__doc__, version=VERSION)

    meta_dir = Path(arguments['META_DIR']).expanduser().resolve(strict=True)

    mysql_file = meta_dir/'mysql.ini'

    if not mysql_file.exists():
        return

    conf = AdministrativeUserConfigFile()

    mysql_config = ArchiveDatabaseConfigFile()
    mysql_config.load(mysql_file)

    with database('localhost', conf.user, conf.password) as cur:
        for dbname in mysql_config.databases:
            print('teardown {} database...'.format(dbname))
            cur.execute('DROP DATABASE IF EXISTS {}'.format(dbname))

        for user in mysql_config.users.keys():
            print('teardown {} user...'.format(dbname))
            cur.execute("DROP USER IF EXISTS '%(user)s'@'%'", {'user': user})


