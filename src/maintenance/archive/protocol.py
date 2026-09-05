
"""Driver side of the plugin protocol.

A plugin is any executable on ``$PATH`` whose name starts with
``archive-plugin-``. The driver runs it with no arguments, writes a single
JSON request to its stdin, and reads a single YAML (or JSON) document back
from its stdout. The plugin's stderr is inherited, so anything it prints
there reaches the user as progress.

Nothing of interest travels in argv, which is world-readable through ``ps``.
Secrets only ever cross the stdin pipe, and only in the modes that need
them.
"""

import json
import shutil
import subprocess
import sys

import yaml

from .programs import find_programs_startswith


PREFIX = 'archive-plugin-'

INFO = 'info'
DISCOVER = 'discover'
SECRETS = 'secrets'
PACK = 'pack'
REMOVE = 'remove'


class PluginError(RuntimeError):
    def __init__(self, program, message):
        self.program = program

        super().__init__("{}: {}".format(program, message))


def plugin_name(program):
    "archive-plugin-postgresql -> postgresql"
    return program.name[len(PREFIX):]


def find_plugins():
    """Every plugin on ``$PATH``, de-duplicated by name, first one wins.

    First-one-wins matches how the shell resolves a command, so putting a
    directory earlier in ``$PATH`` overrides a shipped plugin with your own.
    """
    found = {}

    for program in find_programs_startswith(PREFIX):
        found.setdefault(plugin_name(program), program)

    return [(name, found[name]) for name in sorted(found)]


def resolve(name):
    """Find a plugin by name, the way the shell would.

    Plans record what ran, not where it lived: an absolute path pins a plan
    to one machine's filesystem, and a plan is meant to survive being made
    on a server and used after a reinstall.
    """
    program = shutil.which(PREFIX + name)

    if program is None:
        raise PluginError(PREFIX + name, "is in the plan but not on your PATH")

    return program


def invoke(program, request, timeout=None):
    """Run one plugin with ``request`` on stdin, return its parsed response.

    stderr is inherited rather than captured: plugins report progress there
    and the user should see it as it happens.
    """
    try:
        completed = subprocess.run(
            [str(program)],
            input=json.dumps(request),
            stdout=subprocess.PIPE,
            stderr=None,
            universal_newlines=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise PluginError(program, "timed out after {}s".format(timeout))
    except OSError as e:
        raise PluginError(program, "could not be executed ({})".format(e))

    if completed.returncode != 0:
        raise PluginError(program, "exited with status {}".format(completed.returncode))

    if not completed.stdout.strip():
        return {}

    try:
        response = yaml.safe_load(completed.stdout)
    except yaml.YAMLError as e:
        raise PluginError(program, "returned a malformed response ({})".format(e))

    if response is None:
        return {}

    if not isinstance(response, dict):
        raise PluginError(program, "returned {}, expected a mapping".format(
            type(response).__name__
        ))

    return response


def request(mode, plan_directory, **kwargs):
    "Build the common part of every request."
    payload = {
        'protocol': 1,
        'mode': mode,
        'directory': str(plan_directory),
    }

    payload.update(kwargs)

    return payload


def warn(message):
    print(message, file=sys.stderr)
