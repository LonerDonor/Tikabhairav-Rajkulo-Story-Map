"""Rebuild the platform's CANAL_SECTIONS data from the survey sources.

Truth model:
- CANAL_Survey.xlsx is the canonical mapping. Column A = PDF section number (the
  spatial sequence drawn across the 17 AutoCAD sheets, intake → outlet). Column B =
  the raw Mergin Maps fid (which keys into Survey_new geometry inside Syrvey.gpkg).
- Excel rows are stored in survey-collection (timestamp) order, NOT PDF order — the
  surveyor zig-zagged across the intake branch.
- Chainage (col AD) and Z coordinate (col AE) are Excel *formulas*. If the workbook
  was last saved by openpyxl (not Excel) it has no cached values, so this script
  evaluates those formulas itself instead of trusting `data_only=True`.
- gpkg Syrvey.gpkg layer `Survey_new` has the GPS-walked geometry per Mergin fid.
- gpkg Syrvey.gpkg layer `Canal` filtered to Canal_ID = टि-१ is the full AutoCAD
  alignment (12.8 km, 22 multilinestrings) — kept for reference.
- 12 sections (PDF# 52, 96–99, 101–107) have no Mergin fid. Their placeholder
  geometry is carried over from the current site/data.js so a rebuild never drops it.

Usage:
    python scripts/build_platform_data.py --src "D:\\Rajkulo All Documents"
    (or set the RAJKULO_SRC environment variable)
    add --copy-photos to also copy referenced originals into site/photos/

Output:
- site/data.js            → CANAL_SECTIONS block replaced in place (POIs/historic kept)
- data/canal_sections.js  → the CANAL_SECTIONS array on its own
- data/canal_sections.json → the same as JSON for inspection
- data/canal_base_alignment.json → the टि-१ alignment as a MultiLineString
"""
import sys, io, os, math, json, re, ast, shutil, argparse, operator
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path
from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string

ROOT = Path(__file__).resolve().parent   # scripts/
PROJECT = ROOT.parent                    # repo root
SITE = PROJECT / "site"                  # deployable web platform
DATA = PROJECT / "data"                  # GIS / build sources & intermediates
SITE_DATA_JS = SITE / "data.js"
OUT_JSON = DATA / "canal_sections.json"
OUT_JS = DATA / "canal_sections.js"
OUT_BASE = DATA / "canal_base_alignment.json"
PHOTO_DST = SITE / "photos"

DEFAULT_SRC_CANDIDATES = [
    Path(r"D:\Rajkulo All Documents"),
    Path.home() / "Downloads" / "Rajkulo All Documents",
]


def resolve_src(cli_value):
    if cli_value:
        return Path(cli_value)
    if os.environ.get("RAJKULO_SRC"):
        return Path(os.environ["RAJKULO_SRC"])
    for cand in DEFAULT_SRC_CANDIDATES:
        if cand.exists():
            return cand
    sys.exit("Source folder not found. Pass --src \"<path to Rajkulo All Documents>\" "
             "or set RAJKULO_SRC.")


def safe_str(v):
    if v is None: return ""
    if isinstance(v, float) and math.isnan(v): return ""
    return str(v)


def multi_values(v):
    """Split a Mergin multi-select answer like '{Strom Water, Sewage}' into a list.

    The previous version kept only the first value, which hid every 'Sewage' /
    'Waste Dumping' answer that was not listed first (28 of 30 sections).
    """
    s = safe_str(v).strip()
    if not s:
        return []
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    return [normalise_label(p) for p in s.split(",") if p.strip()]


def first_value(v):
    vals = multi_values(v)
    return vals[0] if vals else ""


LABEL_FIXES = {"strom water": "Storm Water", "storm water": "Storm Water"}

def normalise_label(s):
    s = s.strip()
    return LABEL_FIXES.get(s.lower(), s)


# Ordered worst → best; used to pick the headline value and its colour.
WQ_SEVERITY = ["Sewage", "Waste Dumping", "Mixed", "Storm Water",
               "Irrigation Quality", "River Water", "River Quality", "Drinking Quality"]
WQ_COLOR = {
    "river quality": "#1D9E75",
    "river water": "#1D9E75",
    "drinking quality": "#1D9E75",
    "irrigation quality": "#5ba4c8",
    "storm water": "#5ba4c8",
    "mixed": "#d4a017",
    "waste dumping": "#c0392b",
    "sewage": "#c0392b",
}

def worst_wq(values):
    if not values:
        return ""
    rank = {v.lower(): i for i, v in enumerate(WQ_SEVERITY)}
    return sorted(values, key=lambda v: rank.get(v.lower(), len(WQ_SEVERITY)))[0]

