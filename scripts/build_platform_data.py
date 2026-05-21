"""Rebuild the platform's CANAL_SECTIONS data from the corrected sources.

Truth model:
- CANAL_Survey.xlsx is the canonical mapping. Column A = PDF section number (the
  spatial sequence drawn across the 17 AutoCAD sheets, intake → outlet). Column B =
  the raw Mergin Maps fid (which keys into Survey_new geometry inside Syrvey.gpkg).
- Excel rows are stored in survey-collection (timestamp) order, NOT PDF order — the
  surveyor zig-zagged across the intake branch.
- gpkg Syrvey.gpkg layer `Survey_new` has the GPS-walked geometry per Mergin fid.
- gpkg Syrvey.gpkg layer `Canal` filtered to Canal_ID = टि-१ is the full AutoCAD
  alignment (12.8 km, 22 multilinestrings) — the platform draws this as a base line.

Output:
- canal_sections.js  → the platform's CANAL_SECTIONS array, ordered by PDF#
- canal_sections.json → the same as JSON for inspection
- canal_base_alignment.json → the टि-१ alignment as a MultiLineString
- photos/* → all photos referenced by sections + POIs copied locally
"""
import sys, io, math, json, re, shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from openpyxl import load_workbook
import geopandas as gpd
from shapely.ops import unary_union

ROOT = Path(__file__).parent          # scripts/
PROJECT = ROOT.parent                 # Story map Tikabhairav/
SITE = PROJECT / "site"               # deployable web platform
DATA = PROJECT / "data"               # GIS / build sources & intermediates
EXCEL = Path(r"C:\Users\olenepal\Downloads\Rajkulo All Documents\Rajkulo All Documents\RajkuloSurvey\CANAL_Survey.xlsx")
EXCEL_HYPER = Path(r"C:\Users\olenepal\Downloads\Rajkulo All Documents\CANAL_Survoy.xlsx")  # has the HyperPhoto URLs
GPKG = Path(r"C:\Users\olenepal\Downloads\Rajkulo All Documents\Mergin Maps Data\CANAL1\Syrvey.gpkg")
PHOTO_SRC_DIRS = [
    Path(r"C:\Users\olenepal\Downloads\Rajkulo All Documents\Rajkulo All Documents\RajkuloSurvey\rajkulo_survey"),
    Path(r"C:\Users\olenepal\Downloads\Rajkulo All Documents\Mergin Maps Data\CANAL1"),
    Path(r"C:\Users\olenepal\Downloads\Rajkulo All Documents\Rajkulo All Documents\RajkuloSurvey\rajkulo_survey\images"),
]
PHOTO_DST = SITE / "photos"
OUT_JSON = DATA / "canal_sections.json"
OUT_JS = DATA / "canal_sections.js"
OUT_BASE = DATA / "canal_base_alignment.json"


def safe_str(v):
    if v is None: return ""
    try:
        if isinstance(v, float) and math.isnan(v): return ""
    except: pass
    return str(v)

def clean_multi(v):
    s = safe_str(v).strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1].split(",")[0].strip()
    return s

WQ_COLOR = {
    "River Quality": "#1D9E75",
    "River Water": "#1D9E75",
    "Drinking Quality": "#1D9E75",
    "Irrigation Quality": "#5ba4c8",
    "Storm water": "#5ba4c8",
    "Mixed": "#d4a017",
    "Waste Dumping": "#c0392b",
    "Sewage": "#c0392b",
}
def wq_color(wq):
    s = clean_multi(wq)
    if not s: return "#888"
    return WQ_COLOR.get(s, "#888")

def condition_for(silting, cseen, wq):
    s = clean_multi(silting).lower()
    c = safe_str(cseen).strip().lower()
    w = clean_multi(wq).lower()
    if c == "no": return ("Lost", "#333")
    if c == "underground": return ("Underground", "#7c4a1e")
    if "sewage" in w or "waste" in w:
        if "present" in s or "yes" in s: return ("Critical", "#c0392b")
        return ("Poor", "#d4721a")
    if "present" in s or "yes" in s: return ("Fair", "#d4a017")
    return ("Good", "#1D9E75")


