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
    archive discover [options] [--path=PATH]... [--env=ENV]... DIR
    archive pack [options] PLAN
    archive remove [options] PLAN
    archive [options] [--path=PATH]... [--env=ENV]... DIR
    archive --help
    archive --version

Options:
    -o FILE           Write the plan (discover) or the archive (pack) here.
    --path=PATH       Extra file or directory to archive and remove.
    --env=ENV         Env file describing this installation, in or out of tree.
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


import os
import shutil
import subprocess
import sys
import tempfile

from pathlib import Path

from docopt import docopt

from ..archive import protocol, secrets
from ..archive.environment import SecretRequirement
from ..archive.plugin import check_removable, needs_privilege, remove_command
from ..archive.plan import Plan, PluginEntry
from ..console import ask_for
from ..strings import sizeof_fmt


def confirm(question, assume_yes=False):
    """Ask before doing something irreversible.

    A run with no terminal behind it -- cron, a pipeline -- gets a refusal
    rather than a traceback, and never a silent yes.
    """
    if assume_yes:
        return True

    print(question)

    try:
        return ask_for(['y', 't'], ['n', 'f'], case_sensitive=False)
    except EOFError:
        print("archive: no terminal to confirm on; use -y to proceed "
              "without asking.", file=sys.stderr)
        return False


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

    options = {'paths': arguments['--path'], 'env': arguments['--env']}
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
        if key in ('sudo', 'reload', 'related') or value in (None, [], {}, ''):
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

    if parts:
        return '; '.join(parts)

    # Distinguish "found nothing" from "found something and is deliberately
    # not touching it", which the Left alone section explains below.
    if data.get('related'):
        return 'nothing to remove'

    return 'no recorded state'


def claimed_paths(plan):
    """Every path some plugin in this plan intends to delete.

    Plugins record what they claim under `files` or `paths`, as bare
    strings or as mappings with a `path` key, so both shapes are read.
    """
    claimed = set()

    for entry in plan.plugins:
        for key in ('files', 'paths'):
            for item in entry.data.get(key) or []:
                path = item.get('path') if isinstance(item, dict) else item

                if path:
                    claimed.add(str(path))

    return claimed


def report_related(plan):
    """Say what was found near this installation but will not be touched.

    A plugin puts anything it recognised but deliberately did not claim
    under `related`. Server configuration is the usual case: a vhost that
    names this site but proxies to its replacement looks exactly like one
    worth deleting, right up until it takes production down. Showing it
    before the confirmation is the whole point of showing it at all.
    """
    found = [
        (entry.name, entry.data['related'])
        for entry in plan.in_order()
        if entry.data.get('related')
    ]

    if not found:
        return

    claimed = claimed_paths(plan)
    conflicts = []

    print("\nLeft alone (names this site but serves something else):",
          file=sys.stderr)

    for name, related in found:
        for item in related:
            path = item.get('path')
            sites = item.get('sites') or []

            # Another plugin may have been told to remove the very thing
            # this one is declining to touch -- most often because it was
            # passed to --path by hand. Saying "left alone" about a file
            # that is about to be deleted would be worse than saying
            # nothing at all.
            if path in claimed:
                conflicts.append((name, path))
                continue

            print("  {}: {}{}".format(
                name,
                path,
                ' ({})'.format(', '.join(sites)) if sites else '',
            ), file=sys.stderr)

    if conflicts:
        print("\nWARNING: these were reported as serving something else, "
              "but another plugin in this plan will remove them anyway:",
              file=sys.stderr)

        for name, path in conflicts:
            print("  {} says leave; the plan says remove: {}".format(name, path),
                  file=sys.stderr)


def note(*parts):
    "Render the trailing (a, b) annotation, skipping anything empty."
    shown = [part for part in parts if part]

    return ' ({})'.format(', '.join(shown)) if shown else ''


def removal_paths(plan):
    """Every path the plan will delete, with the plugin that claimed it.

    One entry per path: a directory stands for its whole tree rather than
    being expanded, which is the only way this stays readable for an
    installation of thirteen thousand files.
    """
    found = []
    seen = set()

    for entry in plan.in_order():
        for key in ('files', 'paths'):
            for item in entry.data.get(key) or []:
                if isinstance(item, dict):
                    candidates = list(item.get('links') or []) + [item.get('path')]
                else:
                    candidates = [item]

                for path in candidates:
                    if path and path not in seen:
                        seen.add(path)
                        found.append((path, entry.name))

    return found


def removal_databases(plan):
    "The databases the plan will drop, as one line each."
    lines = []
    vars = plan.environment.vars

    for engine in ('mysql', 'postgresql'):
        databases = vars.get('{}.databases'.format(engine)) or []
        host = vars.get('{}.host'.format(engine)) or 'localhost'
        port = vars.get('{}.port'.format(engine))

        for database in databases:
            lines.append('{} database {} on {}{}'.format(
                engine, database, host, ':{}'.format(port) if port else ''
            ))

    return lines


