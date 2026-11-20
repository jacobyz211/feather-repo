# Moe x FastSign — Feather repo

A single Feather/AltStore-format source that combines:

- **997 apps** from [fastsign.dev/repo.lite.json](https://fastsign.dev/repo.lite.json) (Alan's Gigantic Repo)
- **238 apps** from [moe.mohkg1017.pro](https://moe.mohkg1017.pro) (Moe's App Hub)

Fully merged: **1234 apps**, deduplicated on bundle ID + download URL, sorted by name.
Moe entries show `Moe` as the developer; duplicates of fastsign names get a `(Moe)` suffix.

## Files

| File | Purpose |
| --- | --- |
| `repo.json` | The source itself — this is the file you host. |
| `build_repo.py` | Rebuilds `repo.json` from both upstreams. |

## Using it in Feather

Feather needs the repo to live at a public HTTPS URL — a local file won't work.

1. Upload `repo.json` somewhere public, e.g. GitHub Pages, Cloudflare Pages, Netlify, or any static host.
   Make sure it is served as `application/json` at the exact URL you'll enter.
2. Open Feather → **Sources** (or Settings → Sources) → **Add Source**.
3. Paste your URL, e.g. `https://yourdomain.com/repo.json`.

Quick GitHub Pages route: create a repo, drop `repo.json` in it, enable Pages on the
`main` branch root, then use `https://<user>.github.io/<repo>/repo.json`.

Optionally, before hosting, add a `"sourceURL"` field equal to the final public URL
(AltStore convention — Feather doesn't require it) and change `website`/`iconURL` to
your own if you want the header to point at your page.

## Refreshing

Upstreams change often. Rerun:

```bash
python build_repo.py
```

It re-downloads the fastsign JSON, scrapes all of Moe's catalog pages, and rewrites
`repo.json`. Requires only the Python standard library.

## Notes on the data

- Moe's site does **not** publish a repo JSON, so its catalog is scraped from the
  listing pages (`data-*` attributes on each app card: version, size, bundle ID,
  icon, download URL, description, date).
- 32 Moe entries have no bundle ID upstream. They get a stable generated one
  (`pro.moe.<app-slug>.<id>`) so all of them stay visible and distinct in Feather.
- Google Drive share links from Moe are rewritten to direct
  `uc?export=download&id=…&confirm=t` URLs so Feather can fetch the IPA instead of
  an HTML page. Availability of those files is still controlled by Moe.
- Versions listed as `Latest` upstream stay as `Latest`.
- Some apps appear in both sources with the same bundle ID (510 duplicates already
  exist inside the fastsign repo). Feather keys entries on bundle ID + download URL,
  so all variants remain listed.

## Validation performed

- JSON parses; every one of the 1234 entries has name, bundle ID, version, date,
  icon URL, download URL, and a `versions` array whose version matches the app's.
- No duplicate bundle ID + download URL pairs, no relative icon URLs, no non-HTTP
  download links.
- Dates are `YYYY-MM-DD`; sizes are integers (bytes).
- Could not run Feather itself (Windows host), so in-app import is untested.
