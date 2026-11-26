"""Generate the two web sizes of every survey/POI photo.

    site/photos/thumbs/  400 px wide, ~50 KB  — gallery grids (loaded with every section)
    site/photos/large/   800 px wide, ~250 KB — the lightbox (loaded only when a photo is opened)

Originals are looked for in site/photos/ first, then in the survey source folder
(--src, $RAJKULO_SRC, or D:\\Rajkulo All Documents). EXIF orientation is applied and
all metadata is dropped. Re-run safely — only missing or outdated files are rebuilt;
pass --force to rebuild everything.

    python scripts/build_thumbnails.py --src "D:\\Rajkulo All Documents"
"""
import argparse, io, os, sys
from pathlib import Path
from PIL import Image, ImageOps

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).resolve().parent      # scripts/
SITE = ROOT.parent / "site"
PHOTOS = SITE / "photos"
SIZES = {                                   # folder: (max width, JPEG quality)
    "thumbs": (400, 70),
    "large": (800, 78),
}


def source_dirs(src):
    dirs = [PHOTOS]
    if src:
        dirs += [src / "Rajkulo All Documents" / "RajkuloSurvey" / "rajkulo_survey",
                 src / "Mergin Maps Data" / "CANAL1",
                 src / "Rajkulo All Documents" / "RajkuloSurvey" / "rajkulo_survey" / "images"]
    return [d for d in dirs if d.is_dir()]


def find_original(name, dirs):
    for d in dirs:
        p = d / name
        if p.is_file():
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", help='Folder "Rajkulo All Documents" holding the original photos')
    ap.add_argument("--force", action="store_true", help="rebuild every file")
    args = ap.parse_args()

    src = Path(args.src) if args.src else (
        Path(os.environ["RAJKULO_SRC"]) if os.environ.get("RAJKULO_SRC") else Path(r"D:\Rajkulo All Documents"))
    dirs = source_dirs(src if src.exists() else None)

    # The set of photos the site uses = whatever is already published in thumbs/ or large/,
    # plus any originals placed in site/photos/.
    names = set()
    for folder in SIZES:
        d = PHOTOS / folder
        if d.is_dir():
            names |= {p.name for p in d.iterdir() if p.suffix.lower() in ('.jpg', '.jpeg', '.png')}
    names |= {p.name for p in PHOTOS.iterdir() if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg', '.png')}
    print(f"Photos: {len(names)}   original folders: {[str(d) for d in dirs]}")

    for folder in SIZES:
        (PHOTOS / folder).mkdir(parents=True, exist_ok=True)

    made, kept, fallback, missing = 0, 0, [], []
    for name in sorted(names):
        orig = find_original(name, dirs)
        for folder, (width, quality) in SIZES.items():
            dst = PHOTOS / folder / name
            if dst.exists() and not args.force and (orig is None or dst.stat().st_mtime >= orig.stat().st_mtime):
                kept += 1
                continue
            base = orig
            if base is None:
                # No original available: derive from the largest web copy we have.
                base = next((PHOTOS / f / name for f in ("large", "thumbs") if (PHOTOS / f / name).exists()
                             and PHOTOS / f / name != dst), None)
                if base is None:
                    missing.append(name)
                    continue
                fallback.append(name)
            with Image.open(base) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                if im.width > width:
                    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)   # no EXIF kept
            dst.write_bytes(buf.getvalue())
            made += 1

    for folder in SIZES:
        files = [p for p in (PHOTOS / folder).iterdir() if p.is_file()]
        mb = sum(p.stat().st_size for p in files) / 2**20
        print(f"  {folder:7s} {len(files):4d} files  {mb:6.1f} MB  (avg {1024 * mb / max(len(files), 1):.0f} KB)")
    print(f"Written: {made}   up to date: {kept}   built from a web copy (no original): {len(set(fallback))}"
          f"   missing entirely: {len(set(missing))}")


if __name__ == "__main__":
    main()
