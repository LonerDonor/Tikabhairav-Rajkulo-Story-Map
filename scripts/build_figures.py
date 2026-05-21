"""Generate the report's six data-driven figures from the May 2022 GPS survey.

Inputs:
  Mergin Maps GeoPackage layers (Survey_new, Canal, POIS, Location) in
  C:\\Users\\olenepal\\Downloads\\Rajkulo All Documents\\Mergin Maps Data\\CANAL1

Outputs:
  PNG files in Story map Tikabhairav/figures/, 300 DPI, ~18 cm wide.
"""

from __future__ import annotations

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

try:
    import contextily as cx
    HAS_BASEMAP = True
except Exception:
    HAS_BASEMAP = False

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

GIS_DIR = Path(r"C:\Users\olenepal\Downloads\Rajkulo All Documents\Mergin Maps Data\CANAL1")
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

# Two DoI benchmark elevations (m ASL)
H_INTAKE = 1477.16
H_TERMINUS = 1314.02
ALIGNMENT_LENGTH_M = 13158.2  # AutoCAD-refined main alignment (report Chapter 6)

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
    survey = gpd.read_file(GIS_DIR / "Syrvey.gpkg", layer="Survey_new").to_crs(UTM_CRS)
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


def compute_chainage(survey, main_line, locations=None):
    """Assign chainage (m) to each section using Y-coordinate normalisation.
    The canal runs generally south (intake) to north (terminus); Y of section
    midpoint is a robust monotonic proxy for along-canal distance, more
    reliable than projection onto the partial merged trunk."""
    survey = survey.copy()
    survey["mid_x"] = survey.geometry.apply(lambda g: section_midpoint(g).x)
    survey["mid_y"] = survey.geometry.apply(lambda g: section_midpoint(g).y)

    # Anchor min/max Y using intake and bounding extents to keep chainage stable
    if locations is not None:
        intake = locations[locations["Location"] == "टिकाभैरव मन्दिर"]
        if len(intake):
            y_min = intake.geometry.iloc[0].y
        else:
            y_min = survey["mid_y"].min()
    else:
        y_min = survey["mid_y"].min()
    y_max = survey["mid_y"].max()
    span = max(y_max - y_min, 1e-6)

    survey["chainage"] = ((survey["mid_y"] - y_min) / span) * ALIGNMENT_LENGTH_M
    survey["chainage"] = survey["chainage"].clip(lower=0, upper=ALIGNMENT_LENGTH_M)

    # length: use projected geometry length directly (UTM metres)
    survey["length_m"] = survey.geometry.length
    return survey, y_min, y_max


def poi_chainage(pois, y_min, y_max):
    span = max(y_max - y_min, 1e-6)
    pois = pois.copy()
    pois["chainage"] = ((pois.geometry.y - y_min) / span) * ALIGNMENT_LENGTH_M
    pois["chainage"] = pois["chainage"].clip(lower=0, upper=ALIGNMENT_LENGTH_M)
    return pois


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
# Figure 6.2 — Velocity vs Vc bar chart (no GIS)
# ---------------------------------------------------------------------------

