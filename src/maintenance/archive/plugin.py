
"""Plugin side of the protocol: everything needed to write one in Python.

A plugin subclasses :class:`Plugin`, implements the modes it cares about,
and calls :func:`run` from its ``main()``. The base class takes care of
reading the request, dispatching on mode, and writing the response.

The modes:

info
    Announce your name and ordering. Must be instant: the driver calls it
    on every plugin it can find, just to work out who runs first.

discover
    Look at the directory and say how strongly you claim it (``score``),
    what you learned (``vars``), and which secrets you will need later
    (``require_secret``). Cheap and read-only: no dumping, no prompting,
    no connecting to anything that needs a password.

secrets
    Resolve the secret values you declared, for the stage being run. This
    is a separate pass so that a plan can be made once and archived later,
    with the passwords fetched fresh each time instead of stored.

pack
    Do the work: write dumps and configuration into ``meta_dir``, which
    gets tarred into the archive alongside the directory itself.

remove
    Undo the installation: drop databases, delete vhosts, remove the extra
    files you claimed. Runs after the archive is safely stored.

Plugins never prompt. They declare what they need and the driver, which
owns the terminal, resolves it.
"""

import json
import os
import sys

from pathlib import Path

import yaml


#: Paths no installation ever legitimately occupies. A plan is meant to be
#: edited by hand, and a truncation that leaves "/home/sites/vhosts" where
#: "/home/sites/vhosts/example.com" belonged turns a cleanup into an outage.
PROTECTED_PATHS = frozenset((
    '/', '/bin', '/boot', '/dev', '/etc', '/home', '/lib', '/lib32', '/lib64',
    '/media', '/mnt', '/opt', '/proc', '/root', '/run', '/sbin', '/srv',
    '/sys', '/tmp', '/usr', '/var',
))


def check_removable(path):
    """Return a path safe to delete, or raise ValueError explaining why not.

    Three things are refused: a relative path, whose meaning depends on
    where the command happened to be run; a system directory or a bare
    home directory; and anything that normalises into one, so that a stray
    `..` cannot walk a plan up into `/`.

    This is a guard against typos and bad edits, not against a hostile
    plan. Anyone who can write your plan file can already run your shell.
    """
    text = str(path)

    if not os.path.isabs(text):
        raise ValueError(
            "refusing to remove a relative path: {!r}".format(text)
        )

    resolved = os.path.normpath(text)

    if resolved in PROTECTED_PATHS:
        raise ValueError(
            "refusing to remove the protected path {!r}".format(resolved)
        )

    parts = [part for part in resolved.split('/') if part]

    if len(parts) < 2:
        raise ValueError(
            "refusing to remove the top-level path {!r}".format(resolved)
        )

    if parts[0] == 'home' and len(parts) == 2:
        raise ValueError(
            "refusing to remove the home directory {!r}".format(resolved)
        )

    if resolved == os.path.normpath(os.path.expanduser('~')):
        raise ValueError(
            "refusing to remove your own home directory {!r}".format(resolved)
        )

    return resolved


def remove_command(path, recursive=False):
    """Build an rm argument list that cannot be misread.

    The `--` matters: a file called "-rf" or "--no-preserve-root" is a
    perfectly legal name, and without the separator rm would read it as
    options rather than as the thing to delete.
    """
    return ['rm', '-rf' if recursive else '-f', '--', check_removable(path)]


def needs_privilege(path):
    """Whether deleting ``path`` needs more rights than we currently have.

    Deletion is governed by the containing directory, not by the file, so
    that is what gets tested. Being wrong here is cheap in one direction
    (a pointless sudo) and annoying in the other (a failed removal), so
    err towards asking.
    """
    return not os.access(str(Path(path).parent), os.W_OK)


class Plugin:
    name = None

    #: Lower runs first. Detectors that describe an installation (10) go
    #: before the services that act on that description (50), which go
    #: before catch-alls (90).
    order = 50

    version = '1.0'

    # -- modes, override what you need -----------------------------------

    def discover(self, request):
        return Discovery()

    def secrets(self, request):
        return {}

    def pack(self, request):
        return {}

    def remove(self, request):
        return {}

    # -- helpers ---------------------------------------------------------

    def log(self, message, *args):
        if args:
            message = message.format(*args)

        print('{}: {}'.format(self.name, message), file=sys.stderr)

    def info(self, request):
        return {
            'name': self.name,
            'order': self.order,
            'version': self.version,
        }

    def handle(self, request):
        handler = {
            'info': self.info,
            'discover': self.discover,
            'secrets': self.secrets,
            'pack': self.pack,
            'remove': self.remove,
        }.get(request.mode)

        if handler is None:
            raise ValueError("Unknown mode {!r}".format(request.mode))

        result = handler(request)

        if isinstance(result, Discovery):
            result = result.to_dict()

        if result is None:
            result = {}

        if request.mode == 'discover':
            result.setdefault('order', self.order)
            result.setdefault('score', 0.0)

        if request.mode == 'secrets':
            # A bare mapping of name -> value is the natural thing to
            # return from secrets(); wrap it into the response shape.
            if 'secrets' not in result:
                result = {'secrets': result}

        return result