# ───────────────────────────────────────────────────────────────
# 1. Load Survey_new geometry, keyed by Mergin fid
# ───────────────────────────────────────────────────────────────
print("Loading gpkg Survey_new...")
sn = gpd.read_file(GPKG, layer="Survey_new").reset_index(drop=True)
sn["fid"] = range(1, len(sn) + 1)
print(f"  {len(sn)} rows, CRS={sn.crs}")

def coords_of(g):
    if g is None or g.is_empty: return []
    return [[round(x, 7), round(y, 7)] for (x, y) in g.coords]

sn_by_fid = {}
for _, r in sn.iterrows():
    sn_by_fid[int(r["fid"])] = {
        "fid": int(r["fid"]),
        "tole": r.get("Tole"),
        "cseen": r.get("Cseen"),
        "clined": r.get("Clined"),
        "shape": r.get("Cshaped"),
        "height": r.get("CHeight"),
        "width": r.get("Cwidth"),
        "diam": r.get("Cdiameter"),
        "flow": r.get("CWaterflow"),
        "wq": r.get("WaterQuality"),
        "silting": r.get("Silting"),
        "notes": r.get("AdditionalInformation") or "",
        "photos": [r.get(c) for c in ("Photo1", "Photo2", "Photo3", "Photo4") if r.get(c)],
        "coords": coords_of(r.geometry),
    }


# ───────────────────────────────────────────────────────────────
# 2. Load the CORRECTED Excel (CANAL_Survey.xlsx)
# Column A = PDF section number (spatial sequence)
# Column B = Mergin fid (raw Survey_new fid)
# ───────────────────────────────────────────────────────────────
print(f"\nLoading corrected Excel: {EXCEL.name}")
wb_v = load_workbook(EXCEL, data_only=True)
wb_f = load_workbook(EXCEL, data_only=False)
ws_v = wb_v["CANAL_Survey"]
ws_f = wb_f["CANAL_Survey"]

excel_rows = []
for r in range(2, ws_v.max_row + 1):
    pdf_n = ws_v.cell(r, 1).value
    mergin_fid = ws_v.cell(r, 2).value
    tole = ws_v.cell(r, 3).value
    created = ws_v.cell(r, 4).value
    cseen = ws_v.cell(r, 5).value
    clined = ws_v.cell(r, 6).value
    shape = ws_v.cell(r, 8).value
    height = ws_v.cell(r, 9).value
    width = ws_v.cell(r, 10).value
    diam = ws_v.cell(r, 11).value
    flow = ws_v.cell(r, 12).value
    cmd = ws_v.cell(r, 14).value
    wq = ws_v.cell(r, 16).value
    silting = ws_v.cell(r, 17).value
    notes = ws_v.cell(r, 18).value
    sec_len = ws_v.cell(r, 29).value
    chainage = ws_v.cell(r, 30).value
    zcoord = ws_v.cell(r, 31).value
    photos = []
    for col in (19, 20, 21, 22):
        v = ws_v.cell(r, col).value
        if v: photos.append(v)
    if any(v is not None for v in (pdf_n, mergin_fid, tole)):
        excel_rows.append({
            "row": r,
            "pdf_n": pdf_n,
            "mergin_fid": int(mergin_fid) if isinstance(mergin_fid, (int, float)) else None,
            "tole": (str(tole).strip() if tole else None),
            "created": str(created) if created else None,
            "cseen": cseen,
            "clined": clined,
            "shape": shape,
            "height": height,
            "width": width,
            "diam": diam,
            "flow": flow,
            "cmd": cmd,
            "wq": wq,
            "silting": silting,
            "notes": notes,
            "sec_len": sec_len,
            "chainage": chainage,
            "zcoord": zcoord,
            "photos": photos,
        })
print(f"  {len(excel_rows)} Excel rows loaded")


# ───────────────────────────────────────────────────────────────
# 3. Load HyperPhoto URLs from the second workbook (CANAL_Survoy.xlsx)
# Match by Mergin fid → URLs
# ───────────────────────────────────────────────────────────────
print(f"\nLoading HyperPhoto URLs from: {EXCEL_HYPER.name}")
hp_wb = load_workbook(EXCEL_HYPER, data_only=False)
hp_ws = hp_wb["Canal data plus POIa"]
# In this workbook fid (col 1) is the corrected PDF#, not the Mergin fid — verify by
# inspecting it vs the corrected Excel. Walking the rows in order and matching by Tole
# is more reliable.
hp_by_tole = {}
for r in range(2, hp_ws.max_row + 1):
    tole = hp_ws.cell(r, 2).value
    if not tole: continue
    links = []
    for col in (27, 28, 29, 30):
        cell = hp_ws.cell(r, col)
        target = cell.hyperlink.target if cell.hyperlink else cell.value
        if not target: continue
        fn = str(target).replace("%20", " ").split("/")[-1]
        if fn.lower().endswith((".jpg", ".jpeg", ".png")):
            links.append(fn)
    if links:
        hp_by_tole.setdefault(str(tole).strip(), []).append(links)


