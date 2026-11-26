"""Export the survey data as open, reusable files for the site's "Download data" links.

Reads site/data.js (CANAL_SECTIONS, CANAL_POIS, CANAL_HISTORIC) and writes into
site/downloads/:

    rajkulo_sections.geojson            107 canal sections (LineString) with all attributes
    rajkulo_sections.csv                the same attributes, one row per section (+ start/end coordinates)
    rajkulo_points_of_interest.geojson  68 points of interest (Point)
    rajkulo_points_of_interest.csv
    rajkulo_historic_branches.geojson   96 historic distributary lines
    DATA_README.txt                     field dictionary, licence and how to cite
    rajkulo_open_data.zip               all of the above in one file

Run after build_platform_data.py (which calls this automatically):
    python scripts/export_open_data.py
"""
import csv, io, json, re, sys, zipfile
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).resolve().parent
SITE = ROOT.parent / "site"
DATA_JS = SITE / "data.js"
OUT = SITE / "downloads"
SITE_URL = "https://lonerdonor.github.io/Tikabhairav-Rajkulo-Story-Map/"
PHOTO_URL = SITE_URL + "photos/large/"
ZIP_DATE = (2022, 5, 11, 0, 0, 0)       # fixed timestamp → identical zip on every rebuild

CITATION = ("Joshi, H. R. (2022). Tikabhairab Rajkulo field survey, May 2022 [Data set]. "
            "Living Heritage Map of the Tikabhairab Rajkulo. " + SITE_URL)

SECTION_FIELDS = [
    ("pdf_n", "Section number in the CAD drawings (intake → outlet order)"),
    ("mergin_fid", "Feature id in the Mergin Maps survey layer (blank = not GPS-walked)"),
    ("tole", "Locality / surveyor's section label, as recorded"),
    ("gps_walked", "true = geometry walked with GPS in May 2022; false = approximate CAD-only placeholder"),
    ("chainage_start_m", "Main-line distance from the intake at the start of the section (m)"),
    ("chainage_end_m", "Main-line distance from the intake at the end of the section (m) = Station Point"),
    ("length_m", "Section length (m)"),
    ("elevation_interp_m", "Elevation interpolated linearly between the intake (1,477.16 m) and the outlet (1,314.02 m); not measured"),
    ("flow", "Flow regime observed: Perennial / Seasonal / Unknown"),
    ("water_quality", "Every water-quality value recorded, separated by '; '"),
    ("sewage_or_waste", "true if Sewage or Waste Dumping was among the water-quality values"),
    ("silting", "Present / Absent"),
    ("lined", "Yes / No"),
    ("shape", "Rectangular / Circular"),
    ("width_cm", "Inner width (cm), rectangular sections"),
    ("height_cm", "Inner height (cm), rectangular sections"),
    ("diameter_cm", "Diameter (cm), circular sections"),
    ("condition", "Derived class: Good / Fair / Poor / Critical / Lost / No data (rules in DATA_README.txt)"),
    ("notes", "Surveyor's field notes, as recorded (English)"),
    ("photos", "Photo URLs, separated by '; '"),
    ("surveyed_at", "Date and time the section was recorded"),
]
POI_FIELDS = [
    ("fid", "Point id in the Mergin Maps POI layer"),
    ("category", "Contamination / Cross Drainage / Encroachment / Vulnerable Zone / Intake Structure / Observation Point"),
    ("comment", "Surveyor's comment, as recorded (English)"),
    ("lon", "Longitude (WGS 84)"),
    ("lat", "Latitude (WGS 84)"),
    ("photos", "Photo URLs, separated by '; '"),
]


def read_const(text, name):
    m = re.search(r"const " + name + r"\s*=\s*", text)
    if not m:
        raise SystemExit(f"{name} not found in {DATA_JS}")
    value, _ = json.JSONDecoder().raw_decode(text, m.end())
    return value


def blank(v):
    return None if v in (None, "", "—") else v


def num(v):
    try:
        return float(v) if blank(v) is not None else None
    except (TypeError, ValueError):
        return None


def section_props(s):
    wq = s.get("wq_list") or ([s["wq"]] if blank(s.get("wq")) else [])
    start = (s["chainage"] - s["sec_len"]) if s.get("chainage") is not None and s.get("sec_len") is not None else None
    return {
        "pdf_n": s["pdf_n"],
        "mergin_fid": s.get("mergin_fid"),
        "tole": blank(s.get("tole")),
        "gps_walked": not s.get("is_connector"),
        "chainage_start_m": round(start, 2) if start is not None else None,
        "chainage_end_m": s.get("chainage"),
        "length_m": s.get("sec_len"),
        "elevation_interp_m": s.get("zcoord"),
        "flow": blank(s.get("flow")),
        "water_quality": "; ".join(wq) or None,
        "sewage_or_waste": any(re.search(r"sewage|waste", w, re.I) for w in wq),
        "silting": blank(s.get("silting")),
        "lined": blank(s.get("lined")),
        "shape": blank(s.get("shape")),
        "width_cm": num(s.get("width")),
        "height_cm": num(s.get("height")),
        "diameter_cm": num(s.get("diam")),
        "condition": s.get("condition"),
        "notes": blank(s.get("notes")),
        "photos": "; ".join(PHOTO_URL + p for p in s.get("photos") or []) or None,
        "surveyed_at": blank(s.get("created")),
    }


