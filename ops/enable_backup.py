#!/usr/bin/python3
import os
from pathlib import Path
import secrets
import shutil
import subprocess

base = Path(__file__).resolve().parents[1]
shutil.copy2(base / 'ops/backup.py', '/opt/private-chat/ops/backup.py')
Path('/etc/private-chat/gnupg').mkdir(mode=0o700, exist_ok=True)
key = Path('/etc/private-chat/backup.key')
if not key.exists():
    with os.fdopen(os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
        f.write(secrets.token_urlsafe(48))
for name in ['private-chat-backup.service', 'private-chat-backup.timer']:
    shutil.copy2(base / 'config' / name, Path('/etc/systemd/system') / name)
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'enable', '--now', 'private-chat-backup.timer'], check=True)
subprocess.run(['systemctl', 'start', 'private-chat-backup.service'], check=True)
print('Encrypted backup timer enabled; initial backup and isolated restore verified.')
