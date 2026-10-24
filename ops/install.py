#!/usr/bin/python3
"""Install only the private-chat stack; no changes to existing services."""
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import subprocess
import time

SOURCE = Path(__file__).resolve().parents[1]
DEST = Path('/opt/private-chat')
ETC = Path('/etc/private-chat')


def run(*args):
    subprocess.run(args, check=True)


if os.geteuid() != 0:
    raise SystemExit('Run as the server administrator.')
if DEST.exists():
    raise SystemExit('Existing install found. Use the documented update procedure.')
stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
backup = Path('/storage/private-chat-backups')
if not os.path.ismount('/storage'):
    raise SystemExit('Separate /storage mount unavailable; refusing installation.')
backup.mkdir(mode=0o700, exist_ok=True)
snapshot = backup / ('before-install-' + stamp)
snapshot.mkdir(mode=0o700)
configs = list(Path('/etc/nginx').rglob('*.conf')) + [Path('/etc/nginx/nginx.conf'), Path('/etc/caddy/Caddyfile')]
hashes = {}
for file in configs:
    if file.is_file():
        data = file.read_bytes()
        hashes[str(file)] = hashlib.sha256(data).hexdigest()
        target = snapshot / file.relative_to('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
(snapshot / 'hashes.json').write_text(json.dumps(hashes, indent=2))
try:
    account = pwd.getpwnam('privatechat')
except KeyError:
    run('useradd', '--system', '--user-group', '--no-create-home', '--home-dir', '/var/lib/private-chat', '--shell', '/usr/sbin/nologin', 'privatechat')
    account = pwd.getpwnam('privatechat')
shutil.copytree(SOURCE, DEST, ignore=shutil.ignore_patterns('.env', '.git', '__pycache__', 'audit', 'data', 'backups'))
for path in [Path('/var/lib/private-chat'), Path('/var/lib/private-chat/data')]:
    path.mkdir(mode=0o700, exist_ok=True)
    os.chown(path, account.pw_uid, account.pw_gid)
ETC.mkdir(mode=0o700, exist_ok=True)
password = 'Aa9!' + secrets.token_urlsafe(30)
values = {
    'OPEN_WEBUI_IMAGE': 'ghcr.io/open-webui/open-webui@sha256:912c133d2dcecb8d74662f9be64b1f00f303a0d8c0836cbb30fd156f65652f5f',
    'WEBUI_PORT': '18084',
    'OLLAMA_BASE_URL': 'http://127.0.0.1:18085',
    'APP_UID': str(account.pw_uid),
    'APP_GID': str(account.pw_gid),
    'WEBUI_SECRET_KEY': secrets.token_urlsafe(48),
    'WEBUI_ADMIN_EMAIL': 'admin@banas.dev',
    'WEBUI_ADMIN_PASSWORD': password,
}
env = ETC / 'app.env'
with os.fdopen(os.open(env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
    f.write(''.join(k + '=' + v + '\n' for k, v in values.items()))
with os.fdopen(os.open(ETC / 'initial-login.txt', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as f:
    f.write('Adres: https://chat.banas.dev\nLogin: admin@banas.dev\nHasło: ' + password + '\nZmień hasło po pierwszym logowaniu i usuń ten plik.\n')
shutil.copy2(DEST / 'config/private-chat-gpu-status.service', '/etc/systemd/system/private-chat-gpu-status.service')
unit = '''[Unit]
Description=Banas private chat (Open WebUI and Ollama policy)
Requires=docker.service private-chat-gpu-status.service
After=docker.service private-chat-gpu-status.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/private-chat
ExecStart=/usr/bin/docker compose --env-file /etc/private-chat/app.env up -d --wait --wait-timeout 240
ExecStop=/usr/bin/docker compose --env-file /etc/private-chat/app.env stop
TimeoutStartSec=300
TimeoutStopSec=45

[Install]
WantedBy=multi-user.target
'''
Path('/etc/systemd/system/private-chat.service').write_text(unit)
run('systemctl', 'daemon-reload')
run('systemctl', 'enable', '--now', 'private-chat-gpu-status.service')
run('docker', 'compose', '--project-directory', str(DEST), '--env-file', str(env), 'config', '--quiet')
run('systemctl', 'enable', '--now', 'private-chat.service')
print('Application installed on loopback only. Existing Nginx configuration unchanged.')
print('Bootstrap credentials stored in /etc/private-chat/initial-login.txt (0600).')
