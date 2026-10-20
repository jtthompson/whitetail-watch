#!/usr/bin/env python3
"""Publish files from uploads/inbox to docs/photos. No REVEAL account access."""
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / 'uploads' / 'inbox'
DEST = ROOT / 'docs' / 'photos'
INDEX = ROOT / 'docs' / 'gallery.json'
EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    doc = json.loads(INDEX.read_text(encoding='utf-8'))
    entries = doc.get('photos', [])
    known = {p['id'] for p in entries}
    count = 0
    for path in sorted(INBOX.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in EXTS:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:20]
        if digest in known:
            continue
        camera = path.parent.name if path.parent != INBOX else 'Trail Camera'
        name = re.sub(r'[^a-zA-Z0-9_-]+', '-', path.stem).strip('-')[:45] or 'wildlife'
        out_name = f'{digest}-{name}{path.suffix.lower()}'
        shutil.copy2(path, DEST / out_name)
        dt = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        entries.append({'id': digest, 'title': name.replace('-', ' ').title(), 'type': 'Other', 'camera': camera.replace('_', ' '), 'captured_at': dt, 'url': f'photos/{out_name}'})
        known.add(digest)
        count += 1
    entries.sort(key=lambda p:p.get('captured_at',''), reverse=True)
    INDEX.write_text(json.dumps({'photos': entries}, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f'Imported {count} new photos. Gallery now contains {len(entries)}. Dates come from file modification time and may need correcting.')

if __name__ == '__main__':
    main()
