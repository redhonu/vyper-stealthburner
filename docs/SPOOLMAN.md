# Installed Spoolman service

Spoolman 0.27.0 runs on the Vyper Pi in Docker, with SQLite data persisted in
`/home/pi/spoolman/data`. Deployment: `/home/pi/spoolman/compose.yml`, reproduced
in [spoolman-compose.yml](../system/spoolman-compose.yml). Docker starts on boot;
the container uses `restart: unless-stopped`, a one-CPU limit and rotating logs.

The service is bound to **127.0.0.1:7912** on the Pi. Moonraker's `[spoolman]`
section connects to `http://127.0.0.1:7912` with the default five-second sync
interval. Mainsail and KlipperScreen use their native spool selection panels.
Select the physically loaded spool there before printing; Orca G-Code remains
authoritative for print temperatures and filament calibration.

Native inventory and extrusion tracking are installed. Spool selection does
not itself heat or move the printer. No custom guided load/unload helper was
installed with this service.

## Access and reverse proxy

From a PC with the existing SSH key/config, keep this tunnel running:

```bash
ssh -N -L 127.0.0.1:7912:127.0.0.1:7912 vyper
```

Open `http://localhost:7912`. The tunnel is temporary; the Spoolman service and
Moonraker connection do not depend on the PC remaining online.

For Traefik on the same host, its upstream needs access to the Pi's localhost
listener; localhost inside a separate container refers to that container.
For Traefik on another host, establish a private route/tunnel or an explicitly
restricted listener first. The current listener is intentionally unavailable
directly from the LAN. No Traefik router or public hostname has been configured.
Use a dedicated hostname at the root path unless deliberately configuring
`SPOOLMAN_BASE_PATH`. Preserve WebSocket forwarding. Moonraker can keep its
local URL after proxying. If exposing outside the trusted network, authenticate
at the proxy: Spoolman has no built-in authentication.

## Backup and restore

Spoolman makes its own consistent SQLite backups at midnight under `data/backups`.
Those are on the same SD card and must also be copied off the Pi.

The private [backup utility](../scripts/backup_pi.py) includes
`spoolman/compose.yml`, an optional private `.env`, `spoolman/data/spoolman.db`
and version information. It requests a supported online database backup. If
Spoolman returns a reused snapshot, it takes a fresh SQLite online backup from
the local bind mount instead, avoiding an older inventory snapshot. It never
blindly copies the live database. The full Pi bundle still refuses a printing or
paused job. The initial Spoolman-only online snapshot was independently verified
and copied off the Pi while a print continued.

On a fresh host, install Debian's `docker.io`, `docker-cli` and `docker-compose`
packages. Create `/home/pi/spoolman/data` owned by UID/GID 1000, mode 0700.
Copy the archived Compose file to `/home/pi/spoolman/compose.yml` and the archived
database to `/home/pi/spoolman/data/spoolman.db` while the container is stopped.
Restore any archived `.env` privately. Do not overwrite an existing inventory;
preserve it first. Enable Docker and start the restored deployment:

```bash
sudo systemctl enable --now docker
sudo docker compose -f /home/pi/spoolman/compose.yml up -d
```

Restore Moonraker's section from the newest `moonraker.conf`; do not add it twice.
Restart Moonraker only while idle. Verify `/api/v1/health` on Spoolman returns
healthy, `/server/spoolman/status` on Moonraker reports connected, and the
inventory and selected physical spool are correct. A small observed decrease in
remaining weight verified usage tracking after this installation.

Inventory, spool IDs, remaining weights and credentials belong in the private
database, not this public repository. Component installation and restore files
are public; Orca profiles remain in Orca Cloud.

References: [Spoolman installation](https://github.com/Donkie/Spoolman/wiki/Installation),
[backup/restore](https://github.com/Donkie/Spoolman/wiki/Backup-and-Restore),
[Moonraker integration](https://moonraker.readthedocs.io/en/stable/configuration/#spoolman),
[SQLite online backup](https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup).
