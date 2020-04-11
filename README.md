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

## make-readme (1.0)

```
Generate automatic command index from a module's docstring.

Usage:
    make-readme FILE
    make-readme --help
    make-readme --version


Parses the following tag (one per line):
    [command-name=path.to.module]

Works when module is installed (e.g. by pip install -e .)

Options:
    --help     Display this message.
    --version  Display version information.
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

# Services and daemons


## coordinate-arduino (1.0)

```
Monitor status of specific Redis locks and communicate it to Arduino.

Run with supervisor, as it doesn't daemonize or check for its health.

Usage:
    coordinate-arduino [-d DEVICE] [-f] LOCKS...
    coordinate-arduino -h | --help
    coordinate-arduino --version

LOCKS are an ordered list of Redis keys to poll.

Options:
    -f          Flatten all locks to the least-significant bit.
    -d DEVICE   Device to communicate with Arduino [default: /dev/ttyACM0].
    -h, --help  Display this message.
    --version   Show version information.
```

# Development

```
python3 -m venv env
. env/bin/activate
pip install -e .
```

## Git hooks

The `hooks` directory has hooks that are useful with this application.
