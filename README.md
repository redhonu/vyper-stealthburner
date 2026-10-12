# Vyper Stealthburner configuration backup

Working printer: Anycubic Vyper with the CRYD Stealthburner/Clockwork 2 kit,
standard-flow Revo Micro, BLTouch and independent dual Z. Host: Raspberry Pi 5
4 GB, MainsailOS 3.0.0 arm64.

**Current automatically backed-up configs are on this `main` branch.**
Preserve the full printer.cfg SAVE_CONFIG block when restoring. Its newest
saved calibration is preferable to historical recovery copies.

**[Full restore kit and instructions](https://github.com/redhonu/vyper-stealthburner/tree/restore-tools)**
cover component installation, the Pi 5 screen fix, SSH key-only policy, firmware
build options and a private Moonraker/system backup utility. The kit is on a
separate branch because the automatic backup script removes extra files except
README.md. Keep the automatic backup branch set to `main`.

Git stores configuration, not the complete Pi database or credentials. A full
rebuild also needs a separately stored private backup for Moonraker settings,
network configuration and Git backup credentials. OrcaSlicer presets are managed
in Orca Cloud; no slicer account credentials are stored here.

Installed extras: KlipperScreen, Crowsnest v5, KAMP, Moonraker Timelapse and
automatic Klipper-Backup. Sonar is disabled; manual Git macros and G-Code Shell
Command are removed. Both pause/idle timeouts are 16 hours (57600 seconds).
Timelapse captures in place without parking or retraction and renders after the
print. Follow the restore kit for current recovery instructions; older notes in
config snapshots are historical.

Automatic backups use [Klipper-Backup](https://github.com/Staubgeborener/klipper-backup).
If a manual maintenance backup is needed, its existing command is
`cd ~/klipper-backup && ./script.sh`.

Hardware references:

- [CRYD Stealthburner documentation](https://book.cryd.de/books/hersteller-marken-modelle/page/stealthburner)
- [CRYD Vyper Stealthburner files](https://github.com/cryd-s/Vyper_extended/tree/main/extended_board/stealthburner%20toolhead)
