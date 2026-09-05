#!/usr/bin/env python3

"""
Archive and remove files and directories that live outside the project.

An installation is rarely confined to one directory. There is a cron job in
/etc/cron.d, a unit file in /etc/systemd/system, a logrotate rule, a socket
directory under /var. Nothing can detect those reliably, so they are named
explicitly:

    archive discover /srv/example.com \\
        --path /etc/cron.d/example \\
        --path /etc/systemd/system/example.service \\
        > example.yaml

They can equally well be added to the plan by hand afterwards, which is
often easier than remembering every one up front:

    plugins:
      - name: paths
        order: 90
        score: 1.0
        data:
          paths:
            - /etc/logrotate.d/example

Packing copies each path into meta/paths/, keeping its absolute layout.
Removal deletes it, through sudo when it is not yours to delete.
"""

VERSION = '2.0'

import os
import shutil
import subprocess
import sys

from pathlib import Path

from ..archive.plugin import Discovery, Plugin, needs_privilege, remove_command, run


class PathsPlugin(Plugin):
    name = 'paths'

    #: Last: whatever the specific plugins did not claim.
    order = 90

    version = VERSION

    def discover(self, request):
        given = request.options.get('paths') or []

        if not given:
            return Discovery(score=0.0)

        paths = []

        for entry in given:
            path = Path(entry).expanduser()

            if not path.exists():
                self.log("{} does not exist, skipping", path)
                continue

            resolved = str(path.resolve())

            if resolved not in paths:
                paths.append(resolved)

        if not paths:
            return Discovery(score=0.0)

        discovery = Discovery(score=1.0, data={
            'paths': paths,
            # Whether sudo may be used at all; even when true, it is only
            # reached for on paths that genuinely need it.
            'sudo': os.geteuid() != 0,
        })

        discovery.var('paths.extra', paths)

        self.log("{} extra path(s)", len(paths))

        return discovery

    def pack(self, request):
        meta = request.meta_dir / 'paths'
        meta.mkdir(parents=True, exist_ok=True)

        for entry in request.data.get('paths') or []:
            source = Path(entry)

            if not source.exists():
                self.log("{} has gone missing, skipping", source)
                continue

            target = meta / source.relative_to(source.anchor)
            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                if source.is_dir():
                    shutil.copytree(str(source), str(target), symlinks=True,
                                    dirs_exist_ok=True)
                else:
                    shutil.copy2(str(source), str(target))
            except OSError as e:
                self.log("could not copy {} ({})", source, e)
                continue

            self.log("saved {}", source)

        return {}

    def remove(self, request):
        data = request.data
        sudo = data.get('sudo', os.geteuid() != 0)

        for entry in data.get('paths') or []:
            path = Path(entry)

            if not path.exists():
                continue

            try:
                command = remove_command(path, recursive=True)
            except ValueError as e:
                self.log("{}", e)
                continue

            self.log("removing {}", path)

            if sudo and os.geteuid() != 0 and needs_privilege(path):
                command = ['sudo'] + command

            if subprocess.call(command) != 0:
                self.log("failed to remove {}", path)

        return {}


def main():
    sys.exit(run(PathsPlugin))
