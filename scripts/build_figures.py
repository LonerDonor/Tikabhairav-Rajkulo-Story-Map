"""Generate the report's data-driven figures and maps from the May 2022 survey.

Inputs:
  - site/data.js (CANAL_SECTIONS, CANAL_POIS): section attributes and the main-line
    chainage (distance from the intake at the END of each section). This is the
    primary data source; every chainage in the figures comes from it.
  - Mergin Maps GeoPackages (Survey_new, Canal, POIS, Location) in
    "<Rajkulo All Documents>/Mergin Maps Data/CANAL1", for map geometry only.

Outputs (research/figures/, 300 DPI):
  fig_5_1_flow_regime.png        flow regime and recorded contamination along the main line
  fig_6_1_survey_attributes.png  flow, water quality, silting, lining and condition by chainage
  map_4_1_alignment.png          alignment and points of interest
  map_5_1_contamination.png      water quality along the alignment
  map_8_1_priority.png           restoration priority by 1 km band (scores computed here)

The restoration-priority band scores (report Table 8.1) are computed by
`priority_bands()` and printed as a markdown table.

Usage:
    python scripts/build_figures.py --src "D:\\Rajkulo All Documents"
    (or set RAJKULO_SRC). --only fig_5_1,map_8_1 builds a subset.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import sys as _sys
if hasattr(_sys.stdout, "reconfigure"):
    _sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, FancyBboxPatch, Rectangle
import matplotlib.patheffects as pe
import geopandas as gpd
import pandas as pd
from shapely.ops import linemerge, unary_union
from shapely.geometry import LineString, MultiLineString

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hydraulic_recheck import load_js_array, main_line as main_line_idx, chainage_of  # noqa: E402

try:
    import contextily as cx
    HAS_BASEMAP = True
except Exception:
    HAS_BASEMAP = False

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

GIS_DIR = None  # set in main() from --src / RAJKULO_SRC
OUT_DIR = Path(__file__).parent.parent / "research" / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UTM_CRS = 32645  # WGS 84 / UTM zone 45N — appropriate for Lalitpur

# Brand palette matching the report
ACCENT = "#1F4E79"
ACCENT_LIGHT = "#5D8FBC"

# Water quality categories from the Quality table
QUALITY_LABELS = {1: "River quality", 2: "Storm water", 3: "Sewage", 4: "Waste dumping"}
QUALITY_COLORS = {1: "#2E86AB", 2: "#F4D35E", 3: "#9C3D54", 4: "#5C5C5C"}

# Flow regime palette
FLOW_COLORS = {
    "Perennial": "#1B9E77",
    "Seasonal": "#F4D35E",
    "Interupted": "#E63946",  # GPS spelling preserved; remapped below
    "Disturbed": "#E63946",
    "Unknown": "#B0B0B0",
}

# Priority palette for MAP 8.1
PRIORITY_COLORS = {
    "Critical": "#C0392B",
    "High": "#E67E22",
    "Medium": "#F1C40F",
    "Low": "#27AE60",
}

# Junk / test rows to filter from Survey_new
JUNK_TOLES = {
    "Test", "test", "Old route", "Possible canal", "Ahh",
    "canal 1 rajdal non existing",
}

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 9,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.labelsize": 9,
    "axes.edgecolor": "#555555",
    "axes.linewidth": 0.6,
    "axes.titlecolor": ACCENT,
    "xtick.color": "#333333",
    "ytick.color": "#333333",
    "legend.fontsize": 8,
    "legend.framealpha": 0.92,
    "legend.edgecolor": "#888888",
    "figure.dpi": 100,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.15,
})


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data():
    survey = gpd.read_file(GIS_DIR / "Syrvey.gpkg", layer="Survey_new").to_crs(UTM_CRS).reset_index(drop=True)
    survey["fid"] = range(1, len(survey) + 1)   # Mergin fid, as in build_platform_data.py
    canal = gpd.read_file(GIS_DIR / "Syrvey.gpkg", layer="Canal").to_crs(UTM_CRS)
    pois = gpd.read_file(GIS_DIR / "POIS.gpkg", layer="POIS").to_crs(UTM_CRS)
    locations = gpd.read_file(GIS_DIR / "Syrvey.gpkg", layer="Location").to_crs(UTM_CRS)

    # Filter survey to non-junk sections
    survey = survey[~survey["Tole"].isin(JUNK_TOLES)].copy().reset_index(drop=True)

    # The blue surveyed canal is ALL non-junk Survey_new sections (both Cseen='Yes' and 'No').
    # Confirmed via gap analysis: Cseen='No' sections (1,716 m of 10,122 m) fill the
    # apparent visible gaps and bring 6+ "isolated" POIs back onto the canal.
    # Cseen distinguishes physical visibility at survey time, not canal existence.
    surveyed_all = survey.copy()
    surveyed_seen = survey[survey["Cseen"] == "Yes"].copy()
    surveyed_absent = survey[survey["Cseen"] == "No"].copy()

    # Reference network (Canal layer) — all of it, rendered as orange background.
    reference = canal.copy()
    # `main` and `branches` kept as legacy variables that downstream functions expect.
    main = surveyed_all      # all surveyed sections, treated as continuous blue alignment
    branches = reference     # orange reference network behind it

    # Build a merged LineString trunk from the surveyed (Cseen='Yes') sections
    # for chainage projection.
    def _merge_and_pick_longest(gseries):
        geoms = []
        for geom in gseries:
            if isinstance(geom, MultiLineString):
                geoms.extend(list(geom.geoms))
            elif isinstance(geom, LineString):
                geoms.append(geom)
        merged = linemerge(unary_union(geoms))
        if isinstance(merged, MultiLineString):
            return max(merged.geoms, key=lambda g: g.length)
        return merged

    main_line = _merge_and_pick_longest(surveyed_all.geometry)
    surveyed_total = surveyed_all.geometry.length.sum()
    print(f"  blue (all surveyed) trunk: {main_line.length:.1f} m connected; "
          f"{surveyed_total:.1f} m total across {len(surveyed_all)} sections")

    # Direction check: orient main_line so chainage = 0 is the intake end.
    # Use the named Tikabhairav temple location if present, else the southernmost point.
    intake_row = locations[locations["Location"] == "टिकाभैरव मन्दिर"]
    if len(intake_row):
        intake_pt = intake_row.geometry.iloc[0]
    else:
        # fallback — southernmost (lowest Y) endpoint of canal extents
        minx, miny, maxx, maxy = main.total_bounds
        from shapely.geometry import Point
        intake_pt = Point((minx + maxx) / 2, miny)
    proj_start = main_line.project(main_line.boundary.geoms[0]) if main_line.boundary else 0
    proj_intake = main_line.project(intake_pt)
    # If intake projects to the FAR end of the line, reverse the line so 0 = intake.
    if proj_intake > main_line.length / 2:
        main_line = LineString(list(main_line.coords)[::-1])
        print(f"  (reversed main_line so chainage 0 = intake end)")
    print(f"  intake projects to main_line.project = {main_line.project(intake_pt):.1f} m "
          f"(should be near 0 of {main_line.length:.1f} m)")

    return survey, canal, main, branches, pois, locations, main_line


def decode_quality(s):
    """Parse a {1,2,3}-style string into a sorted set of ints."""
    if not isinstance(s, str):
        return set()
    s = s.strip().strip("{}")
    if not s:
        return set()
    return {int(x) for x in s.split(",") if x.strip().isdigit()}


def section_midpoint(geom):
    return geom.interpolate(0.5, normalized=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_north_arrow(ax, x=0.94, y=0.92, length=0.06):
    ax.annotate(
        "N",
        xy=(x, y), xycoords="axes fraction",
        xytext=(x, y - length), textcoords="axes fraction",
        arrowprops=dict(arrowstyle="->", color="#333333", lw=1.2),
        ha="center", va="bottom", fontsize=10, fontweight="bold", color="#333333",
    )


def add_scalebar(ax, length_m=1000, label=None, location="lower left"):
    # length_m in metres; assumes axes are in projected UTM metres
    from matplotlib.transforms import blended_transform_factory
    fig = ax.get_figure()
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    span = xmax - xmin
    bar_x0 = xmin + 0.04 * span
    bar_x1 = bar_x0 + length_m
    bar_y = ymin + 0.04 * (ymax - ymin)
    h = 0.008 * (ymax - ymin)
    ax.plot([bar_x0, bar_x1], [bar_y, bar_y], color="#333333", lw=2.5, solid_capstyle="butt")
    ax.plot([bar_x0, bar_x0], [bar_y - h, bar_y + h], color="#333333", lw=1.2)
    ax.plot([bar_x1, bar_x1], [bar_y - h, bar_y + h], color="#333333", lw=1.2)
    label = label or f"{length_m/1000:g} km"
    ax.text(
        (bar_x0 + bar_x1) / 2, bar_y + 2.5 * h, label,
        ha="center", va="bottom", fontsize=8, color="#333333",
        path_effects=[pe.withStroke(linewidth=2, foreground="white")],
    )


def try_add_basemap(ax, provider=None):
    if not HAS_BASEMAP:
        return False
    try:
        provider = provider or cx.providers.Esri.WorldImagery
        cx.add_basemap(ax, crs=f"EPSG:{UTM_CRS}", source=provider, attribution_size=6, attribution="")
        return True
    except Exception as e:
        print(f"  (basemap unavailable: {type(e).__name__}: {e})")
        return False


# ---------------------------------------------------------------------------
# Survey data from site/data.js (primary source for chainage and attributes)
# ---------------------------------------------------------------------------

SITE_DATA_JS = Path(__file__).resolve().parent.parent / "site" / "data.js"


def load_survey_js():
    """Sections and POIs from site/data.js, with main-line membership and POI chainage."""
    sections, _ = load_js_array(SITE_DATA_JS, "CANAL_SECTIONS")
    pois, _ = load_js_array(SITE_DATA_JS, "CANAL_POIS")
    main_idx = main_line_idx(sections)
    for s in sections:
        s["on_main"] = s["idx"] in main_idx
        s["x0"] = (s["chainage"] - s["sec_len"]) if s["chainage"] is not None else None
    walked = [s for s in sections if not s["is_connector"] and s["coords"] and s["chainage"] is not None]
    for q in pois:
        (d, x), s = min(((chainage_of({"lat": q["lat"], "lon": q["lon"]}, s), s) for s in walked),
                        key=lambda c: c[0][0])
        q["chainage"], q["snap_m"], q["section"] = x, d, s["pdf_n"]
    return sections, pois


def _contam_score(s):
    w = set(s["wq_list"])
    if not w:
        return None
    if "Sewage" in w and "Waste Dumping" in w:
        return 4
    if "Sewage" in w or "Waste Dumping" in w:
        return 2
    if "Storm Water" in w:
        return 1
    return 0


def _silt_score(s):
    return {"Present": 2, "Absent": 0}.get(s["silting"], 1)


def _encroach_score(s, enc_poi_sections):
    note = (s["notes"] or "").lower()
    if s["condition"] == "Lost" or re.search(r"under\s*ground|under road|below road", note):
        return 2
    if re.search(r"retaining wall|residential|building|plotting|disrupt|road", note) \
            or s["pdf_n"] in enc_poi_sections:
        return 1
    return 0


def priority_bands(sections, pois, band_m=1000.0, min_walked_m=500.0):
    """Report Table 8.1. Length-weighted mean scores over the GPS-walked main-line
    sections in each 1 km chainage band (sections are split at band edges).
      contamination: 0 river water only, 1 storm water, 2 sewage or waste dumping,
                     4 sewage and waste dumping (sections without a record left out)
      silting:       0 absent, 1 not recorded, 2 present
      encroachment:  2 canal not seen, or recorded underground / under a road;
                     1 retaining wall, buildings, plotting or disruption noted, or an
                     Encroachment POI on the section; 0 otherwise
    Tiers on the total (max 8): Critical >= 5, High >= 3.5, Medium >= 2, Low < 2.
    Bands with less than `min_walked_m` walked are not scored."""
    enc_poi = {q["section"] for q in pois if q["cat"] == "Encroachment"}
    main = [s for s in sections if s["on_main"] and not s["is_connector"] and s["chainage"] is not None]
    end = max(s["chainage"] for s in sections if s["on_main"])
    rows = []
    b0 = 0.0
    while b0 < end:
        b1 = min(b0 + band_m, end)
        acc = {"c": [0.0, 0.0], "s": [0.0, 0.0], "e": [0.0, 0.0]}
        walked = 0.0
        for s in main:
            ov = max(0.0, min(b1, s["chainage"]) - max(b0, s["x0"]))
            if ov <= 0:
                continue
            walked += ov
            c = _contam_score(s)
            if c is not None:
                acc["c"][0] += c * ov
                acc["c"][1] += ov
            acc["s"][0] += _silt_score(s) * ov
            acc["s"][1] += ov
            acc["e"][0] += _encroach_score(s, enc_poi) * ov
            acc["e"][1] += ov
        row = {"x0": b0, "x1": b1, "walked_m": walked}
        if walked >= min_walked_m:
            for k in "cse":
                row[k] = round(acc[k][0] / acc[k][1], 1) if acc[k][1] else 0.0
            row["total"] = round(row["c"] + row["s"] + row["e"], 1)
            t = row["total"]
            row["tier"] = "CRITICAL" if t >= 5 else "HIGH" if t >= 3.5 else "MEDIUM" if t >= 2 else "LOW"
        else:
            row["tier"] = None
        rows.append(row)
        b0 = b1
    return rows


def print_priority_table(rows):
    print("\n| Band | Walked (m) | Contam. (0–4) | Silting (0–2) | Encroach. (0–2) | Total / 8 | Priority |")
    print("|---|---:|---:|---:|---:|---:|---|")
    for r in rows:
        band = f"{r['x0'] / 1000:g}–{r['x1'] / 1000:.2f} km".replace(".00 km", " km")
        if r["tier"]:
            print(f"| {band} | {r['walked_m']:.0f} | {r['c']:.1f} | {r['s']:.1f} | {r['e']:.1f} | "
                  f"{r['total']:.1f} | {r['tier']} |")
        else:
            print(f"| {band} | {r['walked_m']:.0f} | — | — | — | — | Not scored (not walked) |")


def _band_ranges(rows, tier):
    out = []
    for r in rows:
        if r["tier"] == tier:
            if out and abs(out[-1][1] - r["x0"]) < 1e-6:
                out[-1][1] = r["x1"]
            else:
                out.append([r["x0"], r["x1"]])
    return ", ".join(f"{a / 1000:g}–{b / 1000:g} km" for a, b in out)


# ---------------------------------------------------------------------------
# Figure 5.1 — Flow regime and recorded contamination along the main line
# ---------------------------------------------------------------------------

FLOW_DRAW = {
    "Perennial": "#1B9E77",
    "Seasonal": "#F4D35E",
    "Unknown": "#B0B0B0",
    "Not recorded": "#E6E6E6",
}
NOT_WALKED = dict(facecolor="white", edgecolor="#999999", hatch="////", lw=0.3)


def _strip(ax, sections, y, h, color_fn):
    for s in sections:
        if s["is_connector"]:
            ax.add_patch(Rectangle((s["x0"] / 1000, y), s["sec_len"] / 1000, h, **NOT_WALKED))
        else:
            ax.add_patch(Rectangle((s["x0"] / 1000, y), s["sec_len"] / 1000, h,
                                   facecolor=color_fn(s), edgecolor="white", lw=0.25))
    end = max(s["chainage"] for s in sections)
    ax.add_patch(Rectangle((0, y), end / 1000, h, fill=False, ec="#444444", lw=0.6))


def fig_5_1_flow_regime(sections, pois):
    out = OUT_DIR / "fig_5_1_flow_regime.png"
    main = sorted((s for s in sections if s["on_main"]), key=lambda s: s["x0"])
    end = max(s["chainage"] for s in main)
    fig, ax = plt.subplots(figsize=(8.5, 3.3))
    flow = lambda s: FLOW_DRAW.get(s["flow"], FLOW_DRAW["Not recorded"])
    sew = lambda s: ("#9C3D54" if {"Sewage", "Waste Dumping"} & set(s["wq_list"])
                     else "#CFE3EE" if s["wq_list"] else FLOW_DRAW["Not recorded"])
    _strip(ax, main, 1.35, 0.5, flow)
    _strip(ax, main, 0.55, 0.5, sew)
    ax.text(-0.15, 1.6, "Flow regime", ha="right", va="center", fontsize=8)
    ax.text(-0.15, 0.8, "Sewage or\nwaste dumping", ha="right", va="center", fontsize=8)
    # unsurveyed transition and contamination POIs
    last_per = max(s["chainage"] for s in main if s["flow"] == "Perennial")
    first_seas = min(s["x0"] for s in main if s["flow"] == "Seasonal")
    for xk in (last_per, first_seas):
        ax.axvline(xk / 1000, color="#222222", lw=0.6, ls=":", ymin=0.12, ymax=0.88)
    ax.text(first_seas / 1000 + 0.08, 2.0, f"Perennial flow ends at {last_per / 1000:.3f} km; "
            f"{(first_seas - last_per) / 1000:.3f} km not walked; seasonal from {first_seas / 1000:.3f} km",
            ha="left", va="bottom", fontsize=6.5)
    contam = sorted((q for q in pois if q["cat"] == "Contamination"), key=lambda q: q["chainage"])
    groups = []
    for q in contam:
        if groups and q["chainage"] - groups[-1][-1]["chainage"] < 400:
            groups[-1].append(q)
        else:
            groups.append([q])
    for g in groups:
        for q in g:
            ax.plot(q["chainage"] / 1000, 0.42, marker="v", color="#9C3D54", ms=6, mec="white", mew=0.6)
        xm = sum(q["chainage"] for q in g) / len(g) / 1000
        ax.text(xm, 0.25, "POI " + ", ".join(str(q["fid"]) for q in g), ha="center", va="top", fontsize=6)
    ax.set_xlim(-0.2, end / 1000 + 0.2)
    ax.set_ylim(0.0, 2.4)
    ax.set_yticks([])
    ax.set_xlabel("Main-line chainage from intake (km)")
    ax.set_title("Figure 5.1  Flow regime and recorded contamination along the main line",
                 loc="left", pad=8)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    legend = [Patch(color=FLOW_DRAW[k], label=k) for k in ("Perennial", "Seasonal", "Unknown")]
    legend += [Patch(color="#9C3D54", label="Sewage or waste dumping recorded"),
               Patch(color="#CFE3EE", label="Water recorded, no sewage or waste"),
               Patch(color=FLOW_DRAW["Not recorded"], label="Walked, not recorded"),
               Patch(label="Not walked (CAD only)", **NOT_WALKED),
               Line2D([0], [0], marker="v", color="w", markerfacecolor="#9C3D54", ms=7,
                      label="Contamination POI")]
    ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.30), ncol=4, frameon=False,
              fontsize=7)
    fig.text(0.01, 0.01, "Source: site/data.js (May 2022 survey). Main line only; parallel branches omitted.",
             fontsize=6.5, color="#666666", style="italic")
    fig.subplots_adjust(bottom=0.36, top=0.88, left=0.13, right=0.98)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Figure 6.1 — Survey attributes along the main line
# ---------------------------------------------------------------------------

CONDITION_ORDER = ["Good", "Fair", "Poor", "Critical", "Lost", "No data"]


def fig_6_1_survey_attributes(sections, pois):
    out = OUT_DIR / "fig_6_1_survey_attributes.png"
    main = sorted((s for s in sections if s["on_main"]), key=lambda s: s["x0"])
    end = max(s["chainage"] for s in main)
    cond_color = {}
    for s in sections:
        cond_color.setdefault(s["condition"], s["color"])

    def wq(s):
        w = set(s["wq_list"])
        if not w:
            return FLOW_DRAW["Not recorded"]
        if "Sewage" in w:
            return "#9C3D54"
        if "Waste Dumping" in w:
            return "#5C5C5C"
        if "Storm Water" in w:
            return "#B5A1D3" if "River Quality" not in w else "#7BAFD4"
        return "#2E86AB"

    silt = lambda s: {"Present": "#8C6D46", "Absent": "#D9EAD3"}.get(s["silting"], FLOW_DRAW["Not recorded"])
    lined = lambda s: {"Yes": "#4F6D8C", "No": "#E6B8A2"}.get(s["lined"], FLOW_DRAW["Not recorded"])
    rows = [
        ("Flow regime", lambda s: FLOW_DRAW.get(s["flow"], FLOW_DRAW["Not recorded"])),
        ("Water quality", wq),
        ("Silting", silt),
        ("Lining", lined),
        ("Condition", lambda s: cond_color.get(s["condition"], "#cccccc")),
    ]
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    h, gap = 0.55, 0.3
    for i, (label, fn) in enumerate(rows):
        y = (len(rows) - 1 - i) * (h + gap)
        _strip(ax, main, y, h, fn)
        ax.text(-0.15, y + h / 2, label, ha="right", va="center", fontsize=8)
    for s in main:
        if re.search(r"one\s*side|on sided|one sided", s["notes"] or "", re.I):
            ax.plot((s["x0"] + s["chainage"]) / 2000, 1 * (h + gap) - 0.08, marker="^", color="#222222", ms=3.5)
    ax.set_xlim(-0.2, end / 1000 + 0.2)
    ax.set_ylim(-0.25, len(rows) * (h + gap))
    ax.set_yticks([])
    ax.set_xlabel("Main-line chainage from intake (km)")
    ax.set_title("Figure 6.1  Survey attributes along the main line (May 2022)", loc="left", pad=8)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    legend = [Patch(color=FLOW_DRAW["Perennial"], label="Perennial"),
              Patch(color=FLOW_DRAW["Seasonal"], label="Seasonal"),
              Patch(color="#2E86AB", label="River water"),
              Patch(color="#7BAFD4", label="River + storm water"),
              Patch(color="#B5A1D3", label="Storm water"),
              Patch(color="#5C5C5C", label="Waste dumping"),
              Patch(color="#9C3D54", label="Sewage"),
              Patch(color="#8C6D46", label="Silting present"),
              Patch(color="#D9EAD3", label="Silting absent"),
              Patch(color="#4F6D8C", label="Lined"),
              Patch(color="#E6B8A2", label="Unlined"),
              Line2D([0], [0], marker="^", color="w", markerfacecolor="#222222", ms=6,
                     label="Note: lined on one side")]
    legend += [Patch(color=cond_color[c], label=f"Condition: {c}") for c in CONDITION_ORDER if c in cond_color]
    legend += [Patch(color=FLOW_DRAW["Not recorded"], label="Not recorded"),
               Patch(label="Not walked (CAD only)", **NOT_WALKED)]
    ax.legend(handles=legend, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=4, frameon=False,
              fontsize=6.8)
    fig.text(0.01, 0.01, "Source: site/data.js (May 2022 survey). Condition: Lost = canal not seen; "
             "Critical = sewage or waste and silting; Poor = sewage or waste; Fair = silting; Good otherwise.",
             fontsize=6.5, color="#666666", style="italic")
    fig.subplots_adjust(bottom=0.36, top=0.92, left=0.13, right=0.98)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Diagram helpers (Figures 2.1, 4.1, 9.1, 10.1)
# ---------------------------------------------------------------------------

WATER = "#DCEBF7"      # water components
LAND = "#EFEBE3"       # land / institutions
STATUS = "#9C3D54"     # current-status notes (text + left rule)
INK = "#222222"
MUTED = "#666666"


def _box(ax, x, y, w, h, title, body=None, fc=LAND, ec="#888888", title_size=8.5, body_size=7.2,
         status=None, lw=0.8):
    """Rounded box with a bold title, optional body text and optional status line (data coords)."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2",
                                fc=fc, ec=ec, lw=lw, zorder=2))
    ax.text(x + w / 2, y + h - 1.4, title, ha="center", va="top", fontsize=title_size,
            fontweight="bold", color=ACCENT, zorder=3, wrap=True)
    if body:
        ax.text(x + w / 2, y + h - 1.4 - title_size * 0.45, body, ha="center", va="top",
                fontsize=body_size, color=INK, zorder=3, linespacing=1.25)
    if status:
        ax.text(x + w / 2, y + 1.0, status, ha="center", va="bottom", fontsize=body_size - 0.4,
                color=STATUS, style="italic", zorder=3, linespacing=1.2)


