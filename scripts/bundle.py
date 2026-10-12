#!/usr/bin/env python3
"""Verify or stage a private Vyper backup. Never writes to a live installation."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def safe_name(name):
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or '..' in path.parts or '\\' in name
            or ':' in name or str(path) != name):
        raise ValueError('Unsafe archive path: ' + name)
    return path


def verify(archive):
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(names) != len(set(n.casefold() for n in names)):
            raise ValueError('Duplicate archive paths')
        for name in names:
            safe_name(name)
        manifest = json.loads(z.read('manifest.json'))
        if manifest.get('format') != 'vyper-private-backup-v1':
            raise ValueError('Unsupported backup format')
        expected = manifest['files']
        if set(names) != set(expected) | {'manifest.json'}:
            raise ValueError('Archive contents differ from manifest')
        for name, entry in expected.items():
            safe_name(name)
            data = z.read(name)
            if len(data) != entry['size'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('Checksum mismatch: ' + name)
        return manifest


def stage(archive, destination):
    manifest = verify(archive)
    destination = Path(destination).resolve()
    # A fresh directory prevents symlink redirection and accidental overwrites.
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            target = destination.joinpath(*safe_name(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with target.open('xb') as f:
                f.write(z.read(name))
            target.chmod(0o600)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['verify', 'stage'])
    parser.add_argument('archive', type=Path)
    parser.add_argument('--destination', type=Path)
    args = parser.parse_args()
    if args.action == 'stage':
        if args.destination is None:
            parser.error('stage requires --destination')
        result = stage(args.archive, args.destination)
    else:
        result = verify(args.archive)
    print(json.dumps({'verified_files': len(result['files']),
                      'created_utc': result['created_utc'],
                      'warnings': result.get('warnings', [])}, indent=2))


if __name__ == '__main__':
    main()
