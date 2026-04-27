import json
import os

from .config import ROOT

_STATE_FILE = os.path.join(ROOT, '.cursor.json')


def load():
    if not os.path.exists(_STATE_FILE):
        return {}
    try:
        with open(_STATE_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save(state):
    with open(_STATE_FILE, 'w') as f:
        json.dump(state, f)
