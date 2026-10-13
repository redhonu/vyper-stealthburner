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

Installed extras: KlipperScreen, Crowsnest v5, KAMP, Moonraker Timelapse, Spoolman and
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

Meshing now uses Klipper built-in adaptive support: one touch per print-mesh
point, 15×15 full-area density, 5 mm margin/travel height, BLTouch touch mode
with no stowing between points. KAMP remains for line purge and Smart Park.
Z tilt keeps two samples. Downward probing remains 3 mm/s.

## Completed calibration and checks

These are dated results, not values to overwrite a newer saved configuration.
Printer calibration lives in `printer.cfg`; filament calibration lives in Orca
Cloud. Update this record when a calibration is completed, with material/nozzle
and the resulting value. Plans and unfinished tests are excluded.

| Date | Calibration or check | Result and scope |
| --- | --- | --- |
| 2026-10-13 | Saved probe offset | 2.308 mm; user corrected the offset and reported successful first-layer printing on the Glacier Pro plate. Preserve the newest SAVE_CONFIG block. |
| 2026-10-13 | Z travel check | Supervised Z20-Z120 cycles at 10 mm/s; user observed smooth movement on both independent sides. Height limit remains 240 mm. |
| 2026-10-13 | Bambu PLA Matte flow | User selected -0.05 in the YOLO flow test; saved flow ratio 0.93, standard-flow Revo 0.4 mm. Stored in Orca Cloud. |
| 2026-10-13 | BLTouch touch/no-stow repeatability | Ten samples: range 0.0225 mm, standard deviation 0.006344 mm. Immediate previous mode range was also 0.0225 mm. |
| 2026-10-13 | Native adaptive mesh checks | One touch per point; representative 4x4 mesh 35.35 s versus 121.56 s previously. Nine-point full-area clearance check completed at 5 mm travel height. First-layer confirmation after this mode change remains separate from these checks. |
| 2026-10-13 | Independent Z alignment check | Completed at 0.010 mm residual against 0.020 mm tolerance after four retries. |

The latest pressure-advance calibration result has not yet been recorded.
The existing Klipper value 0.042 is a prior baseline, not a calibrated Bambu
PLA Matte result; slicer filament G-Code can override it.

The tested meshing configs were automatically backed up at
`5031299a97e887945e0a8a75f62bf9ee2361295f`. A private 49-file host/config/database
bundle was also captured and verified separately on 13 October 2026.

## Spoolman

Spoolman 0.27.0 is installed in Docker with persistent SQLite data, automatic
startup and Moonraker's native filament tracking. Its listener is local to the
Pi at `127.0.0.1:7912`; access through an SSH tunnel until the reverse proxy is
configured. Native Mainsail/KlipperScreen spool selection is available. Inventory
and spool weights are private database state; no IDs are hard-coded in G-Code.

[Spoolman deployment, access and restore](https://github.com/redhonu/vyper-stealthburner/blob/restore-tools/docs/SPOOLMAN.md)
includes the actual deployment files and backup coverage. The private backup
utility now captures the local Spoolman database consistently; the initial
Spoolman-only snapshot was verified and copied off the Pi. Capture another full
private Pi bundle when idle to combine the latest host and integration state.
