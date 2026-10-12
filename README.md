# Vyper restore kit

Restore material for an Anycubic Vyper with the CRYD Stealthburner/Clockwork 2 kit,
Revo Micro, independent dual Z and BLTouch, hosted on a Raspberry Pi 5 4 GB.

The `main` branch is the automatic **printer-config backup**. This `restore-tools`
branch holds the instructions and backup utilities. Klipper-Backup clears extra
files from its working tree on each run, preserving only README.md and
.gitmodules; keeping restore tools here prevents them being deleted by that job.
Always take the newest `main` configuration, rather than this branch's older
`printer_data` snapshot.

- [Restore instructions](docs/RESTORE.md)
- [Backup coverage and usage](docs/BACKUP.md)
- [Installed components](restore-baseline.json)
- [Pi 5 screen configuration](system/20-vyper-vc4.conf)
- [Key-only SSH configuration](system/00-vyper-key-only.conf)
- [Recovered MCU build configuration](system/klipper-mcu.config)

OrcaSlicer profiles are managed in Orca Cloud, as requested; they are not
duplicated here.

This public repository cannot contain a full private backup: the Moonraker
database, Wi-Fi credentials and Git backup token must be stored separately.
The supplied backup utility captures those on an idle Pi. It has been tested
offline, but has not been run on the current printer.
