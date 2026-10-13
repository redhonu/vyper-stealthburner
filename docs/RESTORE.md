# Restore the Vyper installation

Use a fresh Raspberry Pi 5-compatible MainsailOS image, a trusted config snapshot
and the newest private bundle. These steps describe a rebuild; they do not flash
the printer controller or issue movement/heating commands.

## 1. Choose the sources

Download `main` for current printer configs and `restore-tools` for this kit into
separate folders. Record the config commit you use. A private bundle's `config/`
can instead be newer and more complete; compare timestamps and saved calibration
before choosing. Never substitute the original damaged-card calibration for a
newer saved Z offset. Old adaptive meshes are not universal full-bed meshes.

Verify/stage the private archive with `scripts/bundle.py` as described in
[BACKUP.md](BACKUP.md). The extracted manifest records hashes, file modes and
original symlink targets. Keep the staging directory private.

## 2. Rebuild the host and install components

The working baseline was MainsailOS 3.0.0 arm64 / Debian 13 Trixie on Pi 5 4 GB.
Use Raspberry Pi Imager to set hostname `vyper`, user `pi`, timezone
Europe/Zurich, Wi-Fi and the existing user's public SSH key. Restore the public
authorized_keys file if needed; keep private keys on the PC. Verify a new key
SSH session before applying the supplied key-only SSH policy.

