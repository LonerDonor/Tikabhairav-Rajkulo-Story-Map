"""Diagnostic plot: show isolated POIs vs blue surveyed canal vs orange reference."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
import sqlite3, pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.patheffects as pe
from shapely.ops import unary_union
from shapely.geometry import Point
from shapely import wkb
import pyproj

GPKG_DIR = Path(r"C:\Users\olenepal\Downloads\Rajkulo All Documents\Mergin Maps Data\CANAL1")
OUT = Path(__file__).parent.parent / "research" / "figures" / "gap_analysis.png"

# Load layers in UTM 45N
sn = gpd.read_file(GPKG_DIR / "Syrvey.gpkg", layer="Survey_new").to_crs(32645)
canal_ref = gpd.read_file(GPKG_DIR / "Syrvey.gpkg", layer="Canal").to_crs(32645)
JUNK = {"Test", "test", "Old route", "Possible canal", "Ahh", "canal 1 rajdal non existing"}
sn_blue = sn[(sn["Cseen"] == "Yes") & (~sn["Tole"].astype(str).str.strip().isin(JUNK))]
sn_blue_union = unary_union(sn_blue.geometry.tolist())

# POIs with fid via sqlite3
def parse_gpkg_geom(blob):
    if blob[:2] == b'GP':
        flags = blob[3]
        env_type = (flags >> 1) & 0x07
        env_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
        offset = 8 + env_sizes.get(env_type, 0)
        return wkb.loads(blob[offset:])
    return wkb.loads(blob)

conn = sqlite3.connect(GPKG_DIR / "POIS.gpkg")
poi_df = pd.read_sql("SELECT fid, Comment, geometry FROM POIS", conn)
conn.close()
trans = pyproj.Transformer.from_crs(4326, 32645, always_xy=True)
records = []
for _, r in poi_df.iterrows():
    g = parse_gpkg_geom(r["geometry"])
    x, y = trans.transform(g.x, g.y)
    pt = Point(x, y)
    dist = pt.distance(sn_blue_union)
    records.append({"fid": r["fid"], "Comment": r["Comment"], "x": x, "y": y, "dist": dist})
pois = pd.DataFrame(records)

# Plot
fig, ax = plt.subplots(figsize=(8, 16))
canal_ref.plot(ax=ax, color="#F7801E", linewidth=0.8, alpha=0.55, zorder=2, label="Reference (orange Canal layer)")
sn_blue.plot(ax=ax, color="#6190D3", linewidth=2.2, alpha=0.95, zorder=4)

# POIs by isolation tier
tier_on = pois[pois["dist"] <= 30]
tier_close = pois[(pois["dist"] > 30) & (pois["dist"] <= 200)]
tier_far = pois[pois["dist"] > 200]

ax.scatter(tier_on["x"], tier_on["y"], color="#27AE60", s=18, edgecolor="white",
           linewidth=0.5, zorder=6)
ax.scatter(tier_close["x"], tier_close["y"], color="#F39C12", s=40, edgecolor="white",
           linewidth=0.8, zorder=7)
ax.scatter(tier_far["x"], tier_far["y"], color="#C0392B", s=70, edgecolor="white",
           linewidth=1.0, zorder=8)

# Label isolated POIs
for _, p in pois[pois["dist"] > 30].iterrows():
    label = f"fid={int(p['fid'])} ({p['dist']:.0f}m)"
    ax.annotate(label, xy=(p["x"], p["y"]), xytext=(10, 4), textcoords="offset points",
                fontsize=7, color="#444444", fontweight="bold", zorder=9,
                path_effects=[pe.withStroke(linewidth=2, foreground="white")])

ax.set_aspect("equal")
ax.set_xticks([])
ax.set_yticks([])
ax.set_title("Gap analysis: isolated POIs vs blue surveyed canal", fontsize=11, color="#1F4E79")

legend_elems = [
    Line2D([0], [0], color="#6190D3", lw=2.2, label="Surveyed canal (Cseen='Yes')"),
    Line2D([0], [0], color="#F7801E", lw=0.8, label="Reference (orange Canal layer)"),
    Line2D([0], [0], marker="o", color="w", markerfacecolor="#27AE60", markeredgecolor="white",
           markersize=6, label=f"POI on canal ≤30m ({len(tier_on)})"),
    Line2D([0], [0], marker="o", color="w", markerfacecolor="#F39C12", markeredgecolor="white",
           markersize=8, label=f"POI near 30–200m ({len(tier_close)})"),
    Line2D([0], [0], marker="o", color="w", markerfacecolor="#C0392B", markeredgecolor="white",
           markersize=10, label=f"POI far >200m ({len(tier_far)})"),
]
ax.legend(handles=legend_elems, loc="upper left", fontsize=9, framealpha=0.95)

OUT.parent.mkdir(exist_ok=True)
fig.savefig(OUT, dpi=180, bbox_inches="tight")
plt.close(fig)
print(f"wrote {OUT}")
