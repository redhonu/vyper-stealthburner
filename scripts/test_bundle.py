"""Offline checks: archive integrity, traversal protection and print-state refusal."""
from datetime import datetime, timezone
from contextlib import closing, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import sys

# Also support the isolated Windows embedded Python used for offline recovery.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import backup_pi
import bundle


def fixture(path, files, manifest_files=None):
    manifest = {'format': 'vyper-private-backup-v1',
                'created_utc': datetime.now(timezone.utc).isoformat(),
                'files': {name: {'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                          for name, data in (manifest_files or files).items()}}
    with zipfile.ZipFile(path, 'w') as z:
        for name, data in files.items():
            z.writestr(name, data)
        z.writestr('manifest.json', json.dumps(manifest))


class BackupTests(unittest.TestCase):
    def test_spoolman_backup_preserves_data_and_deployment(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            folder = home / 'spoolman'
            (folder / 'data/backups').mkdir(parents=True)
            (folder / 'compose.yml').write_bytes(b'services: {}\n')
            db = folder / 'data/backups/spoolman.db'
            with closing(sqlite3.connect(db)) as conn:
                conn.execute('CREATE TABLE spool (remaining REAL)')
                conn.execute('INSERT INTO spool VALUES (980)')
                conn.commit()
            files = {}
            def add(path, name, required=False):
                files[name] = Path(path).read_bytes()
            def api(route, method='GET'):
                if route == '/info':
                    return {'db_type': 'sqlite', 'data_dir': '/home/app/.local/share/spoolman', 'version': '0.27.0'}
                self.assertEqual(method, 'POST')
                return {'path': '/home/app/.local/share/spoolman/backups/spoolman.db'}
            with patch.object(backup_pi, 'spoolman_request', side_effect=api):
                backup_pi.capture_spoolman(home, add, files)
            self.assertEqual(files['spoolman/compose.yml'], b'services: {}\n')
            staged = home / 'restored.db'
            staged.write_bytes(files['spoolman/data/spoolman.db'])
            with closing(sqlite3.connect(staged)) as conn:
                self.assertEqual(conn.execute('SELECT remaining FROM spool').fetchone()[0], 980)

    def test_spoolman_rejects_backup_path_outside_mounted_directory(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            (home / 'spoolman').mkdir()
            (home / 'spoolman/compose.yml').write_text('services: {}\n')
            for path in ('/etc/passwd', '/home/app/.local/share/spoolman/backups/../spoolman.db'):
                def api(route, method='GET'):
                    if route == '/info':
                        return {'db_type': 'sqlite', 'data_dir': '/home/app/.local/share/spoolman'}
                    return {'path': path}
                with self.subTest(path=path), patch.object(backup_pi, 'spoolman_request', side_effect=api):
                    with self.assertRaisesRegex(RuntimeError, 'Unexpected Spoolman backup path'):
                        backup_pi.capture_spoolman(home, lambda *a, **kw: None, {})

    def test_spoolman_cached_backup_captures_newer_live_data(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            folder = home / 'spoolman'
            (folder / 'data/backups').mkdir(parents=True)
            (folder / 'compose.yml').write_text('services: {}\n')
            for path, value in ((folder / 'data/backups/spoolman.db', 1000),
                                (folder / 'data/spoolman.db', 980)):
                with closing(sqlite3.connect(path)) as conn:
                    conn.execute('CREATE TABLE spool (remaining REAL)')
                    conn.execute('INSERT INTO spool VALUES (?)', (value,))
                    conn.commit()
            def api(route, method='GET'):
                if route == '/info':
                    return {'db_type': 'sqlite', 'data_dir': '/home/app/.local/share/spoolman'}
                return {'path': '/home/app/.local/share/spoolman/backups/spoolman.db', 'created': False}
            files = {}
            def add(path, name, required=False):
                files[name] = Path(path).read_bytes()
            with patch.object(backup_pi, 'spoolman_request', side_effect=api):
                backup_pi.capture_spoolman(home, add, files)
            restored = home / 'restored.db'
            restored.write_bytes(files['spoolman/data/spoolman.db'])
            with closing(sqlite3.connect(restored)) as conn:
                self.assertEqual(conn.execute('SELECT remaining FROM spool').fetchone()[0], 980)

    def test_capture_private_bundle_with_consistent_database(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root) / 'home'
            system = Path(root) / 'system'
            config = home / 'printer_data/config'
            config.mkdir(parents=True)
            (config / 'printer.cfg').write_text('[printer]\nkinematics: cartesian\n')
            for name in ('klipper/.config', 'klipper-backup/.env', '.ssh/authorized_keys'):
                target = home / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('offline fixture only')
            db = home / 'printer_data/backup/database/fixture.db'
            db.parent.mkdir(parents=True)
            with closing(sqlite3.connect(db)) as conn:
                conn.execute('CREATE TABLE fixture (value TEXT)')
                conn.execute("INSERT INTO fixture VALUES ('retained')")
                conn.commit()
            def fake_api(base, route, body=None):
                if route == '/server/database/backup':
                    return {'backup_path': str(db)}
                return {'status': {'print_stats': {'state': 'standby'},
                                   'pause_resume': {'is_paused': False}}}
            output = Path(root) / 'out'
            with patch.object(backup_pi, 'api', side_effect=fake_api), \
                    patch.object(backup_pi, 'command', return_value='fixture-package\t1\n'), \
                    patch.object(os, 'geteuid', return_value=1000, create=True), redirect_stdout(io.StringIO()):
                archive = backup_pi.create_backup(home, output, 'unused', system_root=system)
            manifest = bundle.verify(archive)
            self.assertTrue(manifest['private'])
            self.assertIn('home/klipper-backup/.env', manifest['files'])
            staged = Path(root) / 'stage'
            bundle.stage(archive, staged)
            with closing(sqlite3.connect(staged / 'database/moonraker.db')) as conn:
                self.assertEqual(conn.execute('SELECT value FROM fixture').fetchone()[0], 'retained')
            self.assertTrue(archive.with_suffix('.zip.sha256').is_file())

    def test_verify_and_stage_exact_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'backup.zip'
            files = {'config/printer.cfg': b'nozzle_diameter: 0.4\n',
                     'database/moonraker.db': bytes(range(256))}
            fixture(path, files)
            self.assertEqual(len(bundle.verify(path)['files']), 2)
            out = Path(root) / 'staged'
            bundle.stage(path, out)
            for name, data in files.items():
                self.assertEqual((out / name).read_bytes(), data)
            with self.assertRaises(FileExistsError):
                bundle.stage(path, out)

    def test_corruption_and_undeclared_files_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'backup.zip'
            fixture(path, {'config/printer.cfg': b'changed'}, {'config/printer.cfg': b'original'})
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                bundle.verify(path)
            fixture(path, {'config/printer.cfg': b'x', 'extra': b'bad'}, {'config/printer.cfg': b'x'})
            with self.assertRaisesRegex(ValueError, 'differ'):
                bundle.verify(path)

    def test_unsafe_paths_rejected_before_staging(self):
        for name in ('../outside', '/absolute', 'C:/outside', 'a\\outside', 'a/../outside', 'a//b'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                path = Path(root) / 'bad.zip'
                fixture(path, {name: b'x'})
                out = Path(root) / 'staged'
                with self.assertRaises(ValueError):
                    bundle.stage(path, out)
                self.assertFalse(out.exists())

    def test_case_collision_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'backup.zip'
            fixture(path, {'A': b'x', 'a': b'y'})
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                bundle.verify(path)

    def test_printing_and_paused_refused(self):
        for state, paused in (('printing', False), ('paused', True), ('standby', True)):
            with self.subTest(state=state, paused=paused):
                result = {'status': {'print_stats': {'state': state},
                                     'pause_resume': {'is_paused': paused}}}
                with patch.object(backup_pi, 'api', return_value=result):
                    with self.assertRaisesRegex(RuntimeError, 'printing or paused'):
                        backup_pi.require_idle('unused')
        with patch.object(backup_pi, 'api', return_value={'status': {
                'print_stats': {'state': 'standby'}, 'pause_resume': {'is_paused': False}}}):
            backup_pi.require_idle('unused')


if __name__ == '__main__':
    unittest.main()