class Discovery:
    """The result of a discovery pass, built up a piece at a time."""

    def __init__(self, score=0.0, vars=None, data=None):
        self.score = score
        self.vars = dict(vars or {})
        self.data = dict(data or {})
        self.requirements = {}

    def var(self, key, value):
        if value is not None:
            self.vars[key] = value

        return self

    def require_secret(self, name, stage='archive', source=None,
                       env_var=None, prompt=None, optional=False):
        self.requirements[name] = {
            'stage': stage,
            'source': source,
            'env_var': env_var,
            'prompt': prompt,
            'optional': optional,
        }

        return self

    def to_dict(self):
        d = {'score': float(self.score)}

        if self.vars:
            d['vars'] = self.vars

        if self.data:
            d['data'] = self.data

        if self.requirements:
            d['secrets'] = {
                name: {k: v for k, v in requirement.items() if v not in (None, False)}
                for name, requirement in self.requirements.items()
            }

        return d


class Request:
    """The decoded request, with the awkward parts smoothed over."""

    def __init__(self, payload):
        self.payload = payload
        self.mode = payload.get('mode')
        self.stage = payload.get('stage', 'archive')
        self.vars = payload.get('vars') or {}
        self.data = payload.get('data') or {}
        self.options = payload.get('options') or {}

        self._secrets = payload.get('secrets') or {}
        self._secret_names = payload.get('secret_names') or list(self._secrets)

    @property
    def directory(self):
        return Path(self.payload['directory'])

    @property
    def meta_dir(self):
        meta = self.payload.get('meta_dir')

        return Path(meta) if meta else None

    def var(self, key, default=None):
        return self.vars.get(key, default)

    def namespace(self, prefix):
        dotted = prefix + '.'

        return {
            key[len(dotted):]: value
            for key, value in self.vars.items()
            if key.startswith(dotted)
        }

    def secret(self, name, default=None):
        "The value of a secret the driver resolved for this run."
        return self._secrets.get(name, default)

    def has_secret(self, name):
        """Whether a secret exists, answerable without seeing the value.

        During discovery nothing is resolved yet, so this reports whether
        an earlier plugin has already declared the requirement -- which is
        what a plugin wants to know before declaring it again.
        """
        return name in self._secret_names or name in self._secrets

    def requirements(self):
        "In ``secrets`` mode, the requirements the driver wants resolved."
        return self.payload.get('requirements') or {}


def run(plugin_class, argv=None):
    """Entry point for a plugin executable.

    With arguments it behaves like a normal command (``--help``,
    ``--version``). With none it speaks the protocol on stdin/stdout.
    """
    plugin = plugin_class()
    argv = sys.argv[1:] if argv is None else argv

    if '-h' in argv or '--help' in argv:
        print((sys.modules[plugin_class.__module__].__doc__ or '').strip())
        return 0

    if '--version' in argv:
        print(plugin.version)
        return 0

    if argv:
        print("{} speaks the archive plugin protocol on stdin; see --help.".format(
            plugin.name
        ), file=sys.stderr)
        return 2

    try:
        payload = json.load(sys.stdin)
    except ValueError as e:
        print("{}: malformed request: {}".format(plugin.name, e), file=sys.stderr)
        return 2

    try:
        response = plugin.handle(Request(payload))
    except Exception as e:
        # A plugin's failure is a normal outcome the driver reports, so
        # say it plainly. Set ARCHIVE_DEBUG for the traceback when the
        # failure is a bug rather than a misconfiguration.
        if os.environ.get('ARCHIVE_DEBUG'):
            raise

        print('{}: {}'.format(plugin.name, e), file=sys.stderr)
        return 1

    yaml.dump(
        response,
        sys.stdout,
        Dumper=yaml.SafeDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )

    return 0