def fig_6_2_velocity_bar():
    out = OUT_DIR / "fig_6_2_velocity_vc.png"
    materials = [
        ("Concrete\n(smooth)",        2.96, 1.97, "#1B9E77"),
        ("Brick\nmasonry",             2.37, 1.42, "#3FA9F5"),
        ("Stone\nmasonry",             1.77, 1.18, "#4F86C6"),
        ("Earth\n(unlined)",           1.42, 1.01, "#B58D3A"),
        ("Vegetated\nearth (poor)",    1.18, 0.79, "#7C7C3A"),
    ]
    Vc = 0.306  # Kennedy at D = 0.40 m

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    x = np.arange(len(materials))
    centers = np.array([(m[1] + m[2]) / 2 for m in materials])
    half = np.array([(m[1] - m[2]) / 2 for m in materials])
    colors = [m[3] for m in materials]

    ax.bar(x, height=2*half, bottom=centers - half, color=colors, edgecolor="#333333", linewidth=0.6)
    # max/min markers
    for xi, (_, vmax, vmin, _) in zip(x, materials):
        ax.plot([xi - 0.35, xi + 0.35], [vmax, vmax], color="#222222", lw=1.0)
        ax.plot([xi - 0.35, xi + 0.35], [vmin, vmin], color="#222222", lw=1.0)
        ax.text(xi, vmax + 0.05, f"{vmax:.2f}", ha="center", va="bottom", fontsize=7.5, color="#333333")
        ax.text(xi, vmin - 0.05, f"{vmin:.2f}", ha="center", va="top", fontsize=7.5, color="#333333")

    ax.axhline(Vc, color="#C0392B", lw=1.6, ls="--", zorder=3)
    ax.text(len(materials) - 0.5, Vc + 0.04, f"Kennedy's Vc = {Vc:.3f} m/s at D = 0.40 m",
            ha="right", va="bottom", color="#C0392B", fontsize=8, fontstyle="italic")

    ax.set_xticks(x, [m[0] for m in materials])
    ax.set_ylabel("Mean flow velocity V (m/s)")
    ax.set_ylim(0, 3.5)
    ax.set_title("Figure 6.2  Manning's velocity by lining material vs. Kennedy's critical velocity",
                 loc="left", pad=12)
    ax.grid(axis="y", lw=0.3, color="#cccccc")
    ax.set_axisbelow(True)

    # caption block
    fig.text(0.01, 0.005,
             "Velocities computed at the primary bed slope S = 0.01529 (1 in 65) and representative\n"
             "section w = 0.50 m, d = 0.40 m. Bars span the Manning's n range for each lining material.\n"
             "All materials clear Vc by a factor of 2.6 to 9.7.",
             ha="left", va="bottom", fontsize=7.5, color="#555555", fontstyle="italic")

    fig.subplots_adjust(bottom=0.20, top=0.88, left=0.10, right=0.97)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Figure 6.1 — Elevation profile
# ---------------------------------------------------------------------------

def fig_6_1_elevation_profile(pois_with_chainage, survey_with_chainage):
    out = OUT_DIR / "fig_6_1_elevation_profile.png"
    L = ALIGNMENT_LENGTH_M
    x = np.linspace(0, L, 200)
    y = H_INTAKE + (H_TERMINUS - H_INTAKE) * (x / L)

    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    # Filled band
    ax.fill_between(x / 1000, y, H_TERMINUS - 10, color="#E1EAF1", alpha=0.7, zorder=1)
    ax.plot(x / 1000, y, color=ACCENT, lw=2.0, zorder=3, label="Average bed (linear interpolation)")

    # POI markers
    for _, row in pois_with_chainage.iterrows():
        ch = row["chainage"]
        if not (0 <= ch <= L):
            continue
        yc = H_INTAKE + (H_TERMINUS - H_INTAKE) * (ch / L)
        ax.plot(ch / 1000, yc, "o", color="#C0392B", markersize=2.2, zorder=5, alpha=0.7)

    # Benchmark callouts
    ax.annotate(f"Intake\n{H_INTAKE:.2f} m ASL\n27.574° N, 85.318° E",
                xy=(0, H_INTAKE), xytext=(0.4, H_INTAKE + 8),
                fontsize=8, color=ACCENT,
                arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.6))
    ax.annotate(f"Terminus\n{H_TERMINUS:.2f} m ASL\n(Saptapatal Pokhari, Lagankhel)",
                xy=(L/1000, H_TERMINUS), xytext=(L/1000 - 3.5, H_TERMINUS + 8),
                fontsize=8, color=ACCENT,
                arrowprops=dict(arrowstyle="-", color=ACCENT, lw=0.6))

    # Mark the perennial-seasonal boundary at chainage 3+124 m
    boundary_ch = 3124 / 1000
    boundary_y = H_INTAKE + (H_TERMINUS - H_INTAKE) * (boundary_ch * 1000 / L)
    ax.axvline(boundary_ch, color="#888888", lw=0.8, ls="--", zorder=2)
    ax.text(boundary_ch + 0.1, H_INTAKE - 25, "Perennial → seasonal\ntransition (Ch 3+124)",
            fontsize=7.5, color="#555555", fontstyle="italic")

    ax.set_xlim(0, L / 1000 + 0.5)
    ax.set_ylim(H_TERMINUS - 15, H_INTAKE + 25)
    ax.set_xlabel("Chainage from intake (km)")
    ax.set_ylabel("Elevation (m ASL)")
    ax.set_title("Figure 6.1  Tikabhairab Rajkulo elevation profile (intake to terminus)",
                 loc="left", pad=12)
    ax.grid(lw=0.3, color="#cccccc")
    ax.set_axisbelow(True)

    # Legend / caveat
    legend_elems = [
        Line2D([0], [0], color=ACCENT, lw=2.0, label="Average bed (linear interpolation between DoI benchmarks)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#C0392B", markersize=5,
               label=f"Points of interest ({len(pois_with_chainage)})"),
    ]
    ax.legend(handles=legend_elems, loc="lower left", fontsize=7.5)

    fig.text(0.01, 0.005,
             "Caveat — Per-section bed slope cannot be determined from GPS altitude (±10–30 m vertical error). "
             "Profile is linearly interpolated between two fixed DoI 2020 benchmarks. "
             "Total-station survey is identified as priority follow-up (§12.1).",
             ha="left", va="bottom", fontsize=7, color="#777777", fontstyle="italic")

    fig.subplots_adjust(bottom=0.20, top=0.88, left=0.09, right=0.97)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Figure 5.1 — Longitudinal flow regime diagram
