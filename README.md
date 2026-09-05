# Tools

## notify-on-exit (1.0)

```
Wait for specific process to finish, then notify via Pushover API.

Usage:
    notify-on-exit [options] PID [MESSAGE]

Options:
    -p          High priority (this message will pop on phone).
    -b          Run in background.
    --version   Show version information.
    -h, --help  Show this message.
```

## notify-when-done (1.0)

```
Call specific process. On finish, notify via Pushover API.

Usage:
    notify-when-done [options] [--] COMMAND...

Options:
    -p          High priority (this message will pop on phone).
    -m MESSAGE  Print specific message.
    --version   Show version information.
    -h, --help  Show this message.
```

## coordinate (1.0)

```
Wait on specific resource lock and then run a command.

Usage:
    coordinate [-h HOST] RESOURCE [--] COMMAND...
    coordinate --help
    coordinate --version

Options:
    -h HOST    Use specific Redis host.
    --help     Display this message.
    --version  Display version information.
```

## arduino (1.0)

```
Send a message to Arduino Coordinate device.

Usage:
    arduino [-d DEVICE] relay [RELAYS...]
    arduino [-d DEVICE] led [LEDS...]
    arduino -h | --help
    arduino --version

RELAYS can be from {0, 1}
LEDS can be from {0, 1, 2, 3}

Options:
    -d DEVICE   Device to communicate with Arduino [default: /dev/ttyACM0].
    -h, --help  Display this message.
    --version   Show version information.
```

# YouTube processing pipeline

This is a suite of programs to download YouTube Watch Later queue, and limit
the user in watching too much content.

## yt-remove-watchlater (1.0)

```
Automatically remove N first videos from Youtube Watch Later playlist.

Usage:
    yt-remove-watch-later [-n NUMBER] [-c COOKIES]
    yt-remove-watch-later -h | --help
    yt-remove-watch-later --version

Options:
    -c COOKIES  Path to cookie file.
    -n NUMBER   Remove only N entries.
    -h, --help  Print this message.
    --version   Print version information.

Other considerations:

This program uses webscraping, because currently Youtube API cannot access
Watch Later Playlist.
```

## yt-download-watch-later (1.0)

```
Download Youtube Watch Later playlist to a local directory, eternalize it,
then remove playlist.

Usage:
    yt-download-watch-later [options]

Options:
    -h, --help  Display this message.
    --version   Show version information.
```

## video-feed (1.0)

```
Get feed of NUMBER minutes of video files from remote directory.

Download Watch Later videos with yt-download-watch-later.

Usage:
    video-feed [-n NUMBER] [-c] [DIRECTORY]
    video-feed -h | --help
    video-feed --version

Options:
    -c          Check local and remote pool.
    -n NUMBER   Download enough files to satisfy this period [default: 60].
    -h, --help  Display this message.
    --version   Show version information.
```

## video-lengths (1.0)

```
Get lengths (in full seconds) of all videos present in a directory.

Usage:
    video-lengths [-f FORMAT] [-c CACHE] [-t] DIRECTORY
    video-lengths -h | --help
    video-lengths --version

Options:
    -f FORMAT   Format - text or json [default: text].
    -c CACHE    Cache lengths. Assume files don't change.
    -t          Sort by last modified time.
    -h, --help  Display this message.
    --version   Show version information.
```

# Eternalize

Assuming:

- that you have a workstation and a backup NAS with SSH access;
- that you backup (through rsync) workstation contents to this server;

the eternalize tool will help you to permanently store the files on the server,
by moving them from the backup directory to some other specified destination,
(e.g. Movies, Documents, Pictures), and then, removing them from the workstation.

## eternalize (1.0)

```
Move files from backup to another directory on remote server.

Usage:
    eternalize [options] [FILE...]
    eternalize add [options] TARGET PATH

When called without FILE arguments, displays available targets on the remote server.
The 'add' command appends a new target configuration to the remote .eternalize.ini file.

TARGET can be:
    Folder
    Folder/Directory, which will create a directory and put file inside
    Folder/*, which will try to match the closest directory

Options:
    -p          Preserve the file on the computer.
    -s SERVER   Specify server configuration.
    -d          Dry run (use this for testing).
    -h, --help  Display this text.
    --version   Display version information.
```

## eternalize-locate (1.0)

```
Locate files on the endpoint of eternalize command and return them
in a structured format.

Usage:
    eternalize-locate [options] PATH TARGET

TARGET can be:
    Folder
    Folder/Directory, which will create a directory and put file inside
    Folder/*, which will try to match the closest directory

Options:
    -b BACKUP   Backup base path.
    -p PATTERN  Use the following pattern to find directory.
    -f FORMAT   Set output format (text, json) [default: text].
    -h, --help  Display this text.
    --version   Display version information.
```

