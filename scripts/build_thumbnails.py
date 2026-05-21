"""Generate 800px-wide JPEG thumbnails of every survey/POI photo for gallery use.
Originals stay in photos/; thumbnails go to photos/thumbs/ with the same filename.
Re-run safely — only missing/older thumbnails are regenerated.
"""
from pathlib import Path
from PIL import Image, ImageOps
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).parent          # scripts/
SITE = ROOT.parent / "site"           # deployable web platform
SRC = SITE / "photos"
DST = SITE / "photos" / "thumbs"
DST.mkdir(exist_ok=True)

TARGET_WIDTH = 800
JPEG_QUALITY = 78

src_files = sorted([p for p in SRC.iterdir()
                    if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg', '.png')])
print(f"Source photos: {len(src_files)}")

generated = 0
skipped = 0
errors = 0
total_saved = 0

for src in src_files:
    dst = DST / src.name
    # Skip if up-to-date
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        skipped += 1
        continue
    try:
        with Image.open(src) as im:
            # Honour EXIF orientation
            im = ImageOps.exif_transpose(im)
            if im.mode in ('P', 'RGBA'):
                im = im.convert('RGB')
            w, h = im.size
            if w > TARGET_WIDTH:
                new_h = int(h * TARGET_WIDTH / w)
                im = im.resize((TARGET_WIDTH, new_h), Image.LANCZOS)
            im.save(dst, 'JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
        saved = src.stat().st_size - dst.stat().st_size
        total_saved += saved
        generated += 1
    except Exception as e:
        print(f"  ERROR {src.name}: {e}")
        errors += 1

src_mb = sum(p.stat().st_size for p in src_files) / (1024 * 1024)
dst_mb = sum(p.stat().st_size for p in DST.iterdir() if p.is_file()) / (1024 * 1024)
print(f"\nGenerated: {generated}  Skipped (already current): {skipped}  Errors: {errors}")
print(f"Originals total:  {src_mb:.1f} MB")
print(f"Thumbnails total: {dst_mb:.1f} MB  ({100*(1 - dst_mb/src_mb):.0f}% smaller)")