def check_directory_matches(plan, directory):
    """Refuse a plan whose directory no longer holds what it described.

    The guard against system paths cannot help with the likeliest bad
    edit: trimming the site name off the end and leaving the directory
    that contains every site. Nothing about "/home/sites/vhosts" looks
    dangerous, and it is one keystroke away from a directory that is.

    So the plan is checked against itself. A plugin records the file it
    recognised the installation by -- wp-config.php, a settings module --
    and if that file is not there, this is not the installation the plan
    was made for, whatever the path says.
    """
    missing = []

    for entry in plan.in_order():
        for marker in entry.data.get('markers') or []:
            if not (directory / marker).exists():
                missing.append((entry.name, marker))

    if not missing:
        return

    raise ValueError(
        "{} does not contain what this plan describes ({}); "
        "refusing to remove it. Has the plan been edited, or the "
        "installation already removed?".format(
            directory,
            ', '.join('{} expected {}'.format(n, m) for n, m in missing),
        )
    )


def survey_directory(directory):
    """Measure the tree and find what this user cannot delete.

    Unlinking a file needs write and execute on its *parent* directory,
    so only directories have to be tested -- cheap even for a large tree.
    Knowing this before starting is the whole point: shutil.rmtree deletes
    as it walks, so discovering halfway through that a file belongs to
    somebody else leaves a half-removed installation behind.
    """
    files = 0
    total = 0
    blocked = []

    def unreadable(error):
        blocked.append(getattr(error, 'filename', str(directory)))

    if not os.access(str(directory.parent), os.W_OK | os.X_OK):
        blocked.append(str(directory.parent))

    for root, directories, names in os.walk(str(directory), onerror=unreadable):
        if not os.access(root, os.W_OK | os.X_OK):
            blocked.append(root)

        files += len(names)

        for name in names:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                pass

    return files, total, sorted(set(blocked))


def remove_directory(directory, blocked, sudo=True):
    """Delete the installation's directory, with sudo when it is needed.

    Falls back to sudo even when the survey said it was not required: the
    survey can be wrong about an immutable file or a mount, and finishing
    the job matters more than being right about it in advance.
    """
    if not blocked:
        try:
            shutil.rmtree(str(directory))
            return
        except OSError as e:
            if not sudo or os.geteuid() == 0:
                raise

            protocol.warn("could not remove {} as this user ({}); "
                          "retrying with sudo".format(directory, e))

    if os.geteuid() == 0:
        shutil.rmtree(str(directory))
        return

    if not sudo:
        raise RuntimeError(
            "{} is not yours to delete and sudo is disabled".format(directory)
        )

    if subprocess.call(['sudo'] + remove_command(directory, recursive=True)) != 0:
        raise RuntimeError("failed to remove {} even with sudo".format(directory))


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
    try:
        return sizeof_fmt(path.stat().st_size)
    except OSError:
        return 'unknown size'


def remove(arguments):
    plan = read_plan(arguments)
    directory = Path(plan.directory).expanduser()

    if not arguments['--keep-directory']:
        # Both checks run before a single database is dropped: a plan
        # naming something it should not is a plan to abandon, not to
        # half-run.
        check_removable(directory)

        if directory.exists():
            check_directory_matches(plan, directory)

    print("This will permanently remove:", file=sys.stderr)

    blocked = []

    if directory.exists() and not arguments['--keep-directory']:
        files, total, blocked = survey_directory(directory)

        print("  {}{}".format(directory, note(
            '{} files, {}'.format(files, sizeof_fmt(total)),
            'sudo' if blocked else None,
        )), file=sys.stderr)
    elif not arguments['--keep-directory']:
        print("  {} (already gone)".format(directory), file=sys.stderr)

    for path, plugin in removal_paths(plan):
        print("  {}{}".format(path, note(
            plugin,
            'sudo' if needs_privilege(path) else None,
        )), file=sys.stderr)

    for line in removal_databases(plan):
        print("  {}".format(line), file=sys.stderr)

    report_related(plan)

    secrets.resolve(plan, 'remove', ask=not arguments['--no-ask'])
    secrets.describe(plan.environment, 'remove')

    if not confirm("Do you want to proceed?", arguments['-y']):
        return 1

    meta_dir = Path(arguments['-m']).expanduser() if arguments['-m'] else None

    run_plugins(plan, protocol.REMOVE, meta_dir=meta_dir, reverse=True)

    if arguments['--keep-directory']:
        return 0

    if directory.exists():
        print("removing directory {}{}...".format(
            directory, ' with sudo' if blocked else ''
        ), file=sys.stderr)

        remove_directory(directory, blocked)

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
    except (protocol.PluginError, secrets.MissingSecret, ValueError,
            RuntimeError, OSError) as e:
        print("archive: {}".format(e), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\narchive: cancelled.", file=sys.stderr)
        sys.exit(130)