def poi_props(p):
    return {
        "fid": p["fid"],
        "category": p.get("cat"),
        "comment": blank((p.get("comment") or "").strip()),
        "lon": p["lon"],
        "lat": p["lat"],
        "photos": "; ".join(PHOTO_URL + f for f in p.get("photos") or []) or None,
    }


def geojson(features, name):
    return json.dumps({
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "license": "CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/",
        "attribution": CITATION,
        "features": features,
    }, ensure_ascii=False, indent=1)


def to_csv(rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else str(r[k]).lower() if isinstance(r[k], bool) else r[k])
                    for k in fields})
    return "﻿" + buf.getvalue()          # BOM so Excel opens it as UTF-8


def readme(n_sec, n_poi, n_hist):
    lines = [
        "TIKABHAIRAB RAJKULO — OPEN SURVEY DATA",
        "=" * 38, "",
        f"Field survey of the Tikabhairab Rajkulo canal, Lalitpur, Nepal, 4–11 May 2022.",
        f"{n_sec} canal sections, {n_poi} points of interest, {n_hist} historic branch lines.",
        f"Interactive map: {SITE_URL}", "",
        "LICENCE",
        "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "https://creativecommons.org/licenses/by/4.0/",
        "You may share and adapt the data, including commercially, as long as you give credit.", "",
        "HOW TO CITE", CITATION, "",
        "COORDINATES", "WGS 84 (EPSG:4326), longitude/latitude in decimal degrees.", "",
        "HOW 'condition' IS DERIVED",
        "  Lost      the canal could not be seen",
        "  Critical  sewage or waste dumping recorded, and silting present",
        "  Poor      sewage or waste dumping recorded, no silting",
        "  Fair      silting present, no sewage or waste",
        "  Good      none of the above recorded",
        "  No data   nothing was recorded (includes the 12 CAD-only sections)", "",
        "CAVEATS",
        "- Chainage is a main-line distance; parallel branches restart from their upstream section.",
        "- Elevations are a straight-line interpolation, not measured levels.",
        "- Sections with gps_walked = false have approximate geometry and no field observations.",
        "- Notes and comments are reproduced as the surveyors wrote them.", "",
        "FILES",
        "  rajkulo_sections.geojson / .csv            canal sections",
        "  rajkulo_points_of_interest.geojson / .csv  points of interest",
        "  rajkulo_historic_branches.geojson          historic distributary network (canal_id)", "",
        "SECTION FIELDS",
    ]
    lines += [f"  {k:20s} {d}" for k, d in SECTION_FIELDS]
    lines += ["", "POINT-OF-INTEREST FIELDS"]
    lines += [f"  {k:20s} {d}" for k, d in POI_FIELDS]
    return "\n".join(lines) + "\n"


def main():
    text = DATA_JS.read_text(encoding="utf-8")
    sections = read_const(text, "CANAL_SECTIONS")
    pois = read_const(text, "CANAL_POIS")
    historic = read_const(text, "CANAL_HISTORIC")

    sec_rows = []
    sec_features = []
    for s in sections:
        props = section_props(s)
        coords = s.get("coords") or []
        sec_features.append({"type": "Feature", "properties": props,
                             "geometry": {"type": "LineString", "coordinates": coords} if len(coords) >= 2 else None})
        row = dict(props)
        if coords:
            row.update(start_lon=coords[0][0], start_lat=coords[0][1], end_lon=coords[-1][0], end_lat=coords[-1][1])
        sec_rows.append(row)

    poi_features = [{"type": "Feature", "properties": poi_props(p),
                     "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]}} for p in pois]
    hist_features = [{"type": "Feature", "properties": {"canal_id": h.get("id")},
                      "geometry": {"type": "LineString", "coordinates": h["coords"]}} for h in historic]

    files = {
        "rajkulo_sections.geojson": geojson(sec_features, "rajkulo_sections"),
        "rajkulo_sections.csv": to_csv(sec_rows, [k for k, _ in SECTION_FIELDS] + ["start_lon", "start_lat", "end_lon", "end_lat"]),
        "rajkulo_points_of_interest.geojson": geojson(poi_features, "rajkulo_points_of_interest"),
        "rajkulo_points_of_interest.csv": to_csv([poi_props(p) for p in pois], [k for k, _ in POI_FIELDS]),
        "rajkulo_historic_branches.geojson": geojson(hist_features, "rajkulo_historic_branches"),
        "DATA_README.txt": readme(len(sections), len(pois), len(historic)),
    }
    OUT.mkdir(exist_ok=True)
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8", newline="\n")

    with zipfile.ZipFile(OUT / "rajkulo_open_data.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, content.encode("utf-8"))

    for p in sorted(OUT.iterdir()):
        print(f"  {p.name:38s} {p.stat().st_size / 1024:8.1f} KB")


if __name__ == "__main__":
    main()