## eternalize-resolve-conflict (1.0)

```
Resolve conflicts when there are two versions of a file/directory.

Usage:
    eternalize-resolve-conflict MOVE_FROM MOVE_TO

Options:
    -h, --help  Display this text.
    --version   Display version information.
```

# Archive tool

This is a suite of programs to pack up finished projects (with databases,
server configuration and whatever else they left lying around a server), and
upload them to a specified location on a remote server.

## Workflow

The work happens in three steps, so that the decisions are made while a human
is still watching and the destructive part is never a side effect of the
useful part.

```
archive discover /srv/example.com --path /etc/cron.d/example > example.yaml
$EDITOR example.yaml
archive pack example.yaml
archive remove example.yaml
```

**Discovery** is read-only. Every plugin looks at the directory and reports
what it recognised, and the result is a plan: a YAML file describing exactly
what would be archived and removed. Nothing is dumped, nothing is deleted,
and no password is asked for.

**Packing** does what the plan says, without looking around again. A plan made
in the morning still packs the same thing in the evening, even if someone
edited a vhost in between.

**Removal** is a separate command on purpose. It re-reads the plan, asks for
the privileged credentials it needs at that moment, shows you what is about to
be destroyed, and only then drops the databases, deletes the configuration and
removes the directory.

## Plugins

A plugin is any executable on your `PATH` named `archive-plugin-*`. The driver
runs it with no arguments, writes a JSON request to its stdin, and reads a
YAML response from its stdout, so a plugin can be written in any language.
Nothing interesting travels in `argv`, which every user on the machine can
read out of `ps`.

Plugins are additive: one directory can be a Bedrock installation *and* have a
PostgreSQL database *and* an nginx vhost *and* three stray files in `/etc`,
each handled by the plugin that understands it. They cooperate through the
environment, a shared dictionary of **vars** and **secrets**:

- **vars** are ordinary values. They are written to the plan, printed, and
  treated as documentation of what will happen. `archive-plugin-wordpress`
  publishes `mysql.databases` during discovery and `archive-plugin-mysql`
  picks it up on its own pass, which is why detecting an installation and
  dumping its database are two different plugins.
- **secrets** are never printed and never written anywhere. A plugin can read
  one to do its job, and anyone can ask whether one is present, but only the
  *name* and origin of a secret reach the plan file. That is what makes a plan
  safe to commit or mail.

Because secrets are not stored, they are resolved again on every run, from the
process environment first, then from the installation's own configuration
files, then by asking you. Discovery declares which secrets will be needed;
packing and removal fetch them.

Ordering is declared by each plugin: detectors run at 10, the services that
act on what they found at 50, catch-alls at 90.

## Root access

Dropping a database, deleting its owner, or removing a file from `/etc` needs
rights the person running `archive` usually does not have. Nothing privileged
is carried in the plan: those credentials are resolved during
`archive remove`, at the moment they are needed.

There are two ways a database server lets an administrator in, and both are
supported.

**With a password**, supply it through the environment for unattended runs,
or let it prompt:

```
ARCHIVE_MYSQL_ROOT_PASSWORD=... archive remove example.yaml -y
ARCHIVE_POSTGRESQL_SUPERUSER_PASSWORD=... archive remove example.yaml -y
```

**Without one.** On most current installations the administrator does not
have a password at all: MySQL and MariaDB authenticate `root@localhost`
through `auth_socket`, and PostgreSQL authenticates `postgres` through
`peer`. There is nothing to type and nothing to put in a variable. When no
password turns up, removal falls back to `sudo mysql` and
`sudo -u postgres psql`, which is how those servers expect to be
administered. The statements go in on stdin, so they do not appear in `ps`
either.

Which way it goes is visible in the plan and can be forced:

```
vars:
  mysql.admin_user: root
  mysql.admin_auth: auto        # auto | password | socket
  postgresql.superuser: postgres
  postgresql.superuser_auth: auto   # auto | password | peer
```

On a machine running several PostgreSQL clusters, every call names its port
and uses the client binary matching that cluster's major version. This is
not fussiness: `pg_dump` refuses to dump a server newer than itself, and two
clusters routinely hold databases of the same name -- an old application on
one and its replacement on another -- so a `psql` that does not name a port
will cheerfully drop the wrong one.

`auto` uses a password if one turns up and sudo otherwise. `password`
insists on one and fails loudly if it is missing, which is what you want on a
server where sudo would silently do the wrong thing. `socket` and `peer`
never ask for a password at all.

