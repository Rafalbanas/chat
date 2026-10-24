#!/usr/bin/python3
"""Add the chat virtual host, validating before a graceful Nginx reload."""
from pathlib import Path
import shutil
import subprocess

SOURCE = Path(__file__).resolve().parents[1]
for directory in ['assets', 'config', 'ops', 'tests']:
    if (SOURCE / directory).exists():
        shutil.copytree(SOURCE / directory, Path('/opt/private-chat') / directory, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
for name in ['compose.yaml', 'README.md']:
    shutil.copy2(SOURCE / name, Path('/opt/private-chat') / name)
files = {
    Path('/etc/nginx/snippets/private-chat-proxy.conf'): SOURCE / 'config/private-chat-proxy.conf',
    Path('/etc/nginx/snippets/private-chat-cloudflare.conf'): SOURCE / 'config/private-chat-cloudflare.conf',
    Path('/etc/nginx/sites-available/chat.banas.dev.conf'): SOURCE / 'config/chat.banas.dev.conf',
}
if any(p.exists() for p in files) or Path('/etc/nginx/sites-enabled/chat.banas.dev.conf').exists():
    raise SystemExit('Chat proxy already exists; inspect before updating.')
link = Path('/etc/nginx/sites-enabled/chat.banas.dev.conf')
try:
    for dest, source in files.items():
        shutil.copy2(source, dest)
    link.symlink_to('/etc/nginx/sites-available/chat.banas.dev.conf')
    subprocess.run(['nginx', '-t'], check=True)
except BaseException:
    link.unlink(missing_ok=True)
    for path in files:
        path.unlink(missing_ok=True)
    raise
subprocess.run(['systemctl', 'reload', 'nginx'], check=True)
print('Chat virtual host enabled. Existing site files untouched; Nginx reloaded gracefully.')
