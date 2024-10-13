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
    eternalize [options] FILE...

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

This is a suite of programs to pack up finished projects (with databases and such),
and upload them to a specified location on a remote server.

The unarchive command reverses this process.

## archive (1.0)

```
Package a specific directory, then store it in a storage.

Usage:
    archive [options] DIR [--] [ARGS...]
    archive --help
    archive --version

Options:
    -p         Preserve the directory.
    -s STORAGE  Use specific storage command [default: ssh]
    --help     Display this message.
    --version  Display version information.
```

## archive-pack-wordpress (1.0)

```
Pack an existing Wordpress installation.

Usage:
    archive-pack-wordpress [--db DATABASES] [-o OUTPUT] -m META_DIR DIR
    archive-pack-wordpress --check DIR
    archive-pack-wordpress -h | --help
    archive-pack-wordpress --version

Options:
    --check         Check if directory is a Wordpress instalation, return 0..1.
    -m META_DIR     Use this directory for meta storage.
    -o OUTPUT       Write archive to this file.
    --db DATABASES  A comma-separated list of databases.
    -h, --help      Display this message.
    --version       Show version information.
```

## archive-pack-bedrock (1.0)

```
Pack an existing Bedrock Wordpress installation.

Usage:
    archive-pack-bedrock [--db DATABASES] [-o OUTPUT] -m META_DIR DIR
    archive-pack-bedrock --check DIR
    archive-pack-bedrock -h | --help
    archive-pack-bedrock --version

Options:
    --check         Check if directory is a Wordpress instalation, return 0..1.
    -m META_DIR     Use this directory for meta storage.
    -o OUTPUT       Write archive to this file.
    --db DATABASES  A comma-separated list of databases.
    -h, --help      Display this message.
    --version       Show version information.
```

## archive-pack-generic (1.0)

```
Pack a generic directory.

Usage:
    archive-pack-generic [-o OUTPUT] -m META_DIR DIR
    archive-pack-generic --check DIR
    archive-pack-generic -h | --help
    archive-pack-generic --version

Options:
    --check         Check if directory is a Wordpress instalation, return 0..1.
    -m META_DIR     Use this directory for meta storage.
    -o OUTPUT       Write archive to this file.
    --db DATABASES  A comma-separated list of databases.
    -h, --help      Display this message.
    --version       Show version information.
```

## archive-mysql (1.0)

```
Save MySQL database dump and user info for restoration later.

Usage:
    archive-mysql [options] DATABASE DUMP_DIRECTORY
    archive-mysql [options] DATABASES... -o DUMP_DIR
    archive-mysql -h | --help
    archive-mysql --version

Options:
    -o DUMP_DIR     Put output dumps into this directory.
    -c OUT_CONFIG   Write config to the specified file [default: -]
    --user USER     Username.
    --pass PASS     Use this password.
    --host HOST     Use this host [default: localhost].
    --users USERS   A comma-separated lists of user=password pairs.
                    See USER-PASSWORD PAIRS below to
    -h, --help      Display this message.
    --version       Show version information.

USER-PASSWORD PAIRS

There are three ways to specify user-password pairs:

user1, ...          Will ask for passwords.
user1=pass1, ...    Will store passwords given.
user1=, ...         Won't ask now, will ask for a new one when unarchiving.
```

## archive-teardown-mysql (1.0)

```
Drop MySQL databases for this archive.

Usage:
    archive-teardown-mysql [options] META_DIR
    archive-teardown-mysql --help
    archive-teardown-mysql --version

Options:
    -r REMOTE  Put file in the.
    --help     Display this message.
    --version  Display version information.
```

## archive-pgsql (1.0)

```
Save PostgreSQL database dump and user info for restoration later.

Usage:
    archive-pgsql [options] DATABASE DUMP_DIRECTORY
    archive-pgsql [options] DATABASES... -o OUT_DUMP
    archive-pgsql --check DIRECTORY
    archive-pgsql -h | --help
    archive-pgsql --version

Options:
    -c OUT_CONFIG   Write config to the specified file [default: -]
    -o OUT_DUMP     Write dumps to the specified directory.
    --user USER     Username.
    --pass PASS     Use this password.
    --host HOST     Use this host [default: localhost].
    --users USERS   A comma-separated lists of user=password pairs.
                    See USER-PASSWORD PAIRS below to
    --check DIRECTORY   Check if this plugin can archive this directory.
    -h, --help      Display this message.
    --version       Show version information.

USER-PASSWORD PAIRS

There are three ways to specify user-password pairs:

user1, ...          Will ask for passwords.
user1=pass1, ...    Will store passwords given.
user1=, ...         Won't ask now, will ask for a new one when unarchiving.
```

## archive-check (1.0)

```
Wait on specific resource lock and then run a command.

Usage:
    archive-check [options] DIRS...
    archive-check --help
    archive-check --version

Options:
    -a         Show all entries, even those with 0.0 score.
    -l         Use long format, even if one item was used.
    --help     Display this message.
    --version  Display version information.
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
```

You can use it like this:

```
markdown_command README.md.in > README.md
```