Removing *files* needs no configuration: `sudo` is reached for only on paths
that are genuinely not yours to delete.

## archive (2.0)

```
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
```

## archive-plugin-wordpress (2.0)

```
Recognise a classic WordPress installation and describe its database.

This plugin does not dump anything. It reads wp-config.php, publishes what
it found as mysql.* variables, and lets archive-plugin-mysql do the work.
That split is what lets one directory be a WordPress site *and* have a
Caddy vhost *and* a handful of extra config files, each handled by the
plugin that understands it.
```

## archive-plugin-bedrock (2.0)

```
Recognise a Bedrock-flavoured WordPress installation.

Bedrock keeps its credentials in a dotenv file and its WordPress under
web/wp, so it needs its own detector, but it publishes the same mysql.*
variables as archive-plugin-wordpress and is handled identically downstream.
```

## archive-plugin-django (1.0)

```
Read a Django settings module and describe the database it configures.

Django keeps its database in a DATABASES dict, usually in a settings
package split across several files. Where that dict is written out
literally this plugin reads it; where it is computed -- `env.db()` and
friends -- there is nothing to read, and the credentials are in an env
file that archive-plugin-env should be pointed at instead:

    archive discover /srv/example.com \
        --env /srv/environments/example/example.env

The settings file is parsed, never imported or executed. Importing a
project's settings to find out where its database lives would run whatever
that project runs at import time, on a machine where the application is
being decommissioned; ast.literal_eval reads the dict and refuses anything
that is not a plain value.

sqlite is recognised and deliberately ignored: the database is a file
inside the directory, so the archive already contains it.
```

## archive-plugin-env (1.0)

```
Read an env file and describe the database it points at.

Applications keep their credentials in a dotenv file, and often not inside
the directory being archived: a shared environments directory beside the
docroot is a common arrangement, and a site archived without it is a site
that cannot be restored. Point this plugin at the file:

    archive discover /srv/example.com \
        --env /srv/environments/example/example.env

The file is copied into the archive, and removed with the installation when
it lives outside the directory. A dotenv usually holds far more than a
database password -- API tokens, mail credentials, signing keys -- so the
archive is only as safe as wherever you store it. The plan itself stays
clean: it records the path and the database settings, never a value.

Two shapes are understood, which between them cover most frameworks:

    DATABASE_URL=postgres://user:pass@localhost:5433/example
    DB_CONNECTION=mysql, DB_DATABASE, DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT

A `.env` in the archived directory is picked up automatically, but only
when no earlier plugin has already described a database -- a detector that
understands the application knows better than a generic reader.

Set ARCHIVE_ENV_PATHS to a colon-separated list to always search the same
locations without passing --env every time.
```

## archive-plugin-mysql (2.0)

```
Dump and later drop the MySQL databases belonging to an installation.

The databases are not detected here. A detector plugin (wordpress, bedrock,
or anything you write) publishes mysql.databases, mysql.host and mysql.user
during discovery, and this plugin picks them up. Failing that, it will read
a DATABASE_URL out of a dotenv file in the directory itself.

Credentials never appear in argv, where every user on the machine can read
them out of ps: mysqldump is handed a 0600 defaults file instead.

By default the dump records which users existed but not their passwords, so
nothing secret is written into the archive. Set

    mysql.store_credentials: true

in the plan to embed them, for an installation you expect to restore
unattended.

Removal needs an administrator. If a password is available -- from
ARCHIVE_MYSQL_ROOT_PASSWORD, from ~/.archive.ini, or from a prompt -- it
connects with it. If none is, it falls back to `sudo mysql`, because a great
many servers authenticate root through auth_socket, where there is no
password to give and asking for one would deadlock.

Two plan vars steer this: mysql.admin_user names the administrator, and
mysql.admin_auth is auto (the above), password (insist on one) or socket
(always sudo, never ask).
```

## archive-plugin-postgresql (2.0)

```
Dump and later drop the PostgreSQL databases belonging to an installation.

Works the same way as archive-plugin-mysql: a detector plugin publishes
postgresql.databases during discovery, or this plugin reads a DATABASE_URL
out of a dotenv file in the directory itself. Django, Rails and Laravel
projects are usually recognised by that alone.

pg_dump and psql are driven through a 0600 PGPASSFILE rather than a
password on the command line or in the environment.

Where a machine runs several clusters side by side, every call names its
port and uses the client binary matching that cluster's major version --
pg_dump refuses to dump a server newer than itself, and two clusters
routinely hold databases of the same name, an old application on one and
its replacement on another.

Removal needs a superuser. If a password is available -- from
ARCHIVE_POSTGRESQL_SUPERUSER_PASSWORD, from ~/.archive.ini, or from a prompt
-- it connects over TCP with it. If none is, it falls back to
`sudo -u postgres psql`, which is how a default install expects to be
administered: the postgres role uses peer authentication and has no password
to give. Set postgresql.superuser_auth in the plan to force either way.

Open connections to the database are terminated first, because PostgreSQL
refuses to drop a database anyone is still using.
```

