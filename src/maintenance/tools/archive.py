"""
Pack up a finished project, with its databases and server configuration,
and store it on a remote server.

The work is split into three steps so that the interesting decisions happen
while a human is still watching:

    archive discover /srv/example.com > example.yaml
    $EDITOR example.yaml
    archive pack example.yaml
    archive remove example.yaml

Discovery is read-only and writes a plan describing everything the plugins
found. Packing does exactly what the plan says, without looking around
again. Removal is deliberately separate, and asks for the privileged
credentials it needs at the moment it needs them.

Secrets are never written to the plan. Their names and origins are, so the
plan stays readable and shareable, and the values are fetched again on each
run from the environment, from the installation's own config files, or from
you.

Usage:
    archive discover [options] [--path=PATH]... DIR
    archive pack [options] PLAN
    archive remove [options] PLAN
    archive [options] [--path=PATH]... DIR
    archive --help
    archive --version

Options:
    -o FILE           Write the plan (discover) or the archive (pack) here.
    --path=PATH       Extra file or directory to archive and remove.
    -a                Also report which plugins found nothing.
    -s STORAGE        Storage backend to use [default: ssh]
    -k                Keep the archive locally; do not store it.
    -m META_DIR       Read metadata from an unpacked archive (remove).
    -y                Do not ask for confirmation.
    --no-ask          Never prompt for secrets; use the environment only.
    --keep-directory  Do not delete the project directory (remove).
    --help            Display this message.
    --version         Display version information.
"""

VERSION = '2.0'


import shutil
import subprocess
import sys
import tempfile

from pathlib import Path

from docopt import docopt

from ..archive import protocol, secrets
from ..archive.environment import SecretRequirement
from ..archive.plan import Plan, PluginEntry
from ..console import ask_for


def confirm(question, assume_yes=False):
    if assume_yes:
        return True

    print(question)

    return ask_for(['y', 't'], ['n', 'f'], case_sensitive=False)


def plugin_order(plugins):
    """Ask every plugin who it is and when it wants to run.

    Ordering has to be known before discovery, because discovery is how
    plugins talk to each other: archive-plugin-wordpress writes
    ``mysql.databases`` into the environment and archive-plugin-mysql reads
    it back on its own pass. A plugin that cannot answer is dropped with a
    warning rather than taking the whole run down.
    """
    ordered = []

    for name, program in plugins:
        try:
            info = protocol.invoke(program, protocol.request(protocol.INFO, ''))
        except protocol.PluginError as e:
            protocol.warn("skipping plugin: {}".format(e))
            continue

        ordered.append((info.get('order', 50), info.get('name', name), program))

    return sorted(ordered, key=lambda t: (t[0], t[1]))


def discover(arguments):
    directory = Path(arguments['DIR']).expanduser().resolve(strict=True)

    plan = Plan(directory)
    environment = plan.environment

    options = {'paths': arguments['--path']}
    skipped = []

    for order, name, program in plugin_order(protocol.find_plugins()):
        try:
            response = protocol.invoke(program, protocol.request(
                protocol.DISCOVER,
                directory,
                vars=environment.vars,
                # Nothing is resolved during discovery, so what a plugin
                # needs to see is which requirements have been declared.
                secret_names=sorted(environment.requirements),
                options=options,
            ))
        except protocol.PluginError as e:
            protocol.warn("discovery failed: {}".format(e))
            continue

        score = float(response.get('score', 0.0))

        if score <= 0:
            skipped.append(name)
            continue

        environment.update(response.get('vars'))

        for secret_name, declaration in (response.get('secrets') or {}).items():
            requirement = SecretRequirement.from_dict(secret_name, declaration)
            requirement.plugin = requirement.plugin or name

            environment.require(requirement)

        plan.plugins.append(PluginEntry(
            name,
            order=response.get('order', order),
            score=score,
            data=response.get('data'),
        ))

    if arguments['-a'] and skipped:
        protocol.warn("found nothing: {}".format(', '.join(sorted(skipped))))

    if not plan.plugins:
        # A plan with no plugins is a perfectly good plan: archive the
        # directory and nothing else. Worth saying out loud, though, since
        # it is also what you would see if no plugin were installed.
        protocol.warn(
            "nothing claimed {}; the plan will archive the directory alone.".format(
                directory
            )
        )

    if arguments['-o'] and arguments['-o'] != '-':
        with open(arguments['-o'], 'w') as fp:
            plan.write(fp)

        protocol.warn("wrote plan for {} to {}".format(directory, arguments['-o']))
    else:
        plan.write(sys.stdout)

    return 0


