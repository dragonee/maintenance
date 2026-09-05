
"""Resolving secrets, once per run, without ever storing them.

Discovery records only that a secret is *needed* and where it comes from.
The values are fetched again every time something actually runs, which is
why a plan file can sit in a repository between the two steps.

Three sources are tried in order:

1. the process environment (``ARCHIVE_MYSQL_ROOT_PASSWORD`` and friends),
   so unattended runs and CI never have to prompt;
2. the plugin that declared the requirement, which usually reads it out of
   the installation's own configuration file;
3. the user, over the terminal.

The driver owns the terminal, so plugins never prompt for themselves.
"""

import sys

from collections import defaultdict

from ..console import getpass_until_valid
from . import protocol
from .environment import Secret


class MissingSecret(RuntimeError):
    pass


def describe(environment, stage, file=sys.stderr):
    """Report which secrets are in play, without disclosing any of them."""
    requirements = environment.requirements_for_stage(stage)

    if not requirements:
        return

    print("secrets required for {}:".format(stage), file=file)

    for requirement in sorted(requirements, key=lambda r: r.name):
        print("  {:<32} {:<10} {}".format(
            requirement.name,
            'present' if environment.has_secret(requirement.name) else 'missing',
            requirement.source or requirement.default_env_var(),
        ), file=file)


def _from_environ(environment, requirements):
    "Take everything the process environment already offers."
    remaining = []

    for requirement in requirements:
        secret = requirement.from_environ()

        if secret is None:
            remaining.append(requirement)
            continue

        environment.put_secret(requirement.name, secret)

    return remaining


def _from_plugins(environment, requirements, plan, stage):
    """Ask each owning plugin to resolve the requirements it declared.

    One call per plugin, carrying all of that plugin's outstanding
    requirements, so a plugin that has to open a config file opens it once.
    """
    by_plugin = defaultdict(list)
    unowned = []

    for requirement in requirements:
        if requirement.plugin:
            by_plugin[requirement.plugin].append(requirement)
        else:
            unowned.append(requirement)

    for name, owned in by_plugin.items():
        entry = plan.plugin(name)

        if entry is None:
            unowned.extend(owned)
            continue

        response = protocol.invoke(protocol.resolve(name), protocol.request(
            protocol.SECRETS,
            plan.directory,
            stage=stage,
            vars=environment.vars,
            secret_names=environment.secret_names(),
            data=entry.data,
            requirements={r.name: r.to_dict() for r in owned},
        ))

        returned = response.get('secrets') or {}

        for requirement in owned:
            value = returned.get(requirement.name)

            if value in (None, ''):
                unowned.append(requirement)
                continue

            environment.put_secret(
                requirement.name, value, source=requirement.source or name
            )

    return unowned


def _from_user(environment, requirements, ask=True):
    "Whatever is left has to come from a human, or not at all."
    missing = []

    for requirement in requirements:
        if not ask:
            missing.append(requirement)
            continue

        if requirement.optional:
            print("{} is optional; leave empty to skip.".format(requirement.name),
                  file=sys.stderr)

        try:
            value = getpass_until_valid(
                requirement.prompt_text(),
                "{} cannot be empty (or set {}).".format(
                    requirement.name, requirement.default_env_var()
                ),
                check=lambda x: True if requirement.optional else x != '',
            )
        except (KeyboardInterrupt, EOFError):
            print('', file=sys.stderr)
            raise MissingSecret("Cancelled while asking for {}.".format(requirement.name))

        if value == '':
            missing.append(requirement)
            continue

        environment.put_secret(requirement.name, value, source='prompt')

    return missing


def resolve(plan, stage, ask=True):
    """Fill in every secret needed for ``stage``. Returns the environment.

    Raises :class:`MissingSecret` if a non-optional secret could not be
    obtained, naming the environment variable that would have supplied it.
    """
    environment = plan.environment

    requirements = [
        requirement
        for requirement in environment.requirements_for_stage(stage)
        if not environment.has_secret(requirement.name)
    ]

    remaining = _from_environ(environment, requirements)
    remaining = _from_plugins(environment, remaining, plan, stage)
    remaining = _from_user(environment, remaining, ask=ask)

    required = [r for r in remaining if not r.optional]

    if required:
        raise MissingSecret(
            "Could not resolve {}. Set {} in the environment.".format(
                ', '.join(r.name for r in required),
                ', '.join(r.default_env_var() for r in required),
            )
        )

    return environment