def _arrow(ax, p0, p1, label=None, color=ACCENT, style="-|>", ls="-", lw=1.4, label_offset=(0, 1.2),
           label_size=7.0, rad=0.0, ha="center"):
    ax.annotate("", xy=p1, xytext=p0, zorder=1,
                arrowprops=dict(arrowstyle=style, color=color, lw=lw, ls=ls, shrinkA=2, shrinkB=2,
                                connectionstyle=f"arc3,rad={rad}", mutation_scale=12))
    if label:
        mx, my = (p0[0] + p1[0]) / 2 + label_offset[0], (p0[1] + p1[1]) / 2 + label_offset[1]
        ax.text(mx, my, label, ha=ha, va="center", fontsize=label_size, color=color, style="italic",
                zorder=4, bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.9))


def _diagram_axes(figsize, title):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")
    ax.set_title(title, loc="left", pad=6)
    return fig, ax


# ---------------------------------------------------------------------------
# Figure 2.1 — Integrated hydraulic system schematic
# ---------------------------------------------------------------------------

def fig_2_1_system(sections):
    out = OUT_DIR / "fig_2_1_system_schematic.png"
    main = [s for s in sections if s["on_main"]]
    per_end = max(s["chainage"] for s in main if s["flow"] == "Perennial")
    # same basis as the report (§6.1, Table 6.1): every section with a record, branches included
    below = [s for s in sections if s["x0"] is not None and s["x0"] >= 3441 and s["wq_list"]]
    below_sew = sum(1 for s in below if {"Sewage", "Waste Dumping"} & set(s["wq_list"]))

    fig, ax = _diagram_axes((9.0, 6.0), "Figure 2.1  The rajkulo–pokhari–aquifer–hiti system and the "
                                        "Tikabhairab Rajkulo's place in it")
    # Surface chain (top row)
    _box(ax, 1, 40, 21, 15, "Intake", "Tikabhairav, on the Lele Khola\n1,477.16 m ASL",
         fc=WATER, status="weir silted; sluice gate\nnon-functional (§4.4)")
    _box(ax, 30, 40, 33, 15, "Rajkulo (canal)",
         "Chapagaon → Pyangaon → Thecho →\nSunakothi → Dholahiti\n11.8 km main line",
         fc=WATER, status=f"May 2022: perennial flow only to {per_end / 1000:.1f} km;\n"
                          f"sewage or waste in {below_sew} of {len(below)} sections below 3.4 km")
    _box(ax, 71, 40, 27, 15, "Pokhari", "Saptapatal Pokhari, Lagankhel\n1,314.02 m ASL",
         fc=WATER, status="water level declined sharply\nover two decades (§1.3)")
    # Fields, aquifer, hiti
    _box(ax, 30, 19, 21, 13, "Command-area fields", "irrigated along the canal",
         status="largely converted to\nhousing plots (§1.1)")
    _box(ax, 58, 19, 40, 13, "Shallow aquifer", "beneath southern Lalitpur and the historic core",
         fc="#E4EEF4", status="groundwater levels falling (§1.3)")
    _box(ax, 58, 2, 40, 12, "Hiti network", "stone spouts of historic Lalitpur",
         fc=WATER, status="running thin or dry (§1.1)")

    _arrow(ax, (22.8, 48), (29.2, 48), "abstraction")
    _arrow(ax, (63.8, 48), (70.2, 48), "surface\nflow", label_offset=(0, 2.6))
    _arrow(ax, (40.5, 39.4), (40.5, 32.6), "irrigation", label_offset=(4.8, 0))
    _arrow(ax, (84.5, 39.4), (84.5, 32.6), "infiltration", label_offset=(5.3, 0))
    _arrow(ax, (52, 39.4), (62, 32.6), "bed seepage", ls="--", label_offset=(3.2, 0.8))
    _arrow(ax, (78, 18.4), (78, 14.6), "spring discharge\nat the spouts", label_offset=(9.0, 0))

    # Elevation difference
    ax.annotate("", xy=(3, 22), xytext=(3, 38.5),
                arrowprops=dict(arrowstyle="<->", color=MUTED, lw=0.9))
    ax.text(5, 30.2, "163.14 m between\nintake and pokhari\n(DoI 2020 benchmarks;\nthe fall along the\ncanal was not\nmeasured)",
            fontsize=6.8, color=MUTED, va="center", ha="left")

    # Failure-propagation chain
    ax.text(2.0, 12.5, "Failure propagates down the chain;\nrestoration propagates the same way (§2.1):",
            fontsize=7.2, color=INK, ha="left", va="center", style="italic")
    ax.text(2.0, 6.0, "Canal fails  →  pokhari drains  →\naquifer recharge falls  →  hiti run dry",
            fontsize=7.6, color="white", ha="left", va="center", fontweight="bold", linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.5", fc=STATUS, ec="none"))
    fig.text(0.01, 0.01, "Schematic; not to scale. Status notes summarise this report's sections cited. "
             "Survey figures: site/data.js.", fontsize=6.5, color=MUTED, style="italic")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.04)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Figure 4.1 — Intake structure: schematic long-section + photographs
