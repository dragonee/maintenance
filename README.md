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

# Development

```
python3 -m venv env
. env/bin/activate
pip install -e .
```

