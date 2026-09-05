
"""The plan file: what discovery found, and what archiving will therefore do.

A plan is plain YAML, meant to be read and edited by hand between the
discovery and the archive step. It records every plugin that claimed the
directory, the vars they contributed, and the *names* of the secrets that
will have to be resolved again later. It never records a secret value.
"""

import datetime

import yaml

from .environment import Environment, Secret, SecretsMustNotBeSerialized


VERSION = 1


class PlanDumper(yaml.SafeDumper):
    """A dumper that never emits anchors.

    Two plugins reporting the same list is common, and a plan sprouting
    &id001/*id001 references is a plan nobody wants to edit by hand.
    """

    def ignore_aliases(self, data):
        return True


def _refuse_secret(dumper, data):
    raise SecretsMustNotBeSerialized(
        "Refusing to serialise {!r}. Plans store secret names, never values.".format(data)
    )


PlanDumper.add_representer(Secret, _refuse_secret)
yaml.SafeDumper.add_representer(Secret, _refuse_secret)


def dump(data, stream=None):
    "Dump YAML, blowing up loudly if a secret ever reaches the writer."
    return yaml.dump(
        data,
        stream,
        Dumper=PlanDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )


def load(stream):
    return yaml.safe_load(stream)


class PluginEntry:
    """One plugin's slice of the plan."""

    def __init__(self, name, order=50, score=0.0, data=None):
        self.name = name
        self.order = order
        self.score = score
        self.data = dict(data or {})

    @classmethod
    def from_dict(cls, d):
        return cls(
            d['name'],
            order=d.get('order', 50),
            score=d.get('score', 0.0),
            data=d.get('data'),
        )

    def to_dict(self):
        d = {
            'name': self.name,
            'order': self.order,
            'score': float(self.score),
        }

        if self.data:
            d['data'] = self.data

        return d

    def __repr__(self):
        return '<PluginEntry {} score={}>'.format(self.name, self.score)


class Plan:
    def __init__(self, directory, environment=None, plugins=None,
                 generated=None, version=VERSION):
        self.version = version
        self.directory = str(directory)
        self.generated = generated or datetime.datetime.now().isoformat(timespec='seconds')
        self.environment = environment or Environment()
        self.plugins = list(plugins or [])

    def plugin(self, name):
        for entry in self.plugins:
            if entry.name == name:
                return entry

        return None

    def in_order(self):
        return sorted(self.plugins, key=lambda e: (e.order, e.name))

    def to_dict(self):
        public = self.environment.public_dict()

        return {
            'version': self.version,
            'directory': self.directory,
            'generated': self.generated,
            'vars': public['vars'],
            'secrets': public['secrets'],
            'plugins': [entry.to_dict() for entry in self.in_order()],
        }

    @classmethod
    def from_dict(cls, d):
        version = d.get('version')

        if version != VERSION:
            raise ValueError(
                "Unsupported plan version {!r}, this archive speaks version {}.".format(
                    version, VERSION
                )
            )

        if not d.get('directory'):
            raise ValueError("Plan is missing the 'directory' key.")

        return cls(
            d['directory'],
            environment=Environment.from_public_dict(d),
            plugins=[PluginEntry.from_dict(p) for p in (d.get('plugins') or [])],
            generated=d.get('generated'),
            version=version,
        )

    def write(self, stream):
        return dump(self.to_dict(), stream)

    @classmethod
    def read(cls, stream):
        return cls.from_dict(load(stream))

    def __repr__(self):
        return '<Plan {} ({} plugins)>'.format(self.directory, len(self.plugins))