# ---------------------------------------------------------------------------

INTAKE_PHOTOS = [
    ("JPEG_20220504_094539_9008845450522188938.jpg", "(a) Weir on the Lele Khola"),
    ("JPEG_20220504_094553_7735043035280737894.jpg", "(b) Masonry head basin below the weir"),
    ("JPEG_20220504_094611_4216377242552589911.jpg", "(c) Canal leaving the head basin (section 1)"),
]


def fig_4_1_intake(sections, photo_dirs):
    from PIL import Image, ImageOps
    out = OUT_DIR / "fig_4_1_intake_schematic.png"
    by_pdf = {s["pdf_n"]: s for s in sections}
    s1 = by_pdf[1]
    first6 = [by_pdf[n] for n in (1, 5, 2, 3, 4, 6)]
    end6 = max(s["chainage"] for s in first6)

    fig = plt.figure(figsize=(9.0, 7.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.35, 1.0], hspace=0.12, wspace=0.04)
    ax = fig.add_subplot(gs[0, :])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 42)
    ax.axis("off")
    ax.set_title("Figure 4.1  Intake structure at Tikabhairav: current state (schematic long-section and "
                 "photographs, 4 May 2022)", loc="left", pad=6)

    # ground / river bed
    ax.fill_between([0, 24], [6, 6], [0, 0], color="#C9BBA4", zorder=1)
    ax.fill_between([24, 100], [9, 7], [0, 0], color="#C9BBA4", zorder=1)
    # sediment wedge upstream of the weir, filled to the crest
    ax.fill_between([2, 22], [8, 15.5], [6, 6], color="#A6845C", hatch="..", ec="#7A6040", lw=0, zorder=2)
    # water over the sediment and spilling over the weir
    ax.fill_between([2, 22], [17.5, 17.5], [8, 15.5], color="#BFD9EE", alpha=0.9, zorder=2)
    ax.plot([2, 22, 25.5], [17.5, 17.5, 9.5], color="#3B7DB8", lw=1.2, zorder=3)
    # weir
    ax.add_patch(Rectangle((22, 6), 3, 10, fc="#8C8C8C", ec="#555555", lw=0.8, zorder=3))
    ax.text(23.5, 3.5, "weir", ha="center", fontsize=7.5, color=INK)
    # head basin + gate
    ax.add_patch(Rectangle((30, 8.5), 12, 1.0, fc="#8C8C8C", ec="#555555", lw=0.6, zorder=3))
    ax.fill_between([30, 42], [13, 13], [9.5, 9.5], color="#BFD9EE", zorder=2)
    ax.add_patch(Rectangle((42, 8.5), 1.4, 14, fc="#4A4A4A", ec="#222222", lw=0.8, zorder=4))
    ax.plot([41.2, 44.2], [22.5, 22.5], color="#222222", lw=1.2, zorder=4)
    ax.text(36, 15.2, "head basin", ha="center", fontsize=7.5, color=INK)
    # canal with silt layer thinning downstream
    xs = np.linspace(43.4, 98, 40)
    bed = 8.5 - (xs - 43.4) * 0.02
    silt = bed + np.interp(xs, [43.4, 60, 98], [4.5, 3.0, 1.2])
    ax.fill_between(xs, silt, bed, color="#A6845C", hatch="..", ec="#7A6040", lw=0, zorder=2)
    ax.fill_between(xs, silt + 1.6, silt, color="#BFD9EE", alpha=0.9, zorder=2)
    ax.plot(xs, silt + 1.6, color="#3B7DB8", lw=1.0, ls="--", zorder=3)
    ax.plot(xs, bed, color="#555555", lw=0.8, zorder=3)

    # annotations
    ax.annotate("weir filled with sediment to a depth\nrestricting passive flow (§4.4)", xy=(12, 11.5),
                xytext=(1, 29), fontsize=7.2, color=STATUS,
                arrowprops=dict(arrowstyle="-", color=STATUS, lw=0.7))
    ax.annotate("sluice gate: non-functional, cannot regulate flow;\nfailure mode not visible in the photographs",
                xy=(43.4, 21), xytext=(30, 35), fontsize=7.2, color=STATUS,
                arrowprops=dict(arrowstyle="-", color=STATUS, lw=0.7))
    ax.annotate("silt reported 1.5–2.0 m deep\nimmediately downstream, decreasing\ndownstream (survey team, §4.4)",
                xy=(52, 11), xytext=(50, 24), fontsize=7.2, color=STATUS,
                arrowprops=dict(arrowstyle="-", color=STATUS, lw=0.7))
    ax.text(70, 14.8, "water surface (turbid flow, May 2022)", fontsize=6.8, color="#3B7DB8", style="italic")
    ax.annotate("", xy=(98, 3), xytext=(43.4, 3), arrowprops=dict(arrowstyle="<->", color=MUTED, lw=0.8))
    ax.text(70.7, 4.2, f"first {end6:.0f} m of canal: sections 1 → 5 (hume pipe Ø {by_pdf[5]['diam'].split('.')[0]} cm)"
            f" → 2 → 3 → 4 → 6;\nsilting recorded in all six", ha="center", va="bottom", fontsize=6.8,
            color=INK)

    # inset: recorded cross-section of section 1
    ins = ax.inset_axes([0.80, 0.50, 0.17, 0.34])
    w, h = float(s1["width"]) / 100, float(s1["height"]) / 100
    ins.add_patch(Rectangle((-0.12, -0.08), 0.12, h + 0.08, fc="#9A9A9A", ec="#555555", lw=0.6))
    ins.add_patch(Rectangle((w, -0.08), 0.12, h + 0.08, fc="#9A9A9A", ec="#555555", lw=0.6))
    ins.add_patch(Rectangle((-0.12, -0.08), w + 0.24, 0.08, fc="#9A9A9A", ec="#555555", lw=0.6))
    ins.add_patch(Rectangle((0, 0), w, h * 0.3, fc="#A6845C", hatch="..", ec="#7A6040", lw=0))
    ins.add_patch(Rectangle((0, h * 0.3), w, h * 0.35, fc="#BFD9EE", ec="none"))
    ins.set_xlim(-0.2, w + 0.2)
    ins.set_ylim(-0.15, h + 0.25)
    ins.set_aspect("equal")
    ins.axis("off")
    ins.set_title(f"Section 1 as recorded:\n{w * 100:.0f} cm × {h * 100:.0f} cm, silting present",
                  fontsize=6.6, color=INK, pad=2)

    # photographs
    for i, (name, cap) in enumerate(INTAKE_PHOTOS):
        pax = fig.add_subplot(gs[1, i])
        pax.axis("off")
        f = next((d / name for d in photo_dirs if (d / name).exists()), None)
        if f is None:
            pax.text(0.5, 0.5, f"photo not found:\n{name}", ha="center", va="center", fontsize=6, color=MUTED)
            continue
        im = ImageOps.exif_transpose(Image.open(f))
        im.thumbnail((900, 900))
        pax.imshow(im)
        pax.set_title(cap, fontsize=7.4, color=INK, pad=3)
    fig.text(0.01, 0.01, "Long-section is schematic and not to scale; depths are as reported in §4.4. "
             "Photographs: survey record for section 1 (Intake).", fontsize=6.5, color=MUTED, style="italic")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.04)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Figure 9.1 — Stakeholder relationship diagram