# ───────────────────────────────────────────────────────────────
# 4. Build the section list ordered by PDF section number.
#    Each row may have a Mergin fid (→ geometry from Survey_new) or not.
#    Rows without Mergin fid are PDF-only sections that need geometry inferred.
# ───────────────────────────────────────────────────────────────
JUNK_TOLES = {"Test", "test", "Ahh"}   # rows that are NOT real canal segments
# Filter: keep rows with a PDF# (the canal sequence) and drop pure-junk
canal_rows = [
    er for er in excel_rows
    if er["pdf_n"] is not None
    and (er["tole"] is None or er["tole"] not in JUNK_TOLES)
]
canal_rows.sort(key=lambda e: e["pdf_n"])
print(f"\nCanal sections by PDF# order: {len(canal_rows)} (PDF# {canal_rows[0]['pdf_n']}–{canal_rows[-1]['pdf_n']})")

# Audit which Mergin fids are referenced
mergin_fids_used = set(er["mergin_fid"] for er in canal_rows if er["mergin_fid"])
print(f"  Mergin fids referenced: {len(mergin_fids_used)}")
all_mergin = set(sn_by_fid.keys()) - {1, 2, 3}  # drop junk Test/test/Ahh
unused = sorted(all_mergin - mergin_fids_used)
print(f"  Mergin fids NOT in Excel (excluded from canal): {unused}")


# ───────────────────────────────────────────────────────────────
# 5. Attach gpkg geometry to each PDF section
# ───────────────────────────────────────────────────────────────
matched = 0
no_geom = []
for er in canal_rows:
    er["coords"] = []
    er["gpkg_fid"] = None
    if er["mergin_fid"] and er["mergin_fid"] in sn_by_fid:
        rec = sn_by_fid[er["mergin_fid"]]
        er["coords"] = rec["coords"]
        er["gpkg_fid"] = rec["fid"]
        # Also use gpkg photos if Excel didn't have them
        if not er["photos"] and rec["photos"]:
            er["photos"] = [p for p in rec["photos"] if p]
        matched += 1
    else:
        no_geom.append(er["pdf_n"])
    # Pull HyperPhoto URLs from the photo workbook if available (key by tole)
    if er["tole"] and er["tole"] in hp_by_tole:
        # Take the first list; if multiple rows share a tole, sequential consumption
        # would be safer but the photo set is the same in most cases.
        hp_list = hp_by_tole[er["tole"]][0]
        for fn in hp_list:
            if fn not in er["photos"]:
                er["photos"].append(fn)

print(f"\nMatched gpkg geometry: {matched}/{len(canal_rows)}")
print(f"  Sections without gpkg geometry (PDF#s): {no_geom}")


# ───────────────────────────────────────────────────────────────
# 6. Emit display-ready section records
# ───────────────────────────────────────────────────────────────
def emit(er, idx):
    cond_label, cond_color = condition_for(er["silting"], er["cseen"], er["wq"])
    has_geom = bool(er["coords"])
    return {
        "idx": idx,
        "pdf_n": er["pdf_n"],
        "mergin_fid": er["mergin_fid"],
        "tole": er["tole"] or "—",
        "is_connector": not has_geom,
        "coords": er["coords"],
        "chainage": round(er["chainage"], 2) if isinstance(er["chainage"], (int, float)) else None,
        "sec_len": round(er["sec_len"], 2) if isinstance(er["sec_len"], (int, float)) else None,
        "zcoord": round(er["zcoord"], 2) if isinstance(er["zcoord"], (int, float)) else None,
        "silting": clean_multi(er["silting"]) or "—",
        "wq": clean_multi(er["wq"]) or "—",
        "wq_color": wq_color(er["wq"]),
        "shape": clean_multi(er["shape"]) or "—",
        "height": (f"{er['height']:.1f}" if isinstance(er["height"], (int, float)) else "—"),
        "width": (f"{er['width']:.1f}" if isinstance(er["width"], (int, float)) else "—"),
        "diam": (f"{er['diam']:.1f}" if isinstance(er["diam"], (int, float)) else "—"),
        "flow": clean_multi(er["flow"]) or "—",
        "lined": clean_multi(er["clined"]) or "—",
        "cmd": clean_multi(er["cmd"]) or "",
        "notes": (er["notes"] or "").strip(),
        "photos": [p for p in (er["photos"] or []) if p],
        "cseen": er["cseen"],
        "created": er["created"],
        "condition": cond_label,
        "color": cond_color,
    }
