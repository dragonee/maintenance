from fabric.transfer import Transfer as BaseTransfer, Result
from fabric.util import debug  # TODO: actual logging! LOL


import os
import posixpath
import stat

import subprocess
from pathlib import Path

class Transfer(BaseTransfer):
    def get(self, remote, local=None, preserve_mode=True, callback=None):
        """
        Download a file from the current connection to the local filesystem.
        :param str remote:
            Remote file to download.
            May be absolute, or relative to the remote working directory.
            .. note::
                Most SFTP servers set the remote working directory to the
                connecting user's home directory, and (unlike most shells) do
                *not* expand tildes (``~``).
                For example, instead of saying ``get("~/tmp/archive.tgz")``,
                say ``get("tmp/archive.tgz")``.
        :param local:
            Local path to store downloaded file in, or a file-like object.
            **If None or another 'falsey'/empty value is given** (the default),
            the remote file is downloaded to the current working directory (as
            seen by `os.getcwd`) using its remote filename.
            **If a string is given**, it should be a path to a local directory
            or file and is subject to similar behavior as that seen by common
            Unix utilities or OpenSSH's ``sftp`` or ``scp`` tools.
            For example, if the local path is a directory, the remote path's
            base filename will be added onto it (so ``get('foo/bar/file.txt',
            '/tmp/')`` would result in creation or overwriting of
            ``/tmp/file.txt``).
            .. note::
                When dealing with nonexistent file paths, normal Python file
                handling concerns come into play - for example, a ``local``
                path containing non-leaf directories which do not exist, will
                typically result in an `OSError`.
            **If a file-like object is given**, the contents of the remote file
            are simply written into it.
        :param bool preserve_mode:
            Whether to `os.chmod` the local file so it matches the remote
            file's mode (default: ``True``).
        :returns: A `.Result` object.
        .. versionadded:: 2.0
        """
        # TODO: how does this API change if we want to implement
        # remote-to-remote file transfer? (Is that even realistic?)
        # TODO: handle v1's string interpolation bits, especially the default
        # one, or at least think about how that would work re: split between
        # single and multiple server targets.
        # TODO: callback support
        # TODO: how best to allow changing the behavior/semantics of
        # remote/local (e.g. users might want 'safer' behavior that complains
        # instead of overwriting existing files) - this likely ties into the
        # "how to handle recursive/rsync" and "how to handle scp" questions

        # Massage remote path
        if not remote:
            raise ValueError("Remote path must not be empty!")
        orig_remote = remote
        remote = posixpath.join(
            self.sftp.getcwd() or self.sftp.normalize("."), remote
        )

        # Massage local path:
        # - handle file-ness
        # - if path, fill with remote name if empty, & make absolute
        orig_local = local
        is_file_like = hasattr(local, "write") and callable(local.write)
        if not local:
            local = posixpath.basename(remote)
        if not is_file_like:
            local = os.path.abspath(local)

        # Run Paramiko-level .get() (side-effects only. womp.)
        # TODO: push some of the path handling into Paramiko; it should be
        # responsible for dealing with path cleaning etc.
        # TODO: probably preserve warning message from v1 when overwriting
        # existing files. Use logging for that obviously.
        #
        # If local appears to be a file-like object, use sftp.getfo, not get
        if is_file_like:
            self.sftp.getfo(remotepath=remote, fl=local, callback=callback)
        else:
            self.sftp.get(remotepath=remote, localpath=local, callback=callback)
            # Set mode to same as remote end
            # TODO: Push this down into SFTPClient sometime (requires backwards
            # incompat release.)
            if preserve_mode:
                remote_mode = self.sftp.stat(remote).st_mode
                mode = stat.S_IMODE(remote_mode)
                os.chmod(local, mode)
        # Return something useful
        return Result(
            orig_remote=orig_remote,
            remote=remote,
            orig_local=orig_local,
            local=local,
            connection=self.connection,
        )

    def put(self, local, remote=None, preserve_mode=True, callback=None):
        """
        Upload a file from the local filesystem to the current connection.
        :param local:
            Local path of file to upload, or a file-like object.
            **If a string is given**, it should be a path to a local (regular)
            file (not a directory).
            .. note::
                When dealing with nonexistent file paths, normal Python file
                handling concerns come into play - for example, trying to
                upload a nonexistent ``local`` path will typically result in an
                `OSError`.
            **If a file-like object is given**, its contents are written to the
            remote file path.
        :param str remote:
            Remote path to which the local file will be written.
            .. note::
                Most SFTP servers set the remote working directory to the
                connecting user's home directory, and (unlike most shells) do
                *not* expand tildes (``~``).
                For example, instead of saying ``put("archive.tgz",
                "~/tmp/")``, say ``put("archive.tgz", "tmp/")``.
                In addition, this means that 'falsey'/empty values (such as the
                default value, ``None``) are allowed and result in uploading to
                the remote home directory.
            .. note::
                When ``local`` is a file-like object, ``remote`` is required
                and must refer to a valid file path (not a directory).
        :param bool preserve_mode:
            Whether to ``chmod`` the remote file so it matches the local file's
            mode (default: ``True``).
        :returns: A `.Result` object.
        .. versionadded:: 2.0
        """
        if not local:
            raise ValueError("Local path must not be empty!")

        is_file_like = hasattr(local, "write") and callable(local.write)

        # Massage remote path
        orig_remote = remote
        if is_file_like:
            local_base = getattr(local, "name", None)
        else:
            local_base = os.path.basename(local)
        if not remote:
            if is_file_like:
                raise ValueError(
                    "Must give non-empty remote path when local is a file-like object!"  # noqa
                )
            else:
                remote = local_base
                debug("Massaged empty remote path into {!r}".format(remote))
        elif self.is_remote_dir(remote):
            # non-empty local_base implies a) text file path or b) FLO which
            # had a non-empty .name attribute. huzzah!
            if local_base:
                remote = posixpath.join(remote, local_base)
            else:
                if is_file_like:
                    raise ValueError(
                        "Can't put a file-like-object into a directory unless it has a non-empty .name attribute!"  # noqa
                    )
                else:
                    # TODO: can we ever really end up here? implies we want to
                    # reorganize all this logic so it has fewer potential holes
                    raise ValueError(
                        "Somehow got an empty local file basename ({!r}) when uploading to a directory ({!r})!".format(  # noqa
                            local_base, remote
                        )
                    )

        prejoined_remote = remote
        remote = posixpath.join(
            self.sftp.getcwd() or self.sftp.normalize("."), remote
        )
        if remote != prejoined_remote:
            msg = "Massaged relative remote path {!r} into {!r}"
            debug(msg.format(prejoined_remote, remote))

        # Massage local path
        orig_local = local
        if not is_file_like:
            local = os.path.abspath(local)
            if local != orig_local:
                debug(
                    "Massaged relative local path {!r} into {!r}".format(
                        orig_local, local
                    )
                )  # noqa

        # Run Paramiko-level .put() (side-effects only. womp.)
        # TODO: push some of the path handling into Paramiko; it should be
        # responsible for dealing with path cleaning etc.
        # TODO: probably preserve warning message from v1 when overwriting
        # existing files. Use logging for that obviously.
        #
        # If local appears to be a file-like object, use sftp.putfo, not put
        if is_file_like:
            msg = "Uploading file-like object {!r} to {!r}"
            debug(msg.format(local, remote))
            pointer = local.tell()
            try:
                local.seek(0)
                self.sftp.putfo(fl=local, remotepath=remote, callback=callback)
            finally:
                local.seek(pointer)
        else:
            debug("Uploading {!r} to {!r}".format(local, remote))
            self.sftp.put(localpath=local, remotepath=remote, callback=callback)
            # Set mode to same as local end
            # TODO: Push this down into SFTPClient sometime (requires backwards
            # incompat release.)
            if preserve_mode:
                local_mode = os.stat(local).st_mode
                mode = stat.S_IMODE(local_mode)
                self.sftp.chmod(remote, mode)
        # Return something useful
        return Result(
            orig_remote=orig_remote,
            remote=remote,
            orig_local=orig_local,
            local=local,
            connection=self.connection,
        )

    def rsync_put(self, local, remote):
        f = Path(local)

        if f.exists() and f.is_dir():
            local_path = "{}/".format(str(f))
            remote_path = '{}@{}:{}/'.format(self.connection.user, self.connection.host, remote)
        else:
            local_path = str(f)
            remote_path = '{}@{}:{}'.format(self.connection.user, self.connection.host, remote)

        args = [
            'rsync', '-avzs',
            '--progress', '-e', 'ssh',
            local_path,
            remote_path
        ]

        return subprocess.check_call(args)