def wq_color(value):
    return WQ_COLOR.get(value.lower(), "#888") if value else "#888"


CONDITION_COLORS = {
    "Good": "#1D9E75", "Fair": "#d4a017", "Poor": "#d4721a", "Critical": "#c0392b",
    "Underground": "#7c4a1e", "Lost": "#333", "No data": "#9aa0a6",
}

def condition_for(silting, cseen, wq_values, flow):
    s = first_value(silting).lower()
    c = safe_str(cseen).strip().lower()
    w = " ".join(wq_values).lower()
    if c == "no": return "Lost"
    if c == "underground": return "Underground"
    if not c and not s and not w and not first_value(flow):
        return "No data"             # no field observation at all — don't paint it "Good"
    if "sewage" in w or "waste" in w:
        if "present" in s or "yes" in s: return "Critical"
        return "Poor"
    if "present" in s or "yes" in s: return "Fair"
    return "Good"


# ───────────────────────────────────────────────────────────────
# Excel formula evaluation (Chainage / Z columns)
# ───────────────────────────────────────────────────────────────
_BIN_OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
            ast.Mult: operator.mul, ast.Div: operator.truediv}
_REF = re.compile(r"\$?([A-Z]{1,3})\$?(\d+)")

def _eval_arith(node):
    if isinstance(node, ast.Expression): return _eval_arith(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        v = _eval_arith(node.operand)
        return v if isinstance(node.op, ast.UAdd) else -v
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_arith(node.left), _eval_arith(node.right))
    raise ValueError(f"unsupported formula element: {ast.dump(node)}")


class FormulaSheet:
    """Evaluates simple arithmetic formulas (+ - * / and cell refs) on one sheet."""

    def __init__(self, ws_values, ws_formulas):
        self.v, self.f, self.cache = ws_values, ws_formulas, {}

    def value(self, col, row, _depth=0):
        key = (col, row)
        if key in self.cache:
            return self.cache[key]
        cached = self.v.cell(row, col).value
        raw = self.f.cell(row, col).value
        if isinstance(raw, str) and raw.startswith("="):
            if isinstance(cached, (int, float)):
                result = cached                    # Excel saved a value — trust it
            elif _depth > 500:
                raise RecursionError("formula chain too deep")
            else:
                expr = raw[1:]
                def sub(m):
                    ref = self.value(column_index_from_string(m.group(1)), int(m.group(2)), _depth + 1)
                    if ref is None or ref == "":
                        ref = 0.0                  # Excel treats empty cells as 0
                    if not isinstance(ref, (int, float)):
                        raise ValueError(f"non-numeric reference {m.group(0)} in {raw}")
                    return repr(float(ref))
                try:
                    result = _eval_arith(ast.parse(_REF.sub(sub, expr), mode="eval"))
                except (ValueError, ZeroDivisionError, SyntaxError):
                    result = None
        else:
            result = raw if raw is not None else cached
        self.cache[key] = result
        return result


def num(v, nd=2):
    return round(v, nd) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


