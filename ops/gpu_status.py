#!/usr/bin/python3
"""Read only CV task states; publish a boolean. Never modify CV Tailor data."""
import json
import os
import time
from pathlib import Path

BASE = Path('/var/lib/cvtailor/production')
OUTPUT = Path('/run/private-chat/gpu.json')


def status():
    for mode in ('main', 'demo'):
        directory = BASE / mode / 'tasks'
        if not directory.is_dir():
            return True
        for path in directory.glob('*.json'):
            if json.loads(path.read_text()).get('status') in {'running', 'queued'}:
                return True
    return False


while True:
    try:
        busy = status()
    except (OSError, ValueError):
        busy = True
    temp = OUTPUT.with_suffix('.tmp')
    temp.write_text(json.dumps({'at': time.time(), 'busy': busy}))
    os.chmod(temp, 0o644)
    temp.replace(OUTPUT)
    time.sleep(0.5)
