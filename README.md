# Whitetail Watch — GitHub Pages demo + photo publisher

## What works
- Responsive public photo gallery, with camera and animal filters and photo lightbox.
- Six **illustrative demo entries**, shown only when there are no imported photos.
- Python importer that converts images in `uploads/inbox` into public files in `docs/photos` and `docs/gallery.json`.
- GitHub Actions automation to run importer on incoming image commits, every 6 hours, or manually.

## What is not included
- **No automatic connection to your Tactacam REVEAL account.** No verified official public photo-download API was identified. Nothing here logs into REVEAL or scrapes its private API.
- Automatic image recognition: images are initially tagged `Other`, and timestamps use file modification time in UTC, not camera EXIF timestamps. Change titles/types/dates in `docs/gallery.json` as desired.

## Publish to GitHub Pages
1. Create a repository, e.g. `whitetail-watch`.
2. Unzip and upload the **contents** of this folder to the repository root on its `main` branch, preserving `.github/workflows/import.yml`.
3. Go to **Settings → Pages → Build and deployment → Deploy from a branch**; choose branch `main` and folder `/docs`; Save.
4. Visit `https://YOUR-USERNAME.github.io/whitetail-watch/` once Pages deploys.
5. In **Settings → Actions → General**, check workflow permissions allow **Read and write permissions** for `GITHUB_TOKEN` if importer cannot push updates.

## Add actual pictures
Option A, directly using GitHub: add JPEG/PNG/WebP pictures to `uploads/inbox/` (optionally into subfolders named for cameras, e.g. `uploads/inbox/North_Ridge/`). Commit to `main` and allow the workflow to publish them. The folder `uploads/inbox` is staging; original uploaded pictures remain stored there unless you remove them manually.

Option B, on your computer: copy exported photos to `uploads/inbox`, run `python scripts/import_photos.py`, then commit and push changes.

The gallery uses example art until there are real images in `docs/gallery.json`.

**Caution:** Any pictures added to this public repository or published through GitHub Pages are public. Remove GPS/location metadata before upload if important. Camera names can reveal hunting locations. Do not upload REVEAL account credentials, tokens or passwords.

## Future REVEAL acquisition integration
Implement a separate, approved acquisition tool that places exported images in `uploads/inbox`. This importer will publish new files automatically; deduplication is based on SHA-256. GitHub Actions scheduled runs cannot retrieve REVEAL photos without a separate supported download mechanism and valid authorization.

## Repository layout
- `docs/`: GitHub Pages static site and published media
- `uploads/inbox/`: staging location for manually exported or externally delivered media
- `scripts/import_photos.py`: gallery publisher
- `.github/workflows/import.yml`: GitHub Action