# ───────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", help='Folder "Rajkulo All Documents" (default: $RAJKULO_SRC or a known location)')
    ap.add_argument("--copy-photos", action="store_true", help="copy referenced originals into site/photos/")
    ap.add_argument("--skip-base", action="store_true", help="skip re-extracting the टि-१ alignment")
    args = ap.parse_args()

    src = resolve_src(args.src)
    excel = src / "Rajkulo All Documents" / "RajkuloSurvey" / "CANAL_Survey.xlsx"
    excel_hyper = src / "CANAL_Survoy.xlsx"            # has the HyperPhoto URLs
    gpkg = src / "Mergin Maps Data" / "CANAL1" / "Syrvey.gpkg"
    photo_src_dirs = [
        src / "Rajkulo All Documents" / "RajkuloSurvey" / "rajkulo_survey",
        src / "Mergin Maps Data" / "CANAL1",
        src / "Rajkulo All Documents" / "RajkuloSurvey" / "rajkulo_survey" / "images",
    ]
    for p in (excel, excel_hyper, gpkg):
        if not p.exists():
            sys.exit(f"Missing source file: {p}")
    print(f"Source folder: {src}")

    import geopandas as gpd   # imported late so --help works without it

    # 1. Survey_new geometry, keyed by Mergin fid ─────────────────
    print("Loading gpkg Survey_new...")
    sn = gpd.read_file(gpkg, layer="Survey_new").reset_index(drop=True)
    sn["fid"] = range(1, len(sn) + 1)
    print(f"  {len(sn)} rows, CRS={sn.crs}")

    def coords_of(g):
        if g is None or g.is_empty: return []
        return [[round(x, 7), round(y, 7)] for (x, y) in g.coords]

    sn_by_fid = {}
    for _, r in sn.iterrows():
        sn_by_fid[int(r["fid"])] = {
            "fid": int(r["fid"]),
            "photos": [r.get(c) for c in ("Photo1", "Photo2", "Photo3", "Photo4") if r.get(c)],
            "coords": coords_of(r.geometry),
        }

    # Existing placeholder geometry for sections without a Mergin fid.
    existing_coords = {}
    if SITE_DATA_JS.exists():
        m = re.search(r"const CANAL_SECTIONS = (\[.*?\n\]);", SITE_DATA_JS.read_text(encoding="utf-8"), re.S)
        if m:
            for s in json.loads(m.group(1)):
                if s.get("coords"):
                    existing_coords[s["pdf_n"]] = s["coords"]

    # 2. Canonical Excel ─────────────────────────────────────────
    print(f"\nLoading canonical Excel: {excel.name}")
    ws_v = load_workbook(excel, data_only=True)["CANAL_Survey"]
    ws_f = load_workbook(excel, data_only=False)["CANAL_Survey"]
    fs = FormulaSheet(ws_v, ws_f)
    COL_LEN, COL_CHAIN, COL_Z = 29, 30, 31

    excel_rows = []
    for r in range(2, ws_v.max_row + 1):
        c = lambda col: ws_v.cell(r, col).value
        pdf_n, mergin_fid, tole = c(1), c(2), c(3)
        if not any(v is not None for v in (pdf_n, mergin_fid, tole)):
            continue
        excel_rows.append({
            "row": r, "pdf_n": pdf_n,
            "mergin_fid": int(mergin_fid) if isinstance(mergin_fid, (int, float)) else None,
            "tole": (str(tole).strip() if tole else None),
            "created": str(c(4)) if c(4) else None,
            "cseen": c(5), "clined": c(6), "shape": c(8), "height": c(9), "width": c(10),
            "diam": c(11), "flow": c(12), "cmd": c(14), "wq": c(16), "silting": c(17),
            "notes": c(18),
            "sec_len": fs.value(COL_LEN, r),
            "chainage": fs.value(COL_CHAIN, r),
            "zcoord": fs.value(COL_Z, r),
            "photos": [c(col) for col in (19, 20, 21, 22) if c(col)],
        })
    print(f"  {len(excel_rows)} Excel rows loaded")

    # 3. HyperPhoto URLs from the second workbook (matched by Tole) ─
    print(f"\nLoading HyperPhoto URLs from: {excel_hyper.name}")
    hp_ws = load_workbook(excel_hyper, data_only=False)["Canal data plus POIa"]
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

    # 4. Section list ordered by PDF section number ──────────────
    JUNK_TOLES = {"Test", "test", "Ahh"}
    canal_rows = [er for er in excel_rows
                  if er["pdf_n"] is not None and (er["tole"] is None or er["tole"] not in JUNK_TOLES)]
    canal_rows.sort(key=lambda e: e["pdf_n"])
    print(f"\nCanal sections by PDF# order: {len(canal_rows)} "
          f"(PDF# {canal_rows[0]['pdf_n']}–{canal_rows[-1]['pdf_n']})")

    # 5. Attach geometry ─────────────────────────────────────────
    matched, carried, no_geom = 0, [], []
    for er in canal_rows:
        er["coords"], er["surveyed"] = [], False
        if er["mergin_fid"] and er["mergin_fid"] in sn_by_fid:
            rec = sn_by_fid[er["mergin_fid"]]
            er["coords"], er["surveyed"] = rec["coords"], True
            if not er["photos"] and rec["photos"]:
                er["photos"] = [p for p in rec["photos"] if p]
            matched += 1
        elif er["pdf_n"] in existing_coords:
            er["coords"] = existing_coords[er["pdf_n"]]
            carried.append(er["pdf_n"])
        else:
            no_geom.append(er["pdf_n"])
        if er["tole"] and er["tole"] in hp_by_tole:
            for fn in hp_by_tole[er["tole"]][0]:
                if fn not in er["photos"]:
                    er["photos"].append(fn)
    print(f"\nGPS-walked geometry: {matched}/{len(canal_rows)}")
    print(f"  placeholder geometry carried over from site/data.js: {carried}")
    print(f"  no geometry at all: {no_geom}")

    # 6. Emit display-ready records ──────────────────────────────
    def emit(er, idx):
        wq_list = multi_values(er["wq"])
        headline = worst_wq(wq_list)
        cond = condition_for(er["silting"], er["cseen"], wq_list, er["flow"])
        return {
            "idx": idx,
            "pdf_n": er["pdf_n"],
            "mergin_fid": er["mergin_fid"],
            "tole": er["tole"] or "—",
            "is_connector": not er["surveyed"],
            "coords": er["coords"],
            "chainage": num(er["chainage"]),
            "sec_len": num(er["sec_len"]),
            "zcoord": num(er["zcoord"]),
            "silting": first_value(er["silting"]) or "—",
            "wq": headline or "—",
            "wq_list": wq_list,
            "wq_color": wq_color(headline),
            "shape": first_value(er["shape"]) or "—",
            "height": (f"{er['height']:.1f}" if isinstance(er["height"], (int, float)) else "—"),
            "width": (f"{er['width']:.1f}" if isinstance(er["width"], (int, float)) else "—"),
            "diam": (f"{er['diam']:.1f}" if isinstance(er["diam"], (int, float)) else "—"),
            "flow": first_value(er["flow"]) or "—",
            "lined": first_value(er["clined"]) or "—",
            "cmd": first_value(er["cmd"]) or "",
            "notes": safe_str(er["notes"]).strip(),
            "photos": [p for p in (er["photos"] or []) if p],
            "cseen": er["cseen"],
            "created": er["created"],
            "condition": cond,
            "color": CONDITION_COLORS[cond],
        }
    sections = [emit(er, i) for i, er in enumerate(canal_rows)]

    # 7. Optionally copy referenced photos ───────────────────────
    if args.copy_photos:
        all_photos = {p for s in sections for p in s["photos"] if p}
        m = re.search(r"const CANAL_POIS = (\[.*?\]);", SITE_DATA_JS.read_text(encoding="utf-8"), re.S)
        if m:
            for poi in json.loads(m.group(1)):
                all_photos.update(p for p in (poi.get("photos") or []) if p)
        print(f"\nReferenced photos total: {len(all_photos)}")
        PHOTO_DST.mkdir(exist_ok=True)
        missing = []
        for p in sorted(all_photos):
            if (PHOTO_DST / p).exists(): continue
            src_file = next((d / p for d in photo_src_dirs if (d / p).exists()), None)
            if src_file: shutil.copy2(src_file, PHOTO_DST / p)
            else: missing.append(p)
        print(f"  missing: {len(missing)}", *missing[:8], sep="\n    ")

    # 8. Canal base alignment (टि-१) ─────────────────────────────
    if not args.skip_base:
        print("\nExtracting Canal_ID='टि-१' base alignment...")
        canal_layer = gpd.read_file(gpkg, layer="Canal")
        main_line = canal_layer[canal_layer["Canal_ID"].astype(str) == "टि-१"]
        paths = []
        for _, r in main_line.iterrows():
            g = r.geometry
            for part in (g.geoms if g.geom_type == "MultiLineString" else [g]):
                coords = [[round(x, 7), round(y, 7)] for (x, y) in part.coords]
                if len(coords) >= 2:
                    paths.append(coords)
        OUT_BASE.write_text(json.dumps({"type": "MultiLineString", "coordinates": paths}, ensure_ascii=False),
                            encoding='utf-8')
        print(f"  {len(paths)} path pieces → {OUT_BASE.name}")

    # 9. Persist outputs ─────────────────────────────────────────
    sections_js = "const CANAL_SECTIONS = " + json.dumps(sections, ensure_ascii=False, indent=2) + ";"
    OUT_JSON.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding='utf-8')
    OUT_JS.write_text("// Generated by build_platform_data.py — DO NOT EDIT BY HAND\n" + sections_js + "\n",
                      encoding='utf-8')

    site_js = SITE_DATA_JS.read_text(encoding="utf-8")
    new_site_js, n = re.subn(r"const CANAL_SECTIONS = \[.*?\n\];", lambda _: sections_js, site_js, count=1, flags=re.S)
    if n != 1:
        sys.exit("Could not find the CANAL_SECTIONS block in site/data.js — not modified.")
    SITE_DATA_JS.write_text(new_site_js, encoding="utf-8")

    # 10. Refresh the open-data downloads (site/downloads/) from the new data.js
    print("\nExporting open data to site/downloads/ ...")
    import export_open_data
    export_open_data.main()

    from collections import Counter
    print(f"\nWrote {OUT_JSON.name}, {OUT_JS.name} and updated site/data.js")
    print(f"Final: {len(sections)} sections (PDF# {sections[0]['pdf_n']}–{sections[-1]['pdf_n']})")
    print(f"  GPS-walked: {sum(not s['is_connector'] for s in sections)}, "
          f"placeholder: {sum(s['is_connector'] for s in sections)}")
    print(f"  with chainage: {sum(s['chainage'] is not None for s in sections)}, "
          f"with Z: {sum(s['zcoord'] is not None for s in sections)}")
    print(f"  conditions: {dict(Counter(s['condition'] for s in sections))}")


if __name__ == "__main__":
    main()