# ---------------------------------------------------------------------------

def fig_5_1_flow_regime(survey_with_chainage):
    out = OUT_DIR / "fig_5_1_flow_regime.png"
    L = ALIGNMENT_LENGTH_M
    df = survey_with_chainage.copy()
    # Map "Interupted" → "Disturbed" for readability; preserve original mapping
    flow_map = {"Perennial": "Perennial", "Seasonal": "Seasonal",
                "Interupted": "Disturbed", "Unknown": "Unknown"}
    df["flow_label"] = df["CWaterflow"].map(flow_map).fillna("Unknown")

    fig, ax = plt.subplots(figsize=(8.5, 2.8))
    bar_y = 1.0
    bar_h = 0.6
    # Plot each section as a horizontal coloured slab
    for _, row in df.iterrows():
        ch = row["chainage"]
        l_m = row["length_m"]
        color = FLOW_COLORS.get(row["flow_label"], "#cccccc")
        ax.add_patch(Rectangle((ch / 1000, bar_y), l_m / 1000, bar_h,
                                color=color, ec="white", lw=0.2))
    # Frame
    ax.add_patch(Rectangle((0, bar_y), L / 1000, bar_h, fill=False, ec="#444444", lw=0.8))

    # Chainage axis
    ax.set_xlim(-0.3, L / 1000 + 0.3)
    ax.set_ylim(0.2, 2.0)
    ax.set_xlabel("Chainage from intake (km)")
    ax.set_yticks([])
    ax.set_title("Figure 5.1  Longitudinal flow regime distribution along the main alignment",
                 loc="left", pad=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    # Settlement labels above
    settlements = [
        (0.0, "Tikabhairav"),
        (1.5, "Chapagaon"),
        (3.2, "Pyangaon"),
        (4.5, "Thecho"),
        (6.0, "Sunakothi"),
        (8.0, "Dholahiti"),
        (10.5, "Lagankhel"),
    ]
    for ch_km, name in settlements:
        ax.plot([ch_km, ch_km], [bar_y + bar_h, bar_y + bar_h + 0.15], color="#666666", lw=0.5)
        ax.text(ch_km, bar_y + bar_h + 0.20, name, ha="center", va="bottom",
                fontsize=7, color="#444444", rotation=0)

    # Mark perennial / sewage transition
    ax.axvline(3.124, color="#222222", lw=0.6, ls=":")
    ax.text(3.124, bar_y - 0.05, "Ch 3+124", fontsize=6.5, color="#222222",
            ha="center", va="top", rotation=0)

    # Legend
    legend_elems = [Patch(color=FLOW_COLORS[k], label=k) for k in ("Perennial", "Seasonal", "Disturbed", "Unknown")]
    ax.legend(handles=legend_elems, loc="upper center", bbox_to_anchor=(0.5, -0.30),
              ncol=4, frameon=False)

    fig.subplots_adjust(bottom=0.35, top=0.78, left=0.04, right=0.98)
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
        return "Sewage + storm water", "#C56A5C"
    if 1 in qset and 2 in qset and len(qset) == 2:
        return "River + storm water", "#7BAFD4"
    if qset == {2}:
        return "Storm water only", "#F4D35E"
    return "Mixed contamination", "#888888"


def map_5_1_contamination(survey, canal, main, branches, locations):
    out = OUT_DIR / "map_5_1_contamination.png"
    fig, ax, lax = _setup_map_axis(survey, canal)

    used_basemap = try_add_basemap(ax, cx.providers.OpenStreetMap.Mapnik if HAS_BASEMAP else None)

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
        Patch(facecolor="#C56A5C", label="Sewage + storm water"),
        Patch(facecolor="#9C3D54", label="Sewage + storm + waste"),
        Patch(facecolor="#888888", label="Mixed / other"),
        Line2D([0], [0], color="#F7801E", lw=1.0, label="Reference network (orange, all canals)"),
    ]
    lax.legend(handles=legend_elems, loc="upper left", fontsize=8.5, framealpha=1.0,
               title="Water quality category", title_fontsize=9, edgecolor="#888888",
               bbox_to_anchor=(0.0, 0.95))

    add_north_arrow(ax)
    add_scalebar(ax, length_m=2000, label="2 km")
    attrib = "Basemap: OpenStreetMap contributors. " if used_basemap else ""
    fig.text(0.99, 0.01,
             f"{attrib}Survey: Survey_new Cseen='Yes' sections, multi-select water-quality classification.",
             ha="right", va="bottom", fontsize=6.5, color="#666666", style="italic")
    fig.subplots_adjust(bottom=0.04, top=0.93, left=0.02, right=0.99)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


