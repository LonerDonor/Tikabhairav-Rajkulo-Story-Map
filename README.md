# Tikabhairab Rajkulo — Living Heritage Map

Interactive web platform for the **13 km Tikabhairab Rajkulo** — a Licchavi-era hill-fed canal in Lalitpur, Nepal. Built from field GPS survey (May 2022) + AutoCAD alignment drawings.

The site is a single, static, dependency-free page that runs from any web server (including GitHub Pages) or directly from `file://`.

---

## Folder layout

The project is sorted into five top-level folders:

```
Story map Tikabhairav/
├── README.md          ← this file
├── site/              ← the deployable web platform (self-contained)
├── data/              ← GIS / build sources and intermediates
├── cad/               ← AutoCAD drawings + extracted sheet geometry
├── research/          ← report, drafts, figures, dev notes, archive
└── scripts/           ← Python build & utility scripts
```

### `site/` — the web platform (deploy this folder)

| File | Purpose |
|------|---------|
| `index.html` | Markup, accessible semantics, Open Graph tags |
| `style.css` | All visual styling (field-notebook aesthetic + mobile bottom-sheet) |
| `app.js` | Filter state, map rendering, search, tour mode, deep-linking, lightbox |
| `data.js` | `CANAL_SECTIONS`, `CANAL_POIS`, `CANAL_HISTORIC` constants — **regenerated, do not edit by hand** |
| `photos/` | Original full-resolution survey photos (~1.4 GB, 244 files) |
| `photos/thumbs/` | 800 px JPEG thumbnails (~58 MB) — used in galleries; lightbox loads originals |

These five items reference each other by relative path, so the folder is self-contained — serve `site/` (or open `site/index.html`) and everything works.

### `data/` — GIS sources & build intermediates (not loaded by the live site)

| File | Purpose |
|------|---------|
| `canal_sections.gpkg` | Cleaned gpkg with `canal_sections` + `canal_base` layers for downstream tools (QGIS, etc.) |
| `canal_sections.json` | The section data, for non-JS consumers |
| `canal_sections.js` | Build intermediate: the `CANAL_SECTIONS` block, copied into `site/data.js` |
| `canal_historic.json` | The 96 historic-branch polylines |
| `canal_base_alignment.json` | The `टि-१` main alignment as a MultiLineString (kept for reference) |
| `pdf_only_sections.csv` | The 12 sections defined in CAD but still needing GPS digitisation |

### `cad/` — drawings & extracted geometry

| File | Purpose |
|------|---------|
| `*.dwg` | The source AutoCAD drawings |
| `pdf_extract/` | Vector geometry pulled from the 17 CAD sheets + PNG previews |

### `research/` — written outputs

| File | Purpose |
|------|---------|
| `Tikabhairab_Rajkulo_Report_v2.docx` / `.md` | The v2 report (built `.docx` + its markdown source) |
| `Tikabhairab_Rajkulo_v2_DRAFT.md` | Earlier draft |
| `figures/` | The report's data-driven figures + maps (PNG, 300 DPI) |
| `dev-notes/` | Development notes (filter fix, station-point naming) |
| `archive/` | `Tikabhairab_Rajkulo_Platform.html.backup` — the old monolithic platform page |

### `scripts/` — Python tooling

| Script | Purpose |
|--------|---------|
| `build_platform_data.py` | Regenerates `data/canal_sections.*`, `data/canal_base_alignment.json` and copies referenced photos into `site/photos/` from the source Excel + gpkg |
| `build_thumbnails.py` | Regenerates `site/photos/thumbs/` from `site/photos/` |
| `build_figures.py` | Regenerates the report figures into `research/figures/` |
| `diagnose_gaps.py` | Writes `research/figures/gap_analysis.png` |
| `build_docx.py` | Builds `research/Tikabhairab_Rajkulo_Report_v2.docx` from the markdown + figures |
| `upload_photos.py` | Standalone photo uploader (run from a folder of photos) |

The scripts resolve all project paths relative to their own location (`scripts/`), so run them from anywhere — e.g. `python scripts/build_thumbnails.py`. They read the canonical source Excel/gpkg from absolute paths under `C:\Users\olenepal\Downloads\Rajkulo All Documents\…`.