# ---------------------------------------------------------------------------

def fig_9_1_stakeholders():
    out = OUT_DIR / "fig_9_1_stakeholders.png"
    fig, ax = _diagram_axes((9.0, 6.4), "Figure 9.1  Proposed institutional arrangement: the Tikabhairab "
                                        "Rajkulo Trust and its sub-functions")
    from matplotlib.patches import Ellipse
    # x and y data units differ in physical size; scale the y radius so the hub draws as a circle
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.02)
    bb = ax.get_position()
    k = (60 / (bb.height * fig.get_figheight())) / (100 / (bb.width * fig.get_figwidth()))
    cx_, cy_ = 26, 30
    ax.add_patch(Ellipse((cx_, cy_), 15, 15 * k, fc=ACCENT, ec="none", zorder=3))
    ax.text(cx_, cy_, "Tikabhairab\nRajkulo Trust\n(steering body)", ha="center", va="center",
            fontsize=8.2, color="white", fontweight="bold", zorder=4)
    members = [
        ("GM", "Godavari Municipality", "rotating chair", 90),
        ("LMC", "Lalitpur Metropolitan City", "rotating chair", 30),
        ("DoI", "Department of Irrigation", "technical secretariat", -30),
        ("DoA", "Department of Archaeology", "observer", -90),
        ("CIUD", "CIUD", "ex-officio", -150),
        ("WUA", "Water Users' Association", "ex-officio", 150),
    ]
    for key, name, role, ang in members:
        ux, uy = np.cos(np.radians(ang)), np.sin(np.radians(ang)) * k
        x, y = cx_ + 18 * ux, cy_ + 18 * uy
        ax.plot([cx_ + 7.5 * ux, cx_ + 14.8 * ux], [cy_ + 7.5 * uy, cy_ + 14.8 * uy],
                color=ACCENT, lw=1.2, zorder=1)
        ax.text(x, y + 0.6, key, ha="center", va="center", fontsize=8.6, fontweight="bold", color=ACCENT,
                zorder=4, bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=ACCENT, lw=0.9))
        ry = y + 3.9 if uy > 0.01 else y - 2.6      # role on the outward side, clear of the spoke
        ax.text(x, ry, role, ha="center", va="center", fontsize=6.8, color=INK, style="italic", zorder=5)
    # sub-function cluster
    subs = [
        ("Technical — lead: DoI", "Technical secretariat: technical standards,\ndesign oversight, contractor "
                                  "management,\nengineering documentation and the\ntotal-station survey (§12.1)", 44),
        ("Legal corridor protection — lead: DoA, GM, LMC",
         "DoA heritage classification of the corridor;\nbuffer-zone enforcement by GM and LMC;\n"
         "land-acquisition mechanism for existing\nencroachments", 25),
        ("Community stewardship — lead: WUA", "Ward-based membership; maintenance from\noperational handover; "
                                              "re-established\npre-monsoon cleaning (§9.4)", 6),
    ]
    for title, body, y in subs:
        _box(ax, 56, y, 42, 12.5, title, body, fc=LAND, body_size=7.0, title_size=8.0)
    ax.text(77, 59, "Sub-functions (§9.5)", ha="center", va="top", fontsize=8.2, color=INK, fontweight="bold")
    ax.text(1, 2.2, "Other stakeholders (Table 9.1): DUDBC; NEA / KUKL; Saptapatal Pokhari Trust / Guthi; affected "
            "landowners and businesses;\ncommunities along the alignment; NOA, Seattle; donor community.",
            fontsize=6.8, color=MUTED, ha="left", va="bottom")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.02)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Figure 10.1 — Phase sequencing (indicative Gantt)
