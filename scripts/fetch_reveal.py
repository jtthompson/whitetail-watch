#!/usr/bin/env python3
"""Download new photos from your Tactacam Reveal web account.

Reveal has no public API, so this signs in to the Reveal website
(account.revealcellcam.com) with a headless browser (Playwright), lets the
home feed load, and collects photo URLs from the photo list the site itself
loads from its data service (api.reveal.ishareit.net/v1/photos/v2). Photos are
stored on Amazon S3 under Reveal's own file names, which carry the camera ID
and capture time, and are saved under those names to  uploads/inbox/  with a
small .json sidecar holding the camera name the site shows.

Environment variables (set as GitHub Actions secrets / variables):
  REVEAL_EMAIL, REVEAL_PASSWORD   required - your Reveal sign-in
  REVEAL_LOGIN_URL                default https://account.revealcellcam.com/login
  REVEAL_GALLERY_URL              optional - page to open after sign-in
  REVEAL_MAX_SCROLLS              default 15 - how far to scroll the feed
  REVEAL_MAX_NEW                  default 60 - most photos to download per run
  REVEAL_DEBUG=1                  save debug/screenshot.png (may show your email)

Because Reveal can change its website at any time, this is best-effort. If it
finds nothing, check debug/api_calls.txt and adjust the URLs/selectors below.
"""
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "uploads" / "inbox"
DEBUG = ROOT / "debug"
SEEN_FILE = ROOT / "uploads" / "reveal_seen.json"

LOGIN_URL = os.environ.get("REVEAL_LOGIN_URL") or "https://account.revealcellcam.com/login"
if urlsplit(LOGIN_URL).path in ("", "/"):  # the home page only has a "Log in" button
    LOGIN_URL = LOGIN_URL.rstrip("/") + "/login"
GALLERY_URL = os.environ.get("REVEAL_GALLERY_URL", "")
MAX_SCROLLS = int(os.environ.get("REVEAL_MAX_SCROLLS") or "15")
MAX_NEW = int(os.environ.get("REVEAL_MAX_NEW") or "60")
PHOTO_API = "/photos"            # only read the photo-list responses
PHOTO_HOST = "amazonaws.com"     # where Reveal stores the actual pictures

IMG_RE = re.compile(r"^https?://[^\s\"']+\.(?:jpe?g|png|webp)(?:\?[^\s\"']*)?$", re.I)
URL_KEYS_BEST = ("original", "hd", "full", "large", "highres", "download")
URL_KEYS_WORST = ("thumb", "small", "preview", "icon", "avatar", "logo")
CAMERA_KEYS = ("cameraName", "camera_name", "deviceName", "device_name", "cameraTitle")
DATE_KEYS = ("photoDate", "takenAt", "taken_at", "dateTaken", "captureDate",
             "capturedAt", "photo_date", "createdAt", "created_at", "timestamp", "date")


def key_of(url: str) -> str:
    """Stable id for a photo URL (signed URLs change their query string)."""
    s = urlsplit(url)
    return s.netloc + s.path


def rank(key: str) -> int:
    k = key.lower()
    if any(w in k for w in URL_KEYS_WORST):
        return 0
    if any(w in k for w in URL_KEYS_BEST):
        return 2
    return 1


def walk(node, found: dict, ctx: dict):
    """Recursively pull photo URLs (+ camera/date) out of any JSON blob."""
    if isinstance(node, list):
        for item in node:
            walk(item, found, ctx)
        return
    if not isinstance(node, dict):
        return
    ctx = dict(ctx)
    for k in CAMERA_KEYS:
        if isinstance(node.get(k), str):
            ctx["camera"] = node[k]
    cam = node.get("camera")
    if isinstance(cam, dict) and isinstance(cam.get("name"), str):
        ctx["camera"] = cam["name"]
    for k in DATE_KEYS:
        if isinstance(node.get(k), (str, int, float)):
            ctx["taken"] = node[k]
            break
    urls = [(rank(k), v) for k, v in node.items() if isinstance(v, str) and IMG_RE.match(v)]
    if urls:
        best = max(urls)[1] if max(urls)[0] > 0 else None
        if best:
            found.setdefault(key_of(best), {"url": best, **ctx})
    for v in node.values():
        if isinstance(v, (dict, list)):
            walk(v, found, ctx)


