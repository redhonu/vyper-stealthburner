#!/usr/bin/env python3
"""Create a PRIVATE restore bundle on an idle Pi; do not upload it to GitHub."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import urllib.request
import zipfile

from bundle import verify


def api(base, route, body=None):
    headers = {}
    key = os.environ.get('MOONRAKER_API_KEY')
    if key:
        headers['X-Api-Key'] = key
    data = None if body is None else json.dumps(body).encode()
    if data is not None:
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(base.rstrip('/') + route, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        result = json.load(response)
    if 'error' in result:
        raise RuntimeError('Moonraker request failed: ' + route)
    return result['result']


def require_idle(base):
    info = api(base, '/printer/objects/query?print_stats&pause_resume')
    status = info['status']
    if status['print_stats']['state'] in ('printing', 'paused') or status['pause_resume']['is_paused']:
        raise RuntimeError('Backup refused while printing or paused')


def command(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError('Inventory command failed: ' + argv[0])
    return result.stdout


def create_backup(home, output, base, system_root=Path('/')):
    home = Path(home).resolve()
    config = home / 'printer_data/config'
    if not (config / 'printer.cfg').is_file():
        raise RuntimeError('Missing printer.cfg')
    require_idle(base)
    files, metadata, warnings, sources = {}, {}, [], {}

    def add(path, name, required=False):
        path = Path(path)
        try:
            data = path.read_bytes()
            stat = path.stat()
        except (OSError, ValueError):
            if required:
                raise RuntimeError('Cannot back up required file: ' + str(path))
            warnings.append('Missing or unreadable: ' + str(path))
            return
        files[name] = data
        metadata[name] = {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                          'mode': stat.st_mode & 0o777, 'source': str(path),
                          'symlink_target': os.readlink(path) if path.is_symlink() else None}
        sources[name] = path

    def walk(path, prefix, ancestors=()):
        resolved = path.resolve()
        if resolved in ancestors:
            raise RuntimeError('Symlink cycle: ' + str(path))
        for item in sorted(path.iterdir()):
            if item.name in ('.git', '__pycache__', 'node_modules'):
                continue
            name = prefix + '/' + item.name
            if item.is_dir():
                walk(item, name, ancestors + (resolved,))
            else:
                # Read targets as regular files so the bundle is self-contained.
                add(item, name, required=True)

    walk(config, 'config')
    for rel in ('klipper/.config', 'klipper-backup/.env', '.ssh/authorized_keys'):
        add(home / rel, 'home/' + rel, required=rel != 'klipper/.config')
    # Network credentials, API state and backup token are private archive material.
    for rel in ('etc/os-release', 'etc/fstab', 'etc/hostname', 'etc/timezone',
                'etc/ssh/sshd_config', 'etc/X11/xorg.conf.d/20-vyper-vc4.conf'):
        add(system_root / rel, 'system/' + rel)
    for rel in ('etc/ssh/sshd_config.d', 'etc/NetworkManager/system-connections',
                'etc/systemd/system'):
        folder = system_root / rel
        if not folder.is_dir():
            warnings.append('Missing: /' + rel)
            continue
        for item in folder.rglob('*'):
            if not item.is_file():
                continue
            # Archive relevant local unit definitions, not the whole OS service tree.
            if rel.endswith('system') and not any(s in item.name.lower() for s in
                    ('klipper', 'moonraker', 'crowsnest', 'sonar')):
                continue
            add(item, 'system/' + item.relative_to(system_root).as_posix())
    inventory = {}
    for repo in ('klipper', 'moonraker', 'KlipperScreen', 'crowsnest', 'moonraker-timelapse',
                 'mainsail-config', 'klipper-backup', 'kiauh', 'KAMP'):
        folder = home / repo
        if not (folder / '.git').exists():
            warnings.append('Source checkout missing: ' + repo)
            continue
        git = ['git', '-c', 'safe.directory=' + str(folder), '-C', str(folder)]
        inventory[repo] = {'commit': command(git + ['rev-parse', 'HEAD']).strip()}
        patch = command(git + ['diff', '--binary', 'HEAD'])
        if patch:
            files['source-patches/' + repo + '.patch'] = patch.encode()
        if repo == 'klipper':
            for rel in command(git + ['ls-files', '--others', '--exclude-standard',
                                      'klippy/extras']).splitlines():
                if rel.endswith('.py'):
                    add(folder / rel, 'custom-klipper/' + rel, required=True)
    files['inventory/source-commits.json'] = json.dumps(inventory, indent=2).encode()
    files['inventory/packages.tsv'] = command(['dpkg-query', '-W', '-f=${Package}\t${Version}\n']).encode()
    # API uses SQLite's online backup, never copies the live database/WAL directly.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    require_idle(base)
    result = api(base, '/server/database/backup', {'filename': 'vyper-' + stamp + '.db'})
    database = Path(result['backup_path']).resolve()
    allowed = (home / 'printer_data/backup/database').resolve()
    if database.parent != allowed:
        raise RuntimeError('Unexpected Moonraker database backup directory')
    add(database, 'database/moonraker.db', required=True)
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as conn:
        if conn.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
            raise RuntimeError('Database integrity check failed')
    for name, path in sources.items():
        if path.read_bytes() != files[name]:
            raise RuntimeError('Source changed during backup; retry when idle: ' + name)
    require_idle(base)
    for name, data in files.items():
        metadata.setdefault(name, {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                                   'mode': 0o600})
    manifest = {'format': 'vyper-private-backup-v1', 'created_utc': stamp,
                'private': True, 'files': metadata, 'warnings': warnings,
                'scope': 'Configuration, database, relevant host settings and source versions; not an OS image'}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    archive = output / ('vyper-private-' + stamp + '.zip')
    with archive.open('xb') as raw:
        archive.chmod(0o600)
        with zipfile.ZipFile(raw, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                z.writestr(name, data)
            z.writestr('manifest.json', json.dumps(manifest, indent=2))
    verify(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum = archive.with_suffix('.zip.sha256')
    checksum.write_text(digest + '  ' + archive.name + '\n')
    checksum.chmod(0o600)
    if os.geteuid() == 0:
        owner = home.stat()
        for path in (output, archive, checksum):
            os.chown(path, owner.st_uid, owner.st_gid)
    print('Verified PRIVATE backup: ' + str(archive))
    for warning in warnings:
        print('Backup gap: ' + warning)
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    parser.add_argument('--output', type=Path)
    parser.add_argument('--moonraker', default='http://127.0.0.1:7125')
    args = parser.parse_args()
    if os.name != 'posix':
        parser.error('Run backup_pi.py on the Pi; bundle.py works on Windows too')
    create_backup(args.home, args.output or args.home / 'vyper-backups', args.moonraker)
