#!/usr/bin/env python3
"""Publish photos from uploads/inbox to the website (docs/).

For every new photo this:
  * removes ALL hidden metadata - GPS location, camera serial, etc. -
    by re-saving only the pixels
  * makes a web-size copy (docs/photos/) and a thumbnail (docs/photos/thumbs/)
  * reads the real capture time from the photo (falls back to file name / date)
  * adds it to docs/gallery.json
  * deletes the original from uploads/inbox, because this repository is public
    and the original still contains the GPS data

Camera name: the sub-folder it was uploaded into (uploads/inbox/North_Ridge/...),
             otherwise looked up from the camera ID at the start of Reveal's
             file names in docs/cameras.json (new IDs are added automatically).
Animal type: put "buck" or "doe" in the file or folder name, otherwise "Other".
             You can always change it later in docs/gallery.json.

Run with --keep to leave originals in the inbox (only do that on your own PC).
"""
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / 'uploads' / 'inbox'
DEST = ROOT / 'docs' / 'photos'
THUMBS = DEST / 'thumbs'
INDEX = ROOT / 'docs' / 'gallery.json'
CAMERAS = ROOT / 'docs' / 'cameras.json'   # camera ID -> name you choose
EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
FULL_MAX, THUMB_MAX = 1800, 700          # pixels on the long edge
DATE_TAGS = (36867, 36868, 306)          # DateTimeOriginal, Digitized, DateTime


def sidecar(path):
    """Optional <photo>.json written by fetch_reveal.py with camera/time."""
    meta = path.with_name(path.name + '.json')
    try:
        return json.loads(meta.read_text()) if meta.exists() else {}
    except ValueError:
        return {}


def taken(img, path, meta):
    # Reveal file names hold the camera's local time - the most reliable source.
    m = re.search(r'(?<!\d)(\d\d)(\d\d)(20\d\d)(\d\d)(\d\d)(\d\d)(?!\d)', path.name)
    if m:
        mo, d, y, h, mi, _ = map(int, m.groups())
        try:
            return datetime(y, mo, d, h, mi).strftime('%Y-%m-%d %H:%M')
        except ValueError:
            pass
    exif = img.getexif()
    sub = exif.get_ifd(0x8769)  # date tags usually live in the Exif sub-block
    for tag in DATE_TAGS:
        val = sub.get(tag) or exif.get(tag)
        if val:
            try:
                return datetime.strptime(str(val).strip()[:19], '%Y:%m:%d %H:%M:%S').strftime('%Y-%m-%d %H:%M')
            except ValueError:
                pass
    if meta.get('taken'):
        return str(meta['taken']).replace('T', ' ')[:16]
    m = re.search(r'(20\d\d)[-_]?(\d\d)[-_]?(\d\d)[T_ -]?(\d\d)[-_:]?(\d\d)', path.name)
    if m:
        try:
            return datetime(*map(int, m.groups())).strftime('%Y-%m-%d %H:%M')
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')


def load_cameras():
    """docs/cameras.json maps a Reveal camera ID to a friendly name."""
    try:
        return json.loads(CAMERAS.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def clean_name(name):
    """'FEEDER - SPRINGVILLE' -> 'Feeder' (drop the location part Reveal adds)."""
    return name.split(' - ')[0].replace('_', ' ').strip().title() if name else None


def camera_from_id(name, suggested=None):
    """Reveal file names start with the camera's 15-digit ID."""
    m = re.match(r'(\d{15})-', name)
    if not m:
        return suggested or 'Trail Camera'
    cid = m.group(1)
    names = load_cameras()
    if cid not in names:  # remember new cameras so you can rename them later
        names[cid] = suggested or f'Camera {cid[-4:]}'
        CAMERAS.write_text(json.dumps(names, indent=2) + '\n', encoding='utf-8')
    return names[cid]


def animal(path, meta):
    if meta.get('type') in ('Buck', 'Doe', 'Other'):
        return meta['type']
    text = str(path.relative_to(INBOX)).lower()
    if 'buck' in text:
        return 'Buck'
    if 'doe' in text:
        return 'Doe'
    return 'Other'


def save_clean(img, dest, max_px, quality):
    copy = img.copy()
    copy.thumbnail((max_px, max_px), Image.LANCZOS)
    clean = Image.new('RGB', copy.size)   # brand-new image = no metadata carried over
    clean.paste(copy)
    clean.save(dest, 'JPEG', quality=quality, optimize=True, progressive=True)


def main():
    keep = '--keep' in sys.argv
    DEST.mkdir(parents=True, exist_ok=True)
    THUMBS.mkdir(parents=True, exist_ok=True)
    doc = json.loads(INDEX.read_text(encoding='utf-8')) if INDEX.exists() else {'photos': []}
    entries = doc.get('photos', [])
    known = {p['id'] for p in entries}
    count = 0
    for path in sorted(INBOX.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in EXTS:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:20]
        meta = sidecar(path)
        if digest not in known:
            try:
                with Image.open(path) as raw:
                    raw.load()
                    when = taken(raw, path, meta)
                    img = ImageOps.exif_transpose(raw).convert('RGB')
            except Exception as exc:
                print(f'Skipped {path.name}: {exc}')
                continue
            # Folder name wins; then the name saved for this camera ID in
            # docs/cameras.json; Reveal's own label is only used for new cameras.
            camera = ((path.parent.name.replace('_', ' ').title() if path.parent != INBOX else None)
                      or camera_from_id(path.name, clean_name(meta.get('camera'))))
            out_name = f'{when[:10]}-{digest}.jpg'
            save_clean(img, DEST / out_name, FULL_MAX, 84)
            save_clean(img, THUMBS / out_name, THUMB_MAX, 75)
            kind = animal(path, meta)
            entries.append({
                'id': digest,
                'title': f'{kind if kind != "Other" else "Visitor"} at {camera}',
                'type': kind,
                'camera': camera,
                'captured_at': when,
                'url': f'photos/{out_name}',
                'thumb': f'photos/thumbs/{out_name}',
            })
            known.add(digest)
            count += 1
            print(f'Added {out_name}  ({camera}, {when})')
        if not keep:
            path.unlink()
            path.with_name(path.name + '.json').unlink(missing_ok=True)
    entries.sort(key=lambda p: p.get('captured_at', ''), reverse=True)
    INDEX.write_text(json.dumps({'photos': entries}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Imported {count} new photos. Gallery now contains {len(entries)}.')


if __name__ == '__main__':
    main()
