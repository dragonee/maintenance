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

# Development

```
python3 -m venv env
. env/bin/activate
pip install -e .
```

