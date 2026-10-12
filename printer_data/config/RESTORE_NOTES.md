# Vyper restored installation — 12 October 2026

Raspberry Pi 5 4 GB, MainsailOS 3.0.0 / Debian 13 Trixie.

Retained extras: KlipperScreen (X11, HDMI 1024x600), Crowsnest v5 (USB webcam,
1920x1080 at requested 30 fps), Moonraker Timelapse, KAMP adaptive meshing and
line purge, Klipper-Backup automatic file watching and boot backups. KIAUH
is available at `/home/pi/kiauh` as an installation/management tool.

Sonar remains disabled. Manual Git backup macros/buttons and their G-Code
Shell Command extension were removed. Old development tools from the damaged
installation (VS Code Server, .NET, Copilot and Codex directories) were not restored.

`printer.cfg` retains the current calibration SAVE_CONFIG block, including
BLTouch Z offset 2.301, heater PID values, and saved mesh. Both idle timeout
and Mainsail's pause timeout override are 57600 seconds (16 hours). PAUSE
does not disable heaters or motors; the default idle action does so at expiry.

Compatibility edits: TEST_SPEED uses MINIMUM_CRUISE_RATIO; LOAD_FILAMENT and
UNLOAD_FILAMENT convert temperature parameters to floats; Crowsnest uses
rollover_on_start instead of delete_log (log path is supplied by its service);
Moonraker uses the current Crowsnest v5 dependency configuration. The local
timelapse.cfg copy replaces the deprecated gcode_position.e accessor with
gcode_position[printer.gcode_move.axis_map.E]. After updating timelapse,
review this local compatibility copy against its upstream macro file.

Preheat presets in both interfaces come from the textured PEI first-layer
settings in the OrcaSlicer Vyper profiles:

| Preset | Nozzle | Bed |
| --- | --- | --- |
| PLA (PolyTerra PLA) | 210 C | 55 C |
| PETG (PETG Basic) | 245 C | 80 C |

KlipperScreen stores these in KlipperScreen.conf. Mainsail stores them in the
Moonraker database under mainsail / presets.presets. The accompanying
preheat-presets-mainsail.json contains that database API payload for recovery:
POST it to http://127.0.0.1:7125/server/database/item from the Pi. This stores
presets only; it does not start heating.

Host changes that need reapplying on another fresh OS:

- SSH: /etc/ssh/sshd_config.d/00-vyper-key-only.conf contains PermitRootLogin no,
  PubkeyAuthentication yes, PasswordAuthentication no,
  KbdInteractiveAuthentication no, AuthenticationMethods publickey.
  Install your public key and verify a new SSH connection before enforcing this.
- Xorg: /etc/X11/xorg.conf.d/20-vyper-vc4.conf selects the Pi 5 display GPU:

```
Section "ServerFlags"
    Option "AutoAddGPU" "false"
EndSection
Section "Device"
    Identifier "VyperHDMI"
    Driver "modesetting"
    Option "kmsdev" "/dev/dri/by-path/platform-axi:gpu-card"
EndSection
Section "Screen"
    Identifier "VyperScreen"
    Device "VyperHDMI"
EndSection
```

Git backup credentials remain privately in /home/pi/klipper-backup/.env and
are deliberately outside this public config backup. The enabled services are
klipper-backup-filewatch and klipper-backup-on-boot.

The active configs loaded in current Klipper and Moonraker. Moonraker has no
component warnings; KlipperScreen loaded both presets and its saved UI options.
The printer MCU, webcam stream, and USB touch input still need live verification
after reconnecting the printer peripherals. No printer MCU firmware was flashed.
