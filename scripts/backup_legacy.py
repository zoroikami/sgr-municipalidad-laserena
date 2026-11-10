#!/usr/bin/env python3
"""Read-only snapshot of the previous SQLite database, never an automatic import."""
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

root = Path(__file__).resolve().parents[1]
source = root / 'database/sgr_laserena.db'
if not source.exists():
    raise SystemExit('No hay una base SQLite anterior que respaldar.')
folder = root / '.private/backups'
folder.mkdir(parents=True, exist_ok=True, mode=0o700)
target = folder / ('legacy-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite3')
target.touch(mode=0o600, exist_ok=False)
with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as original:
    with sqlite3.connect(target) as snapshot:
        original.backup(snapshot)
print(f'Respaldo privado creado: {target}')