Install core Klipper/Moonraker/Mainsail plus KlipperScreen, Crowsnest v5,
Moonraker Timelapse, KAMP and Klipper-Backup using their supported installers
and KIAUH. The saved source commits in `restore-baseline.json` (or a newer
private bundle's `inventory/source-commits.json`) identify the known working
revisions. Reinstall dependencies using the upstream installers; do not copy old
Python virtual environments across OS releases. Review
[Klipper configuration changes](https://www.klipper3d.org/Config_Changes.html)
before deliberately upgrading past the baseline.

Restore the installed Spoolman Docker service separately using
[SPOOLMAN.md](SPOOLMAN.md), including its private database. Its deployment files
are supplied in `system/`; Moonraker keeps a local URL independent of any later
Traefik proxy. Do not restore inventory from public Git, which does not contain it.

KAMP supplies purge/Smart Park, while meshing uses native Klipper adaptive
support. Keep KAMP/Adaptive_Meshing.cfg disabled in KAMP_Settings.cfg to avoid
replacing the native BED_MESH_CALIBRATE command. PRINT_START uses ADAPTIVE=1
and SAMPLES=1; global probe samples remain 2 for Z tilt. Restore the checked
BLTouch touch/no-stow settings and 5 mm mesh travel clearance together.

KAMP can be installed in `/home/pi/KAMP`; make `printer_data/config/KAMP` available using
the upstream link or the bundle's materialized copy. `mainsail.cfg` is supplied
by mainsail-config and often symlinked; it is absent from the public config
backup because the backup job skips symlinks. Ensure it exists before starting
Klipper. The restored `timelapse.cfg` has a compatibility change to the E-axis
accessor and should be retained/reviewed against upstream. The Moonraker plugin
must also be installed, normally with its component linked into
`moonraker/moonraker/components/timelapse.py` by the upstream installer.

KlipperScreen uses X11 at 1024x600. Install `system/20-vyper-vc4.conf` as
`/etc/X11/xorg.conf.d/20-vyper-vc4.conf` if the Pi 5 screen setup needs the same
GPU selection. Verify `/dev/dri/by-path/platform-axi:gpu-card` exists first.
Preserve an existing host file before replacing it. Install the SSH policy as
`/etc/ssh/sshd_config.d/00-vyper-key-only.conf`, run `sudo sshd -t`, reload SSH,
and verify another key login with the original session still open.

## 3. Restore configuration and calibration

On the idle fresh host, stop Klipper before replacing config. Save its fresh
config directory separately, then copy the chosen configuration into
`/home/pi/printer_data/config`. If replacing a symlinked include with a
materialized copy, remove only that destination link first, rather than writing
through it into the upstream checkout. Apply correct pi ownership. Review local
source patches from the private bundle; do not replay them blindly onto a new
upstream revision. Restore only required custom extras.

Retain the full SAVE_CONFIG block in printer.cfg. Check:

- MCU serial device identity: current config uses `/dev/ttyUSB0`; prefer a stable
  `/dev/serial/by-id/` path when available and confirmed to identify this board.
- Printer height 240 mm; Z velocity 10 mm/s and Z acceleration 100 mm/s².
- Downward probing 3 mm/s, Z homing 5 mm/s, independent dual Z and measured
  300 mm screw spacing. Saved geometry must match the physical machine.
- **Both idle and pause timeout overrides remain 57600 seconds (16 hours).**
  Keep the bed and motors energized during a runout pause.
- Motion/extrusion limits, PID, pressure advance and saved calibration reflect
  the selected snapshot, rather than installer defaults.

The original build configuration describes STM32F103 / 32 KiB bootloader /
serial at 250000 baud. This is a recovery reference, not proof of every Vyper
board's firmware settings. The working recovery did not flash MCU firmware.
Only rebuild/flash if a confirmed protocol mismatch requires it and the board
variant has been checked.

## 4. Restore Moonraker state

With a compatible Moonraker running and no print, copy the private bundle's
`database/moonraker.db` into `/home/pi/printer_data/backup/database/` with a
unique filename and pi ownership. Create a backup of the fresh database first.
Restore through the supported API, then restart Moonraker:

```bash
curl --fail-with-body -H 'Content-Type: application/json' \
  -d '{"filename":"vyper-restore.db"}' \
  http://127.0.0.1:7125/server/database/restore
sudo systemctl restart moonraker
```

Use that filename only if you copied the database there under that name.
Database restoration includes authorization/integration state: use your own
trusted backup. Do not copy a live database or old LMDB files over a current
SQLite database. The original pre-reinstall archive contains older-format state;
use selective API restoration for that historical backup.

If there is no current database backup, `preheat-presets-mainsail.json` in the
latest config snapshot can restore the preheat preset API payload. Likewise
`timelapse-print-priority.json` records the previously saved timelapse setup;
apply its settings through the installed timelapse API/UI, not the database
item endpoint. Recreate webcam/Mainsail preferences from the inventory. This
fallback loses state not represented in those exports; it is not a full restore.

## 5. Restore backups, networking and check interfaces

Restore `home/klipper-backup/.env` privately, mode 0600, and review the repo/branch
and backupPaths. The automatic backup uses **main**, not restore-tools. Reinstall
and enable `klipper-backup-filewatch` and `klipper-backup-on-boot` with the
upstream installer. Check successful pushing after a harmless config edit.
Preserve key-only SSH and no root login. Use the new OS's network setup or
carefully restore the private NetworkManager profiles with root ownership and
mode 0600; do not restore the old fstab partition identifiers onto a freshly
flashed card. Recreate local systemd units through their supported installers;
system files in the archive are references, not a directory to overwrite wholesale.

Check loaded Klipper sections and MCU connection, Moonraker components/warnings,
KlipperScreen/touch input, webcam snapshot/stream and automatic backup. Verify
PLA 220/55°C and PETG 245/80°C preset values without activating the heaters.
Timelapse must capture in place with park/retract disabled, no capture dwell,
and render after print completion. Sonar and the G-Code Shell Command extension
remain unnecessary for this installation.

Restore Orca profiles via Orca Cloud on the same account. Confirm the Vyper
machine, installed nozzle and material/process selection; no slicer account
credentials or presets are stored in this repository.

Only after software checks, with the user beside the printer and bed clear,
perform physical homing/alignment/probing and a small first-layer validation.
Recalibrate if the plate, nozzle, probe or geometry has changed. Do not treat
an old saved offset as validated for changed hardware.