def normalise_date(val):
    if isinstance(val, (int, float)):  # epoch seconds or ms
        from datetime import datetime, timezone
        sec = val / 1000 if val > 1e11 else val
        return datetime.fromtimestamp(sec, timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")
    return str(val)[:19] if val else None


def sign_in(page, email, password):
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)
    page.wait_for_timeout(2_000)
    email_box = page.locator('input[placeholder*="EMAIL" i], input[type=email], '
                             'input[name*=email i], input[name*=user i]').first
    email_box.fill(email, timeout=20_000)
    pw_box = page.locator("input[type=password]").first
    if not pw_box.is_visible():  # two-step forms: email first, then password
        page.keyboard.press("Enter")
        page.wait_for_timeout(2_000)
    pw_box.fill(password, timeout=20_000)
    page.keyboard.press("Enter")
    try:
        page.wait_for_url(lambda u: "/login" not in u, timeout=20_000)
    except PWTimeout:
        submit = page.locator("button[type=submit]").first
        if submit.count():
            submit.click()
        try:
            page.wait_for_url(lambda u: "/login" not in u, timeout=30_000)
        except PWTimeout:
            pass
    try:
        page.wait_for_load_state("networkidle", timeout=45_000)
    except PWTimeout:
        pass
    if page.locator("input[type=password]").first.is_visible():
        raise SystemExit("Sign-in seems to have failed (password box still showing). "
                         "Check REVEAL_EMAIL / REVEAL_PASSWORD, or the site may require a code/captcha.")


def main() -> int:
    email, password = os.environ.get("REVEAL_EMAIL"), os.environ.get("REVEAL_PASSWORD")
    if not email or not password:
        print("REVEAL_EMAIL / REVEAL_PASSWORD not set - skipping Reveal download.")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    DEBUG.mkdir(exist_ok=True)
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    seen = set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()
    found: dict = {}
    api_log = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1400, "height": 1000})
        page = context.new_page()

        def on_response(resp):
            ctype = resp.headers.get("content-type", "")
            if "json" in ctype and PHOTO_API in urlsplit(resp.url).path:
                api_log.append(f"{resp.status} {key_of(resp.url)}")
                try:
                    walk(resp.json(), found, {})
                except Exception:
                    pass

        page.on("response", on_response)
        sign_in(page, email, password)
        if GALLERY_URL:
            page.goto(GALLERY_URL, wait_until="networkidle", timeout=60_000)

        for _ in range(MAX_SCROLLS):  # infinite-scroll galleries load more as you scroll
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1_500)

        # Backup: large images actually shown on the page.
        for src in page.eval_on_selector_all(
            "img", "els => els.filter(e => e.naturalWidth >= 600).map(e => e.currentSrc || e.src)"
        ):
            if src.startswith("http") and PHOTO_HOST in urlsplit(src).netloc:
                found.setdefault(key_of(src), {"url": src})

        if os.environ.get("REVEAL_DEBUG") == "1":
            page.screenshot(path=str(DEBUG / "screenshot.png"), full_page=True)
        (DEBUG / "api_calls.txt").write_text("\n".join(api_log) + "\n")

        new = [(k, v) for k, v in found.items() if k not in seen][:MAX_NEW]
        print(f"Found {len(found)} photo URL(s), downloading {len(new)} new.")
        for i, (k, info) in enumerate(new):
            try:
                r = context.request.get(info["url"], timeout=60_000)
                if not r.ok or "image" not in r.headers.get("content-type", "image"):
                    print(f"  skip {k}: HTTP {r.status}")
                    continue
                # Keep Reveal's own file name: it holds the camera ID and capture time.
                name = re.sub(r"[^\w.() -]", "_", Path(urlsplit(info["url"]).path).name) or f"reveal_{i:04d}.jpg"
                dest = OUT / name
                dest.write_bytes(r.body())
                meta = {"camera": info.get("camera"), "taken": normalise_date(info.get("taken")),
                        "source": "reveal"}
                dest.with_name(dest.name + ".json").write_text(json.dumps(meta))
                seen.add(k)
            except Exception as exc:
                print(f"  failed {k}: {exc}")
        browser.close()

    SEEN_FILE.write_text(json.dumps(sorted(seen), indent=0))
    if not found:
        print("No photos found. Look at debug/api_calls.txt (workflow artifact) to see what "
              "the site loaded, and set REVEAL_GALLERY_URL to the page that shows your photos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