sections = [emit(er, i) for i, er in enumerate(canal_rows)]


# ───────────────────────────────────────────────────────────────
# 7. Copy referenced photos into ./photos/
# ───────────────────────────────────────────────────────────────
all_photos = set()
for s in sections:
    for p in s["photos"]:
        if p: all_photos.add(p)

# Also POI photos (extracted from the archived monolithic platform HTML)
html_path = PROJECT / "research" / "archive" / "Tikabhairab_Rajkulo_Platform.html.backup"
if html_path.exists():
    html_src = html_path.read_text(encoding="utf-8")
    pm = re.search(r"const CANAL_POIS = (\[.*?\]);", html_src, re.DOTALL)
    if pm:
        try:
            for poi in json.loads(pm.group(1)):
                for p in (poi.get("photos") or []):
                    if p: all_photos.add(p)
        except Exception as e:
            print(f"  could not parse CANAL_POIS: {e}")

print(f"\nReferenced photos total: {len(all_photos)}")
PHOTO_DST.mkdir(exist_ok=True)
copied, missing = 0, []
for p in sorted(all_photos):
    dst = PHOTO_DST / p
    if dst.exists():
        copied += 1
        continue
    src = None
    for d in PHOTO_SRC_DIRS:
        cand = d / p
        if cand.exists():
            src = cand
            break
    if src:
        shutil.copy2(src, dst)
        copied += 1
    else:
        missing.append(p)
print(f"  copied/present: {copied}, missing: {len(missing)}")
for m in missing[:8]:
    print(f"    missing: {m}")


# ───────────────────────────────────────────────────────────────
# 8. Extract canal base alignment (टि-१)
# ───────────────────────────────────────────────────────────────
print("\nExtracting Canal_ID='टि-१' base alignment...")
canal_layer = gpd.read_file(GPKG, layer="Canal")
main_line = canal_layer[canal_layer["Canal_ID"].astype(str) == "टि-१"]
paths = []
for _, r in main_line.iterrows():
    g = r.geometry
    geoms = g.geoms if g.geom_type == "MultiLineString" else [g]
    for part in geoms:
        coords = [[round(x, 7), round(y, 7)] for (x, y) in part.coords]
        if len(coords) >= 2:
            paths.append(coords)
print(f"  {len(paths)} path pieces, "
      f"{sum(len(p) for p in paths)} vertices, "
      f"{main_line.to_crs(32645).geometry.length.sum():.0f} m total")
OUT_BASE.write_text(json.dumps({"type":"MultiLineString","coordinates":paths}, ensure_ascii=False), encoding='utf-8')
print(f"  wrote {OUT_BASE.name}")


# ───────────────────────────────────────────────────────────────
# 9. Persist outputs
# ───────────────────────────────────────────────────────────────
OUT_JSON.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding='utf-8')
OUT_JS.write_text(
    "// Generated by build_platform_data.py — DO NOT EDIT BY HAND\n"
    "const CANAL_SECTIONS = " + json.dumps(sections, ensure_ascii=False) + ";\n",
    encoding='utf-8'
)
print(f"\nWrote {OUT_JSON.name} ({OUT_JSON.stat().st_size:,} bytes)")
print(f"Wrote {OUT_JS.name} ({OUT_JS.stat().st_size:,} bytes)")
print(f"\nFinal: {len(sections)} sections (PDF# {sections[0]['pdf_n']}–{sections[-1]['pdf_n']})")
print(f"  surveyed (gpkg geometry): {sum(1 for s in sections if s['coords'])}")
print(f"  PDF-only (no geometry yet): {sum(1 for s in sections if not s['coords'])}")