# ---------------------------------------------------------------------------

def fig_10_1_phasing():
    out = OUT_DIR / "fig_10_1_phasing.png"
    P = 1.5      # indicative, equal phase length (report gives only a 5–8 year horizon)
    t0 = 1.0     # Phase 1 start, after the institutional preconditions
    rows = [
        ("Institutional preconditions\n(Trust, corridor status, WUA)", 0.0, t0, "#8FA9C4", None),
        ("Total-station survey (§12.1)", 0.0, 0.4, "#8FA9C4", None),
        ("Phase 1 — Foundational works", t0, t0 + P, "#1F4E79", "intake operational"),
        ("Phase 2 — Sewage interception", t0 + P, t0 + 2 * P, "#1F4E79", "water quality acceptable\nfor urban reach"),
        ("Phase 3 — Urban reach reconstruction", t0 + 2 * P, t0 + 3 * P, "#1F4E79", "inflow meets pond-\nreceivable standard"),
        ("Phase 4 — Terminus and pond integration", t0 + 3 * P, t0 + 4 * P, "#1F4E79", None),
    ]
    cross = ["Legal corridor protection", "WUA formation and capacity building", "Community engagement",
             "Monitoring and evaluation", "Research follow-up (§12)"]
    end = t0 + 4 * P
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    n = len(rows) + len(cross)
    ys = {}
    for i, (lab, a, b, col, _) in enumerate(rows):
        y = n - i
        ys[i] = y
        ax.barh(y, b - a, left=a, height=0.56, color=col, edgecolor="white")
        ax.text(-0.1, y, lab, ha="right", va="center", fontsize=7.6, color=INK)
    for i in range(2, len(rows) - 1):
        a, b, gate = rows[i][2], rows[i + 1][1], rows[i][4]
        ax.annotate("", xy=(b + 0.02, ys[i + 1] + 0.3), xytext=(b - 0.02, ys[i] - 0.3),
                    arrowprops=dict(arrowstyle="-|>", color=STATUS, lw=0.9, mutation_scale=9))
        ax.text(b + 0.12, (ys[i] + ys[i + 1]) / 2 + 0.05, gate, fontsize=6.3, color=STATUS, style="italic",
                va="center", ha="left")
    ax.annotate("", xy=(t0 - 0.02, ys[2] + 0.3), xytext=(t0 - 0.02, ys[0] - 0.3),
                arrowprops=dict(arrowstyle="-|>", color=STATUS, lw=0.9, mutation_scale=9))
    for j, lab in enumerate(cross):
        y = n - len(rows) - j
        ax.barh(y, end + 0.8, left=0, height=0.42, color="#C9D6E3", edgecolor="white")
        ax.annotate("", xy=(end + 1.25, y), xytext=(end + 0.75, y),
                    arrowprops=dict(arrowstyle="-|>", color="#8FA9C4", lw=1.2))
        ax.text(-0.1, y, lab, ha="right", va="center", fontsize=7.3, color=INK, style="italic")
    yb = 0.0
    ax.annotate("", xy=(t0 + 5, yb), xytext=(t0, yb), arrowprops=dict(arrowstyle="-", color=MUTED, lw=2.2))
    ax.annotate("", xy=(t0 + 8, yb), xytext=(t0 + 5, yb), arrowprops=dict(arrowstyle="-", color=MUTED, lw=2.2,
                                                                          ls=":"))
    ax.text(t0 + 4.0, yb + 0.35, "Phase 1 start to Phase 4 completion: 5–8 years (working horizon, §10.1)",
            fontsize=7.0, color=MUTED, ha="center", va="bottom")
    ax.axhline(n - len(rows) + 0.5, color="#DDDDDD", lw=0.8)
    ax.text(end + 1.3, n - len(rows) - 2, "cross-cutting:\ncontinuous, and\nbeyond Phase 4", fontsize=6.6,
            color=MUTED, va="center")
    ax.set_xlim(0, t0 + 8.4)
    ax.set_ylim(-0.6, n + 0.7)
    ax.set_yticks([])
    ax.set_xticks(range(0, int(t0 + 9)))
    ax.set_xlabel("Project years (indicative)")
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.set_title("Figure 10.1  Phase sequencing and dependencies", loc="left", pad=8)
    fig.text(0.01, 0.01, "Phase bars are indicative and drawn equal: the report fixes the order and dependencies "
             "(Table 10.1), not phase durations. Arrows: a phase starts only when the previous gate is met.",
             fontsize=6.5, color=MUTED, style="italic")
    fig.subplots_adjust(left=0.30, right=0.97, top=0.92, bottom=0.17)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Maps — alignment overview, contamination, priority
