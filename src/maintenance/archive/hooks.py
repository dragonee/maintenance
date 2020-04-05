from enum import Enum


class Hooks(dict, Enum):
    ARCHIVE_MYSQL_HOOKS = {
        'teardown': 'archive-teardown-mysql',
        'unarchive': 'unarchive-mysql',
    }

    ARCHIVE_PGSQL_HOOKS = {
        'teardown': 'archive-teardown-pgsql',
        'unarchive': 'unarchive-pgsql'
    }

