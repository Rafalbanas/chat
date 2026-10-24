#!/usr/bin/python3
"""Online SQLite snapshot, encrypted backups, and isolated restore verification."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import time

STORE = Path('/storage/private-chat-backups')
DATA = Path('/var/lib/private-chat/data')
KEY = Path('/etc/private-chat/backup.key')
GPG = ['gpg', '--homedir', '/etc/private-chat/gnupg', '--no-options', '--no-symkey-cache']


def file_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()


def hashes(root):
    return {str(p.relative_to(root)): file_hash(p) for p in root.rglob('*') if p.is_file() and p.name != 'hashes.json'}


def verify(archive):
    with tempfile.TemporaryDirectory(prefix='.verify-', dir=STORE) as name:
        base = Path(name)
        plain = base / 'backup.tar.gz'
        subprocess.run(GPG + ['--batch', '--quiet', '--pinentry-mode', 'loopback', '--passphrase-file', str(KEY), '--output', str(plain), '--decrypt', str(archive)], check=True)
        target = base / 'restored'
        target.mkdir()
        with tarfile.open(plain) as tar:
            tar.extractall(target, filter='data')
        expected = json.loads((target / 'hashes.json').read_text())
        if expected != hashes(target):
            raise RuntimeError('Backup hash verification failed')
        with sqlite3.connect(target / 'data/webui.db') as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Restored SQLite integrity check failed')
            counts = {t: db.execute('SELECT count(*) FROM "' + t + '"').fetchone()[0] for t in ('user', 'chat')}
        return counts


def backup():
    if not os.path.ismount('/storage') or os.stat('/storage').st_dev == os.stat('/').st_dev:
        raise RuntimeError('Separate storage mount unavailable')
    STORE.mkdir(mode=0o700, exist_ok=True)
    os.umask(0o077)
    with tempfile.TemporaryDirectory(prefix='.snapshot-', dir=STORE) as name:
        staging = Path(name)
        root = staging / 'snapshot'
        root.mkdir()
        shutil.copytree(DATA, root / 'data', ignore=shutil.ignore_patterns('webui.db', 'webui.db-wal', 'webui.db-shm', 'webui.db-journal', 'cache', 'static'))
        with sqlite3.connect('file:' + str(DATA / 'webui.db') + '?mode=ro', uri=True) as source, sqlite3.connect(root / 'data/webui.db') as target:
            source.backup(target)
            if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('Snapshot integrity check failed')
        shutil.copytree('/opt/private-chat', root / 'project', ignore=shutil.ignore_patterns('__pycache__', '.git', '.env'))
        configuration = root / 'configuration'
        configuration.mkdir()
        for item in ['/etc/private-chat/app.env', '/etc/nginx/sites-available/chat.banas.dev.conf', '/etc/nginx/snippets/private-chat-proxy.conf', '/etc/nginx/snippets/private-chat-cloudflare.conf', '/etc/systemd/system/private-chat.service', '/etc/systemd/system/private-chat-gpu-status.service', '/etc/systemd/system/private-chat-backup.service', '/etc/systemd/system/private-chat-backup.timer']:
            p = Path(item)
            if p.exists():
                shutil.copy2(p, configuration / p.name)
        (root / 'hashes.json').write_text(json.dumps(hashes(root), indent=2))
        plain = staging / 'backup.tar.gz'
        with tarfile.open(plain, 'w:gz') as tar:
            for path in root.iterdir():
                tar.add(path, arcname=path.name)
        stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
        encrypted = STORE / ('daily-' + stamp + '.tar.gz.gpg')
        subprocess.run(GPG + ['--batch', '--quiet', '--pinentry-mode', 'loopback', '--passphrase-file', str(KEY), '--cipher-algo', 'AES256', '--output', str(encrypted), '--symmetric', str(plain)], check=True)
        counts = verify(encrypted)
        report = {'archive': str(encrypted), 'sha256': file_hash(encrypted), 'verified': True, 'restored_counts': counts, 'at': time.time()}
        Path('/etc/private-chat/last-backup.json').write_text(json.dumps(report, indent=2))
        for old in sorted(STORE.glob('daily-????????T??????Z.tar.gz.gpg'))[:-14]:
            old.unlink()
        print(json.dumps(report))


if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == 'verify':
        print(json.dumps({'verified': True, 'restored_counts': verify(Path(sys.argv[2]))}))
    else:
        backup()