---

## Regenerating data

After editing the source Excel (`CANAL_Survey.xlsx`) or the source gpkg:

```bash
python scripts/build_platform_data.py
```

This writes into `data/`:
- `canal_sections.json` (inspection format)
- `canal_sections.js` (the `CANAL_SECTIONS` block)
- `canal_base_alignment.json` (the `टि-१` main alignment as MultiLineString)

…and copies any newly referenced photos into `site/photos/`.

To update the live site, copy the `const CANAL_SECTIONS = …;` block from `data/canal_sections.js` into `site/data.js`. (We can fold this into the build script if it becomes routine.)

To regenerate photo thumbnails after adding/replacing photos in `site/photos/`:

```bash
python scripts/build_thumbnails.py
```

Re-runnable safely — only missing/older thumbnails get rebuilt.

To rebuild the report figures and `.docx`:

```bash
python scripts/build_figures.py
python scripts/build_docx.py
```

---

## Hosting on GitHub Pages

1. Push this folder to a GitHub repository.
2. Repository **Settings → Pages → Source** → select your branch (`main`) + folder.
3. Point the published path at the **`site/`** subfolder, e.g. `…/Story map Tikabhairav/site/`.

The space in the folder name URL-encodes as `%20`. For a cleaner URL, rename the parent folder to something like `rajkulo/` and update GitHub Pages source accordingly.

### LFS recommendation

The `site/photos/` folder is **~1.4 GB** of original-resolution JPEGs. GitHub's soft repo limit is 1 GB; the hard limit is 100 GB. Options:

- **Easiest**: commit `site/photos/thumbs/` (~58 MB) and skip `site/photos/` originals (add to `.gitignore`). The platform silently falls back to the placeholder ("Photo unavailable") for full-res lightbox views. Galleries still work.
- **Better**: enable Git LFS for `site/photos/*.jpg`. Free quota is 1 GB/month bandwidth; small heritage sites fit comfortably.
- **Best**: host the originals on Cloudinary (free tier 25 GB) and set `PHOTO_FULL_BASE` in `site/app.js` to the Cloudinary URL prefix. Keep thumbs in-repo for instant gallery rendering.

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `/` | Focus search box |
| `[`  `←` | Previous section (when one is selected) |
| `]`  `→` | Next section |
| `Esc` | Close lightbox / exit tour |

---

## URL deep-linking

| Hash | Effect |
|------|--------|
| `#section=37` | Open section detail panel and fly to section #37 |
| `#poi=12` | Open POI detail panel and fly to POI #12 |
| `#tour=1` | Auto-start the tour on load |

---

## Tour mode

Click **Take the tour →** on the splash screen, or visit any URL with `#tour=1`. The tour is a scripted 10-stop sequence covering: intake, perennial reach, hydraulic finding, sewage inflow, encroachment zone, underground sections, settlement crossings, the historic network, outlet, and how to explore further. Stops are defined in `TOUR_STOPS` in `site/app.js`.

---

## Accessibility

- Keyboard-navigable filters, tabs, and search results
- ARIA roles on tablist, dialogs, listboxes, toolbar
- Focus rings on every focusable element
- High-contrast text alternatives next to colour-coded chips
- 44 px minimum touch target on interactive elements
- Lightbox traps focus and closes on Esc

---

## Known limitations

- **12 sections** (PDF# 52, 96–99, 101–107) are defined in the CAD drawings but were not GPS-walked in May 2022. They appear in the data with no geometry; the detail panel shows a notice.
- **1 photo** referenced by the data (`IMG_20220508_150014.jpg`) was not found in any source folder.
- The full-resolution `site/photos/` directory is ~1.4 GB. See "LFS recommendation" above before pushing to GitHub.

---

## Credits

Survey, photographs, and analysis: Hrishav Raj Joshi, Lalitpur (May 2022).
Hydraulic analysis: Lacey regime equations applied to the 13 km alignment.
Source canal name "Tilmak" attested in Licchavi-era inscriptions.
