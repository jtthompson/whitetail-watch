# Whitetail Watch — trail camera gallery

Live site: https://jtthompson.github.io/whitetail-watch/

## What it does
- Public photo gallery. The newest photo fills the big picture at the top, there is a filter button for each camera plus animal filters, and the photo viewer supports swiping and arrow keys.
- Six **illustrative demo entries**, shown only until real photos are imported.
- `scripts/import_photos.py` turns images in `uploads/inbox` into web-size photos and thumbnails in `docs/photos`, **removes GPS and all other hidden metadata**, reads the real capture time from the photo, updates `docs/gallery.json`, then deletes the original from the inbox.
- `.github/workflows/import.yml` runs the importer automatically when photos are uploaded, every 3 hours, or when you press **Run workflow** on the Actions tab.
- Optional Reveal downloader (`scripts/fetch_reveal.py`). It runs only if you add `REVEAL_EMAIL` and `REVEAL_PASSWORD` as repository secrets (Settings → Secrets and variables → Actions). It signs in to the Reveal website with a headless browser and drops new photos into the inbox. This is best-effort: Reveal has no official API, so it may need adjusting if Reveal changes its site, and automated sign-in may not be permitted by Tactacam's terms.

## Add pictures
1. On GitHub, open the `uploads/inbox` folder and choose **Add file → Upload files**.
2. To label the camera, put the photos in a folder on your computer named for it (e.g. `North_Ridge`) and drag the whole folder into the upload box — GitHub keeps the folder name. Loose photos are labeled "Trail Camera".
3. Put `buck` or `doe` in a file or folder name to tag it; everything else is tagged "Other wildlife". You can change titles and types later in `docs/gallery.json`.
4. Click **Commit changes**. About a minute later the photo is on the site.

## Privacy
- Everything in this repository and on the site is public.
- Published copies have GPS removed, but a photo you upload yourself stays in the repository's history with its original data. For full privacy, turn off location in the Reveal app before saving photos, or use the Reveal downloader (its originals are never committed).
- Camera names can reveal hunting spots — pick names that don't.
- Never put your Reveal password in a file; only in a repository secret.

## Settings this repo relies on
- **Settings → Pages:** deploy from branch `main`, folder `/docs`.
- **Settings → Actions → General → Workflow permissions:** **Read and write permissions**, so the automation can save published photos.

## Repository layout
- `docs/` — the website (`index.html`, `styles.css`, `extra.css`, `app.js`, `gallery.json`, `photos/`)
- `uploads/inbox/` — drop zone for new photos
- `scripts/import_photos.py` — publisher (resize, strip GPS, update gallery)
- `scripts/fetch_reveal.py` — optional Reveal downloader
- `.github/workflows/import.yml` — the automation
