#!/usr/bin/env python3
"""Zip older photos into a GitHub release, then take them off the website.

OFF by default. Settings live in archive.json at the top of the repository:

    {
      "enabled": false,        <- set to true to turn archiving on
      "older_than_days": 120,  <- photos older than this get archived
      "min_photos": 50         <- don't bother until at least this many qualify
    }

How it runs (from .github/workflows/import.yml):
  1. `archive_photos.py prepare`  - if enabled and enough photos qualify, writes
     build/archive.zip (full-size photos + a list of what's inside) and
     build/archive-notes.md. Nothing is removed yet.
  2. The workflow uploads build/archive.zip as a GitHub release
     ("Releases" on the repository page) where you can download it any time.
  3. `archive_photos.py finalize` - only after the upload worked: removes those
     photos from docs/gallery.json, deletes their files, and records their ids
     in uploads/archived.json so they are never downloaded again.

Favorites are never archived. The zipped copies are the published web copies
(GPS already removed). Releases of a public repository are public, like the site.
"""
import json
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'archive.json'
INDEX = ROOT / 'docs' / 'gallery.json'
EDITS = ROOT / 'docs' / 'edits.json'
ARCHIVED = ROOT / 'uploads' / 'archived.json'
BUILD = ROOT / 'build'
ZIP = BUILD / 'archive.zip'
PLAN = BUILD / 'archive-plan.json'
NOTES = BUILD / 'archive-notes.md'


def load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def prepare():
    cfg = {'enabled': False, 'older_than_days': 120, 'min_photos': 50, **load(CONFIG, {})}
    if not cfg['enabled']:
        print('Archiving is turned off (archive.json "enabled": false).')
        return
    cutoff = (datetime.now() - timedelta(days=int(cfg['older_than_days']))).strftime('%Y-%m-%d')
    favorites = set(load(EDITS, {}).get('favorites', []))
    photos = load(INDEX, {'photos': []})['photos']
    old = [p for p in photos if p.get('captured_at', '9999') < cutoff and p['id'] not in favorites]
    if len(old) < int(cfg['min_photos']):
        print(f'{len(old)} photo(s) older than {cutoff}; waiting for {cfg["min_photos"]} before archiving.')
        return
    BUILD.mkdir(exist_ok=True)
    with zipfile.ZipFile(ZIP, 'w', zipfile.ZIP_STORED) as z:  # JPEGs don't compress further
        for p in old:
            f = ROOT / 'docs' / p['url']
            if f.exists():
                z.write(f, f"{p['camera']}/{p['captured_at'][:10]}/{f.name}")
        z.writestr('photos.json', json.dumps(old, indent=1))
    first, last = min(p['captured_at'] for p in old), max(p['captured_at'] for p in old)
    PLAN.write_text(json.dumps([p['id'] for p in old]))
    NOTES.write_text(f'{len(old)} trail-camera photos taken {first[:10]} to {last[:10]}, '
                     f'removed from the website to save space.\n')
    print(f'Prepared {ZIP.name}: {len(old)} photos ({ZIP.stat().st_size / 1e6:.1f} MB), {first} to {last}.')


def finalize():
    if not PLAN.exists():
        return
    ids = set(json.loads(PLAN.read_text()))
    doc = load(INDEX, {'photos': []})
    keep = []
    for p in doc['photos']:
        if p['id'] in ids:
            for key in ('url', 'thumb'):
                f = ROOT / 'docs' / p.get(key, '')
                if p.get(key) and f.exists():
                    f.unlink()
        else:
            keep.append(p)
    doc['photos'] = keep
    INDEX.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    done = sorted(set(load(ARCHIVED, [])) | ids)
    ARCHIVED.write_text(json.dumps(done, indent=0) + '\n')
    print(f'Archived {len(ids)} photos; {len(keep)} remain on the site.')


if __name__ == '__main__':
    {'prepare': prepare, 'finalize': finalize}[sys.argv[1] if len(sys.argv) > 1 else 'prepare']()
