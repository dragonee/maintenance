# Tools

## notify-on-pid

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

## notify-when-done

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

## coordinate

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

## yt-remove-watchlater

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

## yt-download-watch-later

```
Download Youtube Watch Later playlist to a local directory, eternalize it,
then remove playlist.

Usage:
    yt-download-watch-later [options]

Options:
    -h, --help  Display this message.
    --version   Show version information.

```

## video-feed

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

## video-lengths

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

## coordinate-arduino

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