## archive-plugin-nginx (2.0)

```
Archive and remove the nginx configuration pointing at an installation.

Discovery searches the usual configuration directories for files that name
the directory being archived, and records both the sites-enabled symlink
and the file it points at, since disabling a site and deleting it are
different acts.

Packing copies the configuration into meta/nginx/, keeping the absolute
layout so a restore knows where each file belongs. Removal deletes them,
runs nginx -t, and reloads only if the remaining configuration is valid.

Configuration under /etc is not usually writable by the user running
archive, so removal shells out through sudo unless already running as root.

Set ARCHIVE_NGINX_CONFIG_PATHS to a colon-separated list to search
somewhere other than the standard locations.
```

## archive-plugin-caddy (2.0)

```
Archive and remove the Caddy configuration pointing at an installation.

Behaves exactly like archive-plugin-nginx, differing only in where Caddy
keeps its files and how a site address is written. A Caddyfile that serves
several unrelated sites is copied whole and reported, but removing it would
take the other sites down too, so check what discovery found before running
archive remove.

Set ARCHIVE_CADDY_CONFIG_PATHS to a colon-separated list to search
somewhere other than the standard locations.
```

## archive-plugin-paths (2.0)

```
Archive and remove files and directories that live outside the project.

An installation is rarely confined to one directory. There is a cron job in
/etc/cron.d, a unit file in /etc/systemd/system, a logrotate rule, a socket
directory under /var. Nothing can detect those reliably, so they are named
explicitly:

    archive discover /srv/example.com \
        --path /etc/cron.d/example \
        --path /etc/systemd/system/example.service \
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
```

## archive-compress (1.0)

```
Compress meta directory and target directory into one tar archive.

Usage:
    archive-compress [options] DIR FILE
    archive-compress -h | --help
    archive-compress --version

Options:
    -v              Be verbose.
    -m META_DIR     Path to meta directory.
    -f FORMAT       Format: gz, bz2 or xz [default: gz]
    -h, --help      Display this message.
    --version       Show version information.
```

## archive-store-ssh (1.0)

```
Store a file in the remote storage.

Usage:
    archive-store-ssh [options] FILE
    archive-store-ssh --help
    archive-store-ssh --version

Options:
    -r REMOTE  Put file in the.
    --help     Display this message.
    --version  Display version information.
```

# Services and daemons

## coordinate-arduino (1.0)

```
Monitor status of specific Redis locks and communicate it to Arduino.

Run with supervisor, as it doesn't daemonize or check for its health.

Usage:
    coordinate-arduino [-d DEVICE] [-s DEVICES] [-f] LOCKS...
    coordinate-arduino -h | --help
    coordinate-arduino --version

LOCKS are an ordered list of Redis keys to poll.

Options:
    -f          Flatten all locks to the least-significant bit.
    -d DEVICE   Device to communicate with Arduino [default: /dev/ttyACM0].
    -s DEVICES  Scan for available devices with glob patterns.
    -h, --help  Display this message.
    --version   Show version information.
```

# Development

```
python3 -m venv env
. env/bin/activate
pip install -e .
```

For ease of development, automated README generation is provided.

## make-readme (1.0)

```
Generate automatic command index from a program.

Usage:
    make-readme [options] COMMAND

It outputs a Markdown section with program name, 
help and version information.

Works for any installed program that has --help
and --version options. Especially useful for Docopt.
It can be used with the following command to generate readme files:
    pip install -e .

Options:
    -h LEVEL, --heading LEVEL  Start from hLEVEL heading [default: 2].
    --help     Display this message.
    --version  Display version information.
```

## markdown-command (1.1)

```
Process a Markdown file, execute commands within 
and print file contents with executed commands' output.

Usage:
    markdown-command [options] FILE

The pattern for commands to be executed is:
    [$ command --with-options -and arguments]

Options:
    -h, --help               Display this message.
    --version                Display version information.
    --dry-run                Do not execute commands, just print them.
    -O, --only-commands      Only run commands, do not print file contents.
    -C, --cwd PATH           Change to directory before running commands.
```

You can use it like this:

```
markdown_command README.md.in > README.md
```