# ---------------------------------------------------------------------------

def _setup_map_axis(survey, canal, fig_w=11.0, fig_h=10.5):
    """Returns (fig, map_ax, legend_ax). Legend lives in its own subplot on the right
    so it never overlaps the map data."""
    fig = plt.figure(figsize=(fig_w, fig_h))
    gs = fig.add_gridspec(1, 2, width_ratios=[3, 1], wspace=0.02)
    ax = fig.add_subplot(gs[0, 0])
    lax = fig.add_subplot(gs[0, 1])
    lax.axis("off")

    minx, miny, maxx, maxy = canal.total_bounds
    pad = 0.05 * max(maxx - minx, maxy - miny)
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("#888888")
        spine.set_linewidth(0.6)
    return fig, ax, lax


def _add_settlement_labels(ax, locations):
    # Whitelist of canal-corridor settlements with explicit label-offset positions
    # to avoid the top-cluster overlap problem.
    # Offset is (dx, dy) in points — positive dx = right, positive dy = up.
    keep = {
        "टिकाभैरव मन्दिर": ("Tikabhairav (intake)", (8, -2)),
        "प्यांग गाउँ":     ("Pyangaon",             (8, 0)),
        "थेच्व":           ("Thecho",               (8, 0)),
        "धोंलाहिति":       ("Dholahiti",            (8, 0)),
        "जावलाखेल":        ("Jawalakhel",           (-50, 8)),
        "पुल्चोक":         ("Pulchowk",             (8, -10)),
        "पाटन ढोका":       ("Patan Dhoka",          (8, 4)),
        "ग्वार्को":         ("Gwarko",               (8, -4)),
        "नखु खोला":        ("Nakhu Khola",          (-65, 2)),
    }
    for _, row in locations.iterrows():
        name = row["Location"]
        if name in keep:
            label, (dx, dy) = keep[name]
            x, y = row.geometry.x, row.geometry.y
            ax.plot(x, y, marker="s", color="white", markeredgecolor=ACCENT,
                    markersize=4, markeredgewidth=1.0, zorder=8)
            ax.annotate(label, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                        fontsize=7.5, color=ACCENT, fontweight="bold", zorder=9,
                        path_effects=[pe.withStroke(linewidth=2.4, foreground="white")])