def summarise(data, limit=4):
    """A one-line, human-sized rendering of a plugin's recorded state.

    This is what someone reads just before agreeing to delete a database,
    so it shows the things being destroyed rather than the bookkeeping
    around them.
    """
    parts = []

    for key, value in sorted(data.items()):
        if key in ('sudo', 'reload') or value in (None, [], {}, ''):
            continue

        if isinstance(value, list):
            shown = [
                item.get('path', item) if isinstance(item, dict) else item
                for item in value[:limit]
            ]

            rendered = ', '.join(str(item) for item in shown)

            if len(value) > limit:
                rendered += ' (+{} more)'.format(len(value) - limit)
        else:
            rendered = str(value)

        parts.append('{}: {}'.format(key, rendered))

    return '; '.join(parts) or 'no recorded state'


def read_plan(arguments):
    with open(arguments['PLAN']) as fp:
        return Plan.read(fp)


def run_plugins(plan, mode, meta_dir=None, reverse=False):
    "Invoke every plugin in the plan, handing each its own slice back."
    environment = plan.environment
    transport = environment.transport_dict()

    entries = plan.in_order()

    if reverse:
        entries = list(reversed(entries))

    for entry in entries:
        protocol.invoke(protocol.resolve(entry.name), protocol.request(
            mode,
            plan.directory,
            data=entry.data,
            meta_dir=str(meta_dir) if meta_dir else None,
            **transport
        ))


def store(archive_path, storage):
    if 'archive-store-' in storage:
        name = storage
    else:
        name = 'archive-store-{}'.format(storage)

    program = shutil.which(name)

    if program is None:
        raise ValueError("Invalid storage program {}".format(name))

    subprocess.check_call([program, str(archive_path)])


def pack(arguments):
    plan = read_plan(arguments)
    directory = Path(plan.directory).expanduser().resolve(strict=True)

    secrets.resolve(plan, 'archive', ask=not arguments['--no-ask'])
    secrets.describe(plan.environment, 'archive')

    meta_dir = Path(tempfile.mkdtemp(prefix='archive-m-{}'.format(directory.name[:19])))
    archive_dir = Path(tempfile.mkdtemp(prefix='archive-d-{}'.format(directory.name[:19])))

    if arguments['-o']:
        archive_path = Path(arguments['-o']).expanduser()
    elif arguments['-k']:
        archive_path = Path.cwd() / '{}.tar.gz'.format(directory.name)
    else:
        archive_path = archive_dir / '{}.tar.gz'.format(directory.name)

    try:
        run_plugins(plan, protocol.PACK, meta_dir=meta_dir)

        # The plan travels inside the archive, so that an unpacked archive
        # can be torn down or restored without the original file.
        with (meta_dir / 'archive.yaml').open('w') as fp:
            plan.write(fp)

        subprocess.check_call([
            'archive-compress', '-v',
            '-f', 'gz',
            '-m', str(meta_dir),
            str(directory),
            str(archive_path),
        ])

        print("archive: {} ({})".format(
            archive_path, _sizeof(archive_path)
        ), file=sys.stderr)

        if arguments['-k']:
            return 0

        if not confirm("Do you want to store this archive?", arguments['-y']):
            return 1

        store(archive_path, arguments['-s'])

        print("archive: stored. Run 'archive remove {}' to tear the "
              "installation down.".format(arguments['PLAN']), file=sys.stderr)
    finally:
        shutil.rmtree(meta_dir, ignore_errors=True)
        shutil.rmtree(archive_dir, ignore_errors=True)

    return 0


def _sizeof(path):
    from ..strings import sizeof_fmt

    try:
        return sizeof_fmt(path.stat().st_size)
    except OSError:
        return 'unknown size'


def remove(arguments):
    plan = read_plan(arguments)
    directory = Path(plan.directory).expanduser()

    print("This will permanently remove:", file=sys.stderr)
    print("  {}".format(directory), file=sys.stderr)

    for entry in plan.in_order():
        print("  {}: {}".format(entry.name, summarise(entry.data)), file=sys.stderr)

    secrets.resolve(plan, 'remove', ask=not arguments['--no-ask'])
    secrets.describe(plan.environment, 'remove')

    if not confirm("Do you want to proceed?", arguments['-y']):
        return 1

    meta_dir = Path(arguments['-m']).expanduser() if arguments['-m'] else None

    run_plugins(plan, protocol.REMOVE, meta_dir=meta_dir, reverse=True)

    if arguments['--keep-directory']:
        return 0

    if directory.exists():
        print("removing directory {}...".format(directory), file=sys.stderr)
        shutil.rmtree(directory)

    return 0


def main():
    arguments = docopt(__doc__, version=VERSION)

    if arguments['pack']:
        action = pack
    elif arguments['remove']:
        action = remove
    else:
        action = discover

    try:
        sys.exit(action(arguments))
    except (protocol.PluginError, secrets.MissingSecret, ValueError) as e:
        print("archive: {}".format(e), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\narchive: cancelled.", file=sys.stderr)
        sys.exit(130)
