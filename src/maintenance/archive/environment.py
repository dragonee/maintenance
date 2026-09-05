
"""The environment shared between the driver and its plugins.

Two kinds of values live here:

vars
    Ordinary strings, lists and dicts. They are written to the plan file,
    printed, and generally treated as documentation of what will happen.

secrets
    Values that must never be printed or written anywhere. A plugin may
    read one to do its job, but the driver only ever serialises the *name*
    of a secret, so a plan file can be committed, mailed or pasted safely.

Both are namespaced by convention: a plugin owns the ``<name>.`` prefix
matching its own name, and reads other plugins' keys to cooperate with them
(``archive-plugin-wordpress`` writes ``mysql.databases``, which
``archive-plugin-mysql`` picks up on its own discovery pass).
"""

import os

from collections.abc import Mapping


class SecretsMustNotBeSerialized(TypeError):
    """Raised when something tries to write a secret out."""


class Secret:
    """A string that refuses to be printed.

    ``reveal()`` is the only way to get the value back, and it is spelled
    loudly on purpose so that ``grep -rn reveal`` finds every place a secret
    escapes into the world.
    """

    __slots__ = ('_value', 'source')

    def __init__(self, value, source=None):
        self._value = value
        self.source = source

    def reveal(self):
        return self._value

    def __bool__(self):
        return bool(self._value)

    def __len__(self):
        return len(self._value)

    def __eq__(self, other):
        if isinstance(other, Secret):
            return self._value == other._value

        return NotImplemented

    def __hash__(self):
        raise SecretsMustNotBeSerialized(
            "Refusing to hash a secret; use .reveal() if you really mean it."
        )

    def __repr__(self):
        return '<Secret {}>'.format(self.source or 'undisclosed')

    __str__ = __repr__

    def __format__(self, spec):
        return repr(self)


class SecretRequirement:
    """A secret a plugin says it will need, declared during discovery.

    The requirement itself is public: it is written to the plan so that a
    reader can see *that* a database password is needed, where it comes
    from, and at which stage, without the value ever being stored.

    stage
        ``archive`` for secrets needed to pack, ``remove`` for the
        privileged ones needed to tear an installation down.
    source
        Free-form provenance, e.g. ``wp-config.php:DB_PASSWORD``.
    env_var
        Environment variable consulted before prompting the user.
    """

    def __init__(self, name, plugin=None, stage='archive', source=None,
                 env_var=None, prompt=None, optional=False):
        self.name = name
        self.plugin = plugin
        self.stage = stage
        self.source = source
        self.env_var = env_var
        self.prompt = prompt
        self.optional = optional

    @classmethod
    def from_dict(cls, name, d):
        if not isinstance(d, Mapping):
            d = {}

        return cls(
            name,
            plugin=d.get('plugin'),
            stage=d.get('stage', 'archive'),
            source=d.get('source'),
            env_var=d.get('env_var'),
            prompt=d.get('prompt'),
            optional=d.get('optional', False),
        )

    def to_dict(self):
        d = {'stage': self.stage}

        for key in ('plugin', 'source', 'env_var', 'prompt'):
            value = getattr(self, key)

            if value:
                d[key] = value

        if self.optional:
            d['optional'] = True

        return d

    def default_env_var(self):
        if self.env_var:
            return self.env_var

        return 'ARCHIVE_' + self.name.upper().replace('.', '_').replace('-', '_')

    def from_environ(self):
        "Return the secret if the process environment carries it, else None."
        value = os.environ.get(self.default_env_var())

        if not value:
            return None

        return Secret(value, source='${}'.format(self.default_env_var()))

    def prompt_text(self):
        if self.prompt:
            return self.prompt

        return '{} ({}): '.format(self.name, self.source or 'secret')

    def __repr__(self):
        return '<SecretRequirement {} stage={}>'.format(self.name, self.stage)


class Environment:
    """Vars and secrets, plus the requirements that have been declared."""

    def __init__(self, vars=None, secrets=None, requirements=None):
        self.vars = dict(vars or {})
        self.secrets = dict(secrets or {})
        self.requirements = dict(requirements or {})

    # -- vars ------------------------------------------------------------

    def get(self, key, default=None):
        return self.vars.get(key, default)

    def set(self, key, value):
        self.vars[key] = value

    def update(self, mapping):
        self.vars.update(mapping or {})

    def namespace(self, prefix):
        "Every var under ``prefix.``, with the prefix stripped."
        dotted = prefix + '.'

        return {
            key[len(dotted):]: value
            for key, value in self.vars.items()
            if key.startswith(dotted)
        }

    # -- secrets ---------------------------------------------------------

    def has_secret(self, name):
        "Presence is public information; the value is not."
        return name in self.secrets

    def secret_names(self):
        return sorted(self.secrets.keys())

    def secret(self, name, default=None):
        "Return the raw value of a secret, or ``default`` if it is absent."
        found = self.secrets.get(name)

        if found is None:
            return default

        return found.reveal()

    def put_secret(self, name, value, source=None):
        if value is None:
            return

        if not isinstance(value, Secret):
            value = Secret(value, source=source)

        self.secrets[name] = value

    def require(self, requirement):
        """Record a secret requirement, keeping the first one declared.

        Discovery runs detectors before the services they feed, so the
        plugin that actually read the configuration file has already
        described where the secret comes from; a later plugin restating
        the requirement should not blur that provenance.
        """
        self.requirements.setdefault(requirement.name, requirement)

    def requirements_for_stage(self, stage):
        return [r for r in self.requirements.values() if r.stage == stage]

    # -- serialisation ---------------------------------------------------

    def public_dict(self):
        """What may be written to a plan file: vars and secret *names*.

        Secret values are structurally unable to reach this dictionary.
        """
        return {
            'vars': dict(self.vars),
            'secrets': {
                name: requirement.to_dict()
                for name, requirement in sorted(self.requirements.items())
            },
        }

    def transport_dict(self):
        """What is piped to a plugin on stdin. Contains revealed secrets.

        Only ever hand this to a subprocess pipe, never to a file or a
        terminal.
        """
        return {
            'vars': dict(self.vars),
            'secrets': {
                name: secret.reveal()
                for name, secret in self.secrets.items()
            },
            'secret_names': self.secret_names(),
        }

    @classmethod
    def from_public_dict(cls, d):
        d = d or {}

        requirements = {
            name: SecretRequirement.from_dict(name, value)
            for name, value in (d.get('secrets') or {}).items()
        }

        return cls(vars=d.get('vars'), requirements=requirements)

    def __repr__(self):
        return '<Environment {} vars, {} secrets>'.format(
            len(self.vars), len(self.secrets)
        )