def map_4_1_alignment(survey, canal, main, branches, pois, locations):
    """main = surveyed-seen sections (Cseen='Yes'), drawn in BLUE.
    branches = the full Canal reference layer, drawn in light ORANGE behind."""
    out = OUT_DIR / "map_4_1_alignment.png"
    fig, ax, lax = _setup_map_axis(survey, canal)

    used_basemap = try_add_basemap(ax, cx.providers.Esri.WorldImagery if HAS_BASEMAP else None)

    # Orange reference network (Canal layer) behind everything
    branches.plot(ax=ax, color="white", linewidth=2.4, alpha=0.55, zorder=3)
    branches.plot(ax=ax, color="#F7801E", linewidth=1.4, alpha=0.85, zorder=4)
    # Blue surveyed canal (Cseen='Yes') on top
    main.plot(ax=ax, color="white", linewidth=4.0, alpha=0.85, zorder=5)
    main.plot(ax=ax, color="#6190D3", linewidth=2.6, alpha=1.0, zorder=6)

    pois.plot(ax=ax, color="#DB1E2A", markersize=14, edgecolor="white", linewidth=0.6,
              zorder=8, alpha=0.95)

    _add_settlement_labels(ax, locations)

    ax.set_title("Map 4.1  Tikabhairab Rajkulo alignment and points of interest",
                 loc="left", pad=10, color=ACCENT, fontsize=11, fontweight="bold")

    legend_elems = [
        Line2D([0], [0], color="#6190D3", lw=2.6, label="Surveyed canal (May 2022, all sections)"),
        Line2D([0], [0], color="#F7801E", lw=1.4, label="Reference network (orange, all canals)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#DB1E2A", markeredgecolor="white",
               markersize=7, label=f"Points of interest (n = {len(pois)})"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="white", markeredgecolor=ACCENT,
               markersize=6, markeredgewidth=1.0, label="Named settlements"),
    ]
    lax.legend(handles=legend_elems, loc="upper left", fontsize=8.5, framealpha=1.0,
               title="Legend", title_fontsize=9, edgecolor="#888888",
               bbox_to_anchor=(0.0, 0.95))

    add_north_arrow(ax)
    add_scalebar(ax, length_m=2000, label="2 km")

    attrib = "Imagery: Esri World Imagery. " if used_basemap else ""
    fig.text(0.99, 0.01,
             f"{attrib}Data: GPS field survey May 2022; coordinates WGS 84 UTM 45N.",
             ha="right", va="bottom", fontsize=6.5, color="#666666", style="italic")
    fig.subplots_adjust(bottom=0.04, top=0.93, left=0.02, right=0.99)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


def _category_for_quality_set(qset):
    """Map a set of quality codes to a categorical label and colour."""
    if not qset:
        return "Underground / not observed", "#cccccc"
    if qset == {1}:
        return "River quality only", "#2E86AB"
    if 3 in qset and 4 in qset:
        return "Sewage + storm + waste", "#9C3D54"
    if 3 in qset:
        return "Sewage, no waste dumping", "#C56A5C"
    if 1 in qset and 2 in qset and len(qset) == 2:
        return "River + storm water", "#7BAFD4"
    if qset == {2}:
        return "Storm water only", "#F4D35E"
    return "Mixed contamination", "#888888"


def map_5_1_contamination(survey, canal, main, branches, locations):
    out = OUT_DIR / "map_5_1_contamination.png"
    fig, ax, lax = _setup_map_axis(survey, canal)

    used_basemap = try_add_basemap(ax, cx.providers.Esri.WorldGrayCanvas if HAS_BASEMAP else None)

    # Orange reference network in background
    branches.plot(ax=ax, color="#F7801E", linewidth=1.0, alpha=0.55, zorder=3)
    # Halo behind surveyed sections so they read clearly against the basemap
    main.plot(ax=ax, color="white", linewidth=4.4, alpha=0.8, zorder=4)

    # Colour ALL surveyed sections by water quality (continuous canal)
    survey_q = survey.copy()
    survey_q["qset"] = survey_q["WaterQuality"].apply(decode_quality)
    survey_q[["q_label", "q_color"]] = survey_q["qset"].apply(
        lambda s: pd.Series(_category_for_quality_set(s))
    )
    for label, color in survey_q.groupby("q_label")["q_color"].first().items():
        survey_q[survey_q["q_label"] == label].plot(
            ax=ax, color=color, linewidth=2.8, zorder=6, capstyle="round"
        )

    _add_settlement_labels(ax, locations)

    ax.set_title("Map 5.1  Water quality along the canal alignment (May 2022 survey)",
                 loc="left", pad=10, color=ACCENT, fontsize=11, fontweight="bold")

    legend_elems = [
        Patch(facecolor="#2E86AB", label="River quality only"),
        Patch(facecolor="#7BAFD4", label="River quality + storm water"),
        Patch(facecolor="#F4D35E", label="Storm water only"),
        Patch(facecolor="#C56A5C", label="Sewage, no waste dumping"),
        Patch(facecolor="#9C3D54", label="Sewage + storm + waste"),
        Patch(facecolor="#888888", label="Mixed / other"),
        Patch(facecolor="#cccccc", label="Not recorded (incl. canal not seen)"),
        Line2D([0], [0], color="#F7801E", lw=1.0, label="Reference network (orange, all canals)"),
    ]
    lax.legend(handles=legend_elems, loc="upper left", fontsize=8.5, framealpha=1.0,
               title="Water quality category", title_fontsize=9, edgecolor="#888888",
               bbox_to_anchor=(0.0, 0.95))

    add_north_arrow(ax)
    add_scalebar(ax, length_m=2000, label="2 km")
    attrib = "Basemap: Esri World Gray Canvas. " if used_basemap else ""
    fig.text(0.99, 0.01,
             f"{attrib}Survey: Survey_new Cseen='Yes' sections, multi-select water-quality classification.",
             ha="right", va="bottom", fontsize=6.5, color="#666666", style="italic")
    fig.subplots_adjust(bottom=0.04, top=0.93, left=0.02, right=0.99)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


