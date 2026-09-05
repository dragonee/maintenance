
"""Small readers shared by the plugins that sniff an installation.

Nothing here is clever. It exists so that four plugins do not each grow
their own slightly different ``.env`` parser.
"""

import re

from urllib.parse import urlsplit, unquote


#: define('DB_NAME', 'example'); and friends, as written by WordPress.
PHP_DEFINE = re.compile(
    r'''define\s*\(\s*['"](?P<name>\w+)['"]\s*,\s*['"](?P<value>[^'"]*)['"]\s*\)'''
)

#: KEY=value, KEY='value', export KEY="value"
ENV_LINE = re.compile(
    r'''^\s*(?:export\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<value>.*?)\s*$'''
)

DSN_SCHEMES = {
    'mysql': 'mysql',
    'mysql2': 'mysql',
    'mariadb': 'mysql',
    'postgres': 'postgresql',
    'postgresql': 'postgresql',
    'pgsql': 'postgresql',
}


def read_php_defines(path, keys=None):
    "Pull define()d constants out of a PHP config file."
    found = {}

    with path.open(errors='replace') as f:
        for line in f:
            match = PHP_DEFINE.search(line)

            if not match:
                continue

            name, value = match.group('name'), match.group('value')

            if keys is not None and name not in keys:
                continue

            found[name] = value

    return found


def read_env_file(path):
    "Parse a dotenv file well enough for database settings."
    found = {}

    with path.open(errors='replace') as f:
        for line in f:
            line = line.split('#', 1)[0] if line.lstrip().startswith('#') else line

            match = ENV_LINE.match(line)

            if not match:
                continue

            value = match.group('value')

            if len(value) > 1 and value[0] == value[-1] and value[0] in '\'"':
                value = value[1:-1]

            found[match.group('name')] = value

    return found


def parse_dsn(url):
    """Split a ``postgres://user:pass@host:5432/db`` style URL.

    Returns ``None`` for anything that is not a database URL we recognise.
    """
    if not url or '://' not in url:
        return None

    parts = urlsplit(url)
    engine = DSN_SCHEMES.get(parts.scheme.split('+')[0].lower())

    if engine is None:
        return None

    return {
        'engine': engine,
        'host': parts.hostname or 'localhost',
        'port': parts.port,
        'user': unquote(parts.username) if parts.username else None,
        'password': unquote(parts.password) if parts.password else None,
        'database': unquote(parts.path.lstrip('/')) or None,
    }


def find_dsn(config, engine=None):
    """First database URL in a config mapping, optionally of one engine.

    Looks at the keys frameworks actually use, in the order a human would.
    """
    for key in ('DATABASE_URL', 'DB_URL', 'DATABASE_DSN', 'POSTGRES_URL', 'MYSQL_URL'):
        dsn = parse_dsn(config.get(key))

        if dsn is None:
            continue

        if engine is None or dsn['engine'] == engine:
            return dsn

    return None


def first_existing(paths):
    for path in paths:
        if path.exists():
            return path

    return None
