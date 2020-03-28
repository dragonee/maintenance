
import requests

from .config.pushover import PushoverConfigFile

def notify(message, title=None, priority=None):
    c = PushoverConfigFile()

    payload = {
        'user': c.user,
        'token': c.token,
        'message': message,
    }

    if title:
        payload['title'] = title

    if priority:
        payload['priority'] = priority

    requests.post(
        'https://api.pushover.net/1/messages.json',
        data=payload
    )