def map_8_1_priority(survey, canal, main, branches, locations, sections, bands):
    """Restoration priority map. Each surveyed section is coloured by the band of its
    main-line chainage (from site/data.js via the Mergin fid); bands from priority_bands()."""
    out = OUT_DIR / "map_8_1_priority.png"
    fig, ax, lax = _setup_map_axis(survey, canal)

    # OpenStreetMap's own tile servers refuse this client ("Access blocked") and CARTO now
    # needs an API key, so use Esri's light grey canvas (Map 4.1 uses Esri imagery).
    used_basemap = try_add_basemap(ax, cx.providers.Esri.WorldGrayCanvas if HAS_BASEMAP else None)

    color_map = {"CRITICAL": PRIORITY_COLORS["Critical"],
                 "HIGH": PRIORITY_COLORS["High"],
                 "MEDIUM": PRIORITY_COLORS["Medium"],
                 "LOW": PRIORITY_COLORS["Low"],
                 None: "#9A9A9A"}

    branches.plot(ax=ax, color="#F7801E", linewidth=1.0, alpha=0.55, zorder=3)
    main.plot(ax=ax, color="white", linewidth=4.5, alpha=0.8, zorder=4)

    mid_by_fid = {s["mergin_fid"]: (s["x0"] + s["chainage"]) / 2 for s in sections
                  if s["mergin_fid"] and s["on_main"] and s["chainage"] is not None}

    def tier_for(fid):
        x = mid_by_fid.get(fid)
        if x is None:
            return "BRANCH"
        for r in bands:
            if r["x0"] <= x < r["x1"] or (x == r["x1"] and r is bands[-1]):
                return r["tier"]
        return None

    survey_p = survey.copy()
    survey_p["tier"] = survey_p["fid"].apply(tier_for)
    survey_p[survey_p["tier"] == "BRANCH"].plot(ax=ax, color="#9A9A9A", linewidth=1.8, zorder=5)
    for tier in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
        sub = survey_p[survey_p["tier"] == tier]
        if not sub.empty:
            sub.plot(ax=ax, color=color_map[tier], linewidth=2.8, zorder=6, capstyle="round")

    _add_settlement_labels(ax, locations)

    ax.set_title("Map 8.1  Restoration priority by 1 km chainage band",
                 loc="left", pad=10, color=ACCENT, fontsize=11, fontweight="bold")

    legend_elems = []
    for tier, name in (("CRITICAL", "Critical"), ("HIGH", "High"), ("MEDIUM", "Medium"), ("LOW", "Low")):
        rng = _band_ranges(bands, tier)
        if rng:
            legend_elems.append(Patch(facecolor=PRIORITY_COLORS[name], label=f"{name} ({rng})"))
    legend_elems += [
        Line2D([0], [0], color="#9A9A9A", lw=1.8, label="Parallel branch (not scored)"),
        Line2D([0], [0], color="#F7801E", lw=1.0, label="Reference network (orange, all canals)"),
    ]
    lax.legend(handles=legend_elems, loc="upper left", fontsize=8.5, framealpha=1.0,
               title="Priority class (Table 8.1)", title_fontsize=9, edgecolor="#888888",
               bbox_to_anchor=(0.0, 0.95))

    add_north_arrow(ax)
    add_scalebar(ax, length_m=2000, label="2 km")
    attrib = "Basemap: Esri World Gray Canvas. " if used_basemap else ""
    fig.text(0.99, 0.01,
             f"{attrib}Scores computed from site/data.js (method §3.6). The canal beyond 9.65 km was not walked.",
             ha="right", va="bottom", fontsize=6.5, color="#666666", style="italic")
    fig.subplots_adjust(bottom=0.04, top=0.93, left=0.02, right=0.99)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_OUTPUTS = ("fig_2_1", "fig_4_1", "fig_5_1", "fig_6_1", "fig_9_1", "fig_10_1",
               "map_4_1", "map_5_1", "map_8_1")


def resolve_src(arg):
    for cand in (arg, os.environ.get("RAJKULO_SRC"), r"D:\Rajkulo All Documents",
                 str(Path.home() / "Downloads" / "Rajkulo All Documents")):
        if cand and Path(cand).exists():
            return Path(cand)
    sys.exit("Source folder not found: pass --src or set RAJKULO_SRC")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", help='Folder "Rajkulo All Documents" (default: $RAJKULO_SRC)')
    ap.add_argument("--only", help=f"comma-separated subset of {', '.join(ALL_OUTPUTS)}")
    args = ap.parse_args()
    wanted = set(args.only.split(",")) if args.only else set(ALL_OUTPUTS)

    print("Loading site/data.js...")
    sections, pois_js = load_survey_js()
    bands = priority_bands(sections, pois_js)
    print_priority_table(bands)

    if "fig_2_1" in wanted:
        print("\nGenerating Figure 2.1 (system schematic)...")
        fig_2_1_system(sections)
    if "fig_4_1" in wanted:
        print("Generating Figure 4.1 (intake schematic + photographs)...")
        site_photos = Path(__file__).resolve().parent.parent / "site" / "photos"
        photo_dirs = [site_photos / "large", site_photos / "thumbs"]
        try:
            photo_dirs.insert(0, resolve_src(args.src) / "Rajkulo All Documents" / "RajkuloSurvey" / "rajkulo_survey")
        except SystemExit:
            pass
        fig_4_1_intake(sections, photo_dirs)
    if "fig_9_1" in wanted:
        print("Generating Figure 9.1 (stakeholders)...")
        fig_9_1_stakeholders()
    if "fig_10_1" in wanted:
        print("Generating Figure 10.1 (phase sequencing)...")
        fig_10_1_phasing()
    if "fig_5_1" in wanted:
        print("Generating Figure 5.1 (flow regime and contamination)...")
        fig_5_1_flow_regime(sections, pois_js)
    if "fig_6_1" in wanted:
        print("Generating Figure 6.1 (survey attributes)...")
        fig_6_1_survey_attributes(sections, pois_js)

    if wanted & {"map_4_1", "map_5_1", "map_8_1"}:
        global GIS_DIR
        GIS_DIR = resolve_src(args.src) / "Mergin Maps Data" / "CANAL1"
        print(f"Loading GIS data from {GIS_DIR}...")
        survey, canal, main, branches, pois, locations, main_line = load_data()
        print(f"  Survey_new (clean): {len(survey)} sections; POIs: {len(pois)}")
        if "map_4_1" in wanted:
            print("Generating Map 4.1 (alignment overview)...")
            map_4_1_alignment(survey, canal, main, branches, pois, locations)
        if "map_5_1" in wanted:
            print("Generating Map 5.1 (water quality)...")
            map_5_1_contamination(survey, canal, main, branches, locations)
        if "map_8_1" in wanted:
            print("Generating Map 8.1 (restoration priority)...")
            map_8_1_priority(survey, canal, main, branches, locations, sections, bands)

    print(f"\nFigures written to {OUT_DIR}")


if __name__ == "__main__":
    main()
