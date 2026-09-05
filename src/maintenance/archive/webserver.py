
"""Shared behaviour for the plugins that look after server configuration.

nginx and Caddy differ in syntax but not in what has to happen: find the
configuration files that point at the directory being archived, copy them
into the archive, and delete them again (reloading the server) when the
installation is torn down.

Configuration usually lives under /etc, which the person running archive
does not normally own, so removal shells out through sudo unless it is
already running as root.
"""

import os
import re
import shutil
import subprocess

from pathlib import Path

from .plugin import Discovery, Plugin, needs_privilege


#: Files bigger than this are not server configuration and reading them
#: on every discovery pass would be rude.
MAX_CONFIG_SIZE = 1024 * 1024


class WebserverPlugin(Plugin):
    order = 50

    #: Directories and files to search, most specific first.
    config_paths = ()

    #: Command that makes the server notice the configuration is gone.
    reload_command = ()

    #: Command that checks the configuration before reloading it.
    test_command = ()

    #: Extracts the human-facing name of a site from its config text.
    site_pattern = None

    def search_paths(self):
        """Where to look, honouring an override for non-standard installs.

        ARCHIVE_NGINX_CONFIG_PATHS=/opt/nginx/sites:/opt/nginx/conf.d
        replaces the built-in list entirely, colon-separated like $PATH.
        """
        override = os.environ.get('ARCHIVE_{}_CONFIG_PATHS'.format(self.name.upper()))

        if override:
            return [entry for entry in override.split(os.pathsep) if entry]

        return list(self.config_paths)

    def candidate_files(self):
        "Every plausible configuration file on this machine."
        for entry in self.search_paths():
            path = Path(entry).expanduser()

            if path.is_file():
                yield path
                continue

            if not path.is_dir():
                continue

            for child in sorted(path.rglob('*')):
                if child.is_file():
                    yield child

    def mentions(self, path, directory):
        "Whether a config file points at the directory being archived."
        try:
            if path.stat().st_size > MAX_CONFIG_SIZE:
                return None
        except OSError:
            return None

        try:
            text = path.read_text(errors='replace')
        except OSError:
            return None

        if str(directory) not in text:
            return None

        return text

    def sites(self, text):
        if self.site_pattern is None:
            return []

        found = []

        for match in re.finditer(self.site_pattern, text):
            for name in match.group('names').split():
                name = name.strip('{;,')

                if name and name not in found:
                    found.append(name)

        return found

    def collect(self, directory):
        """Find the configuration for a directory, one entry per real file.

        sites-enabled/foo.conf is normally a symlink to sites-available/foo.conf,
        and searching both turns up the same configuration twice. Keying on
        the resolved path collapses that into a single entry which records
        the real file and every symlink pointing at it, whichever order the
        search happens to find them in.
        """
        entries = {}
        sites = []

        for path in self.candidate_files():
            text = self.mentions(path, directory)

            if text is None:
                continue

            real = os.path.realpath(str(path))
            entry = entries.setdefault(real, {'path': real, 'links': []})

            if str(path) != real and str(path) not in entry['links']:
                entry['links'].append(str(path))

            for site in self.sites(text):
                if site not in sites:
                    sites.append(site)

        for entry in entries.values():
            if not entry['links']:
                del entry['links']

        return list(entries.values()), sites

    # -- modes -----------------------------------------------------------

    def discover(self, request):
        directory = request.directory

        files, sites = self.collect(directory)

        if not files:
            return Discovery(score=0.0)

        discovery = Discovery(score=1.0, data={
            'files': files,
            # Whether sudo may be used at all. Set it to false in the plan
            # for a server you administer as yourself; even when true, it
            # is only reached for on files that genuinely need it.
            'sudo': os.geteuid() != 0,
            'reload': list(self.reload_command),
        })

        discovery.var('{}.sites'.format(self.name), sites)
        discovery.var('{}.files'.format(self.name), [f['path'] for f in files])

        self.log("{} config file(s){}", len(files),
                 ' for ' + ', '.join(sites) if sites else '')

        return discovery

    def pack(self, request):
        """Copy the configuration into meta/<server>/, keeping its layout.

        The absolute path is preserved under the meta directory so that a
        restore knows where each file belongs.
        """
        meta = request.meta_dir / self.name
        meta.mkdir(parents=True, exist_ok=True)

        for entry in request.data.get('files') or []:
            source = Path(entry['path'])
            target = meta / source.relative_to(source.anchor)

            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.copy2(str(source), str(target))
            except OSError as e:
                self.log("could not read {} ({})", source, e)
                continue

            self.log("saved {}", source)

        return {}

    def run_privileged(self, command, sudo):
        if sudo and os.geteuid() != 0:
            command = ['sudo'] + list(command)

        return subprocess.call(list(command))

    def remove_file(self, path, sudo):
        "Delete one file, reaching for sudo only if it is actually needed."
        return self.run_privileged(
            ['rm', '-f', str(path)], sudo and needs_privilege(path)
        )

    def remove(self, request):
        data = request.data
        sudo = data.get('sudo', os.geteuid() != 0)

        removed = 0

        for entry in data.get('files') or []:
            # Symlinks first. A sites-enabled link left pointing at a file
            # that is already gone makes `nginx -t` fail, which blocks the
            # next reload or restart of every other site on the box.
            for path in list(entry.get('links') or []) + [entry.get('path')]:
                # lexists, not exists: exists() follows the link and reports
                # False for a dangling one, which is exactly the case that
                # most needs cleaning up.
                if not path or not os.path.lexists(path):
                    continue

                self.log("removing {}", path)

                if self.remove_file(path, sudo) == 0:
                    removed += 1
                else:
                    self.log("failed to remove {}", path)

        if not removed:
            return {}

        reload_command = list(data.get('reload') or self.reload_command)

        if not reload_command:
            return {}

        # Configuration for a server that is not installed on this machine
        # is a normal thing to archive: the files were still worth saving
        # and deleting, there is just nothing running to tell about it.
        if not shutil.which(reload_command[0]):
            self.log("{} is not installed here; not reloading", reload_command[0])
            return {}

        if self.test_command and self.run_privileged(self.test_command, sudo) != 0:
            self.log("configuration test failed; not reloading")
            return {}

        self.log("reloading...")
        self.run_privileged(reload_command, sudo)

        return {}
