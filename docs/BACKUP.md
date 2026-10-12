# Backup coverage

| Material | Storage | Recovery role |
| --- | --- | --- |
| Current printer configs and saved calibration | Repository `main` | Newest automatically pushed configuration |
| Restore utilities, component inventory, host setup | Repository `restore-tools` | Rebuild the software environment |
| Moonraker SQLite database | Private idle-time bundle | Mainsail settings, webcam, history and integration state |
| Config symlink targets, firmware build options, local source patches | Private bundle | Include files absent from Git and local compatibility changes |
| NetworkManager profiles, SSH policy/public authorized keys, backup .env | Private bundle | Network, login policy and automatic Git backup |
| OrcaSlicer presets | Orca Cloud | Restore using the same account, then verify selected Vyper presets |
| Original SD image and verified extraction | Separate local archive | Recover the damaged installation; historical, not current |

The public Git backup alone is not a complete Pi backup. Do not publish private
bundles, a raw SD image, an Orca account configuration or cloud-init credentials.
Copy private bundles off the SD card to access-controlled/encrypted storage.
Keep the user's existing SSH private key separately on their PC; this tool does
not capture private SSH keys or reproduce root login credentials.

## Capture a private bundle after a print

Download/clone the restore-tools branch into a separate folder, not
`~/config_backup` or the active `~/printer_data/config` directory. On the Pi:

```bash
cd ~/vyper-restore-tools
sudo python3 scripts/backup_pi.py --home /home/pi --output /home/pi/vyper-backups
```

Root is used to read the existing network and SSH system files. The resulting
archive is mode 0600 and owned by the owner of /home/pi. It includes the Git
backup token and may include database/API credentials. The tool refuses a
printing or paused job, makes no heater/movement/service commands, and uses
Moonraker's supported database backup API instead of copying its live database.
It follows configuration symlinks, materializing their contents, and detects
configuration changes during capture. It does not stop services or clear jobs.
The database API leaves an additional database backup on the Pi.

If localhost Moonraker requires an API key, supply `MOONRAKER_API_KEY` privately
to the process; do not put it into shell history or Git. Read any printed
`Backup gap` lines. A missing component or unreadable system file needs resolving
before treating the archive as complete. In particular, the MCU .config may be
absent on a fresh host; this kit also supplies the recovered build configuration.

Verify on either the Pi or a PC:

```bash
python3 scripts/bundle.py verify /path/to/vyper-private-TIMESTAMP.zip
python3 scripts/bundle.py stage /path/to/vyper-private-TIMESTAMP.zip --destination /path/to/new-empty-stage
```

Staging only writes to the requested new directory; it never applies settings to
the printer. Checksums detect corruption, not malicious alteration: use backups
from trusted storage. Include the adjacent archive SHA256 file when copying.

The archive is a configuration/database rebuild bundle, not a sector image.
Print G-Code, videos, timelapse frames, arbitrary home-directory data, private SSH
keys, and the printer MCU firmware binary are outside its scope. Export those
separately if wanted. `source-patches/` and `custom-klipper/` capture tracked local
source modifications and untracked Klipper extras; virtual environments are
reinstalled. Capture while no one edits configs or changes UI settings.

## Existing October 2026 recovery

The preserved 12 October raw card image and verified selective archive contain
the pre-reinstall private state. They do not include later calibration changes.
The latest available `main` commit at kit creation was
`dfe0ab052e4aaa6bc43db54f798bf566ba2c5045`, with saved probe z_offset 2.308.
The user subsequently reported successful first-layer printing. No live
comparison or new private bundle was made during that print. Obtain a new
private bundle when idle to complete the current backup.

Official API reference: [Moonraker database backup](https://moonraker.readthedocs.io/en/latest/external_api/database/#backup-database).