def map_8_1_priority(survey, canal, main, branches, locations):
    """Restoration priority map — uses the band scores from Chapter 8 Table 8.1."""
    out = OUT_DIR / "map_8_1_priority.png"
    fig, ax, lax = _setup_map_axis(survey, canal)

    used_basemap = try_add_basemap(ax, cx.providers.OpenStreetMap.Mapnik if HAS_BASEMAP else None)

    band_priority = {
        (0, 1): "MEDIUM", (1, 2): "LOW", (2, 3): "MEDIUM",
        (3, 4): "HIGH", (4, 5): "HIGH",
        (5, 6): "CRITICAL", (6, 7): "CRITICAL",
        (7, 8): "MEDIUM", (8, 9): "HIGH",
        (9, 10): "MEDIUM", (10, 11): "HIGH",
    }
    color_map = {"CRITICAL": PRIORITY_COLORS["Critical"],
                 "HIGH": PRIORITY_COLORS["High"],
                 "MEDIUM": PRIORITY_COLORS["Medium"],
                 "LOW": PRIORITY_COLORS["Low"]}

    # Orange reference behind
    branches.plot(ax=ax, color="#F7801E", linewidth=1.0, alpha=0.55, zorder=3)
    main.plot(ax=ax, color="white", linewidth=4.5, alpha=0.8, zorder=4)

    def pri_for(ch):
        km = ch / 1000.0
        for (lo, hi), pri in band_priority.items():
            if lo <= km < hi:
                return pri
        return "MEDIUM"

    # Colour ALL surveyed sections by priority (continuous canal)
    survey_p = survey.copy()
    survey_p["priority"] = survey_p["chainage"].apply(pri_for)
    survey_p["color"] = survey_p["priority"].map(color_map)
    for pri, color in [("LOW", PRIORITY_COLORS["Low"]),
                        ("MEDIUM", PRIORITY_COLORS["Medium"]),
                        ("HIGH", PRIORITY_COLORS["High"]),
                        ("CRITICAL", PRIORITY_COLORS["Critical"])]:
        sub = survey_p[survey_p["priority"] == pri]
        if not sub.empty:
            sub.plot(ax=ax, color=color, linewidth=2.8, zorder=6, capstyle="round")

    _add_settlement_labels(ax, locations)

    ax.set_title("Map 8.1  Restoration priority by 1 km chainage band",
                 loc="left", pad=10, color=ACCENT, fontsize=11, fontweight="bold")

    legend_elems = [
        Patch(facecolor=PRIORITY_COLORS["Critical"], label="Critical (5–7 km)"),
        Patch(facecolor=PRIORITY_COLORS["High"], label="High (3–5, 8–9, 10–11 km)"),
        Patch(facecolor=PRIORITY_COLORS["Medium"], label="Medium (0–1, 2–3, 7–8, 9–10 km)"),
        Patch(facecolor=PRIORITY_COLORS["Low"], label="Low (1–2 km)"),
        Line2D([0], [0], color="#F7801E", lw=1.0, label="Reference network (orange, all canals)"),
    ]
    lax.legend(handles=legend_elems, loc="upper left", fontsize=8.5, framealpha=1.0,
               title="Priority class (Table 8.1)", title_fontsize=9, edgecolor="#888888",
               bbox_to_anchor=(0.0, 0.95))

    add_north_arrow(ax)
    add_scalebar(ax, length_m=2000, label="2 km")
    attrib = "Basemap: OpenStreetMap contributors. " if used_basemap else ""
    fig.text(0.99, 0.01,
             f"{attrib}Priority scoring methodology: §3.6. Source data: §8.2 Table 8.1.",
             ha="right", va="bottom", fontsize=6.5, color="#666666", style="italic")
    fig.subplots_adjust(bottom=0.04, top=0.93, left=0.02, right=0.99)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading GIS data...")
    survey, canal, main, branches, pois, locations, main_line = load_data()
    print(f"  Survey_new (clean): {len(survey)} sections")
    print(f"  Canal main alignment: {len(main)} features, {main_line.length:.1f} m")
    print(f"  Canal branches: {len(branches)} features")
    print(f"  POIs: {len(pois)}")
    print(f"  Locations: {len(locations)}")

    print("Computing chainage...")
    survey, y_min, y_max = compute_chainage(survey, main_line, locations)
    pois_ch = poi_chainage(pois, y_min, y_max)
    print(f"  chainage range: {survey['chainage'].min():.0f} to {survey['chainage'].max():.0f} m")
    print(f"  Y-anchor: {y_min:.1f} m N (intake) to {y_max:.1f} m N (terminus)")

    print("\nGenerating Figure 6.2 (velocity vs Vc)...")
    fig_6_2_velocity_bar()

    print("Generating Figure 6.1 (elevation profile)...")
    fig_6_1_elevation_profile(pois_ch, survey)

    print("Generating Figure 5.1 (longitudinal flow regime)...")
    fig_5_1_flow_regime(survey)

    print("Generating Map 4.1 (alignment overview)...")
    map_4_1_alignment(survey, canal, main, branches, pois, locations)

    print("Generating Map 5.1 (water quality)...")
    map_5_1_contamination(survey, canal, main, branches, locations)

    print("Generating Map 8.1 (restoration priority)...")
    map_8_1_priority(survey, canal, main, branches, locations)

    print(f"\nAll figures written to {OUT_DIR}")


if __name__ == "__main__":
    main()
