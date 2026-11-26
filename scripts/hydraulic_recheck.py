"""Hydraulic re-check of the Tikabhairab Rajkulo from the May 2022 survey data.

Replaces the single average-slope / Lacey-regime argument with three steps:

  (a) Measured long-profile. Every survey photo listed in CANAL_SECTIONS[].photos
      is read for its EXIF GPS altitude and snapped to its own section: the
      photo's position is projected onto that section's GPS-walked polyline,
      which gives its chainage. Altitudes are fitted with a continuous
      piecewise-linear profile (1 km segments) whose segment slopes are
      constrained to be >= 0 (water cannot run uphill in an open channel).
      The fit has a free intercept, so the phone's datum offset is estimated
      from all photos and the profile is then tied to the DoI intake benchmark.
      The fit is robust (bisquare reweighting) and its 90 % bands come from a
      cluster bootstrap that resamples whole sections. An unconstrained LOWESS
      curve is computed as a cross-check. The result is compared with the
      straight-line `zcoord` the site uses (1,477.16 m -> 1,314.02 m over the
      main chainage).

  (b) Manning velocities for every GPS-walked main-line section that is
      rectangular or circular and has dimensions. Inputs: the section's slope
      from (a); Manning's n from the lining material recorded in Survey_new
      (Chow 1959, Table 5-6); and flow depths of 25 %, 50 % (central) and 80 %
      of the section's depth or diameter. Velocities are compared with a
      self-cleansing band of 0.6-0.9 m/s and with masonry scour limits of
      2.5 m/s (cement mortar) and 1.8 m/s (old, weak mortar).

  (c) Silting recorded in the survey compared with the predicted velocity.

Outputs (paths relative to the repo root):
  research/figures/fig_H1_measured_long_profile.png
  research/figures/fig_H2_manning_velocity.png
  research/figures/fig_H3_silting_vs_velocity.png
  research/data/hydraulic_recheck_photos.csv     one row per photo used
  research/data/hydraulic_recheck_sections.csv   one row per section analysed
  research/data/hydraulic_recheck_summary.json   headline numbers quoted in the md
  site/profile.js                                only with --site: measured elevation and local
                                                 slope per section (not used by the site)
  research/hydraulic_recheck.md                  blocks between
                                                 <!-- BEGIN AUTO: name --> / <!-- END AUTO: name -->
                                                 are rewritten in place

Usage:
    python scripts/hydraulic_recheck.py --src "D:\\Rajkulo All Documents"
    (or set RAJKULO_SRC). Needs numpy, matplotlib, Pillow, pyogrio.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROJECT = Path(__file__).resolve().parent.parent
SITE_DATA_JS = PROJECT / "site" / "data.js"
SITE_PROFILE_JS = PROJECT / "site" / "profile.js"
FIG_DIR = PROJECT / "research" / "figures"
OUT_DIR = PROJECT / "research" / "data"
MD_PATH = PROJECT / "research" / "hydraulic_recheck.md"

# ── Fixed inputs ────────────────────────────────────────────────────────────
Z_INTAKE = 1477.16          # DoI benchmark at chainage 0 (as used for zcoord)
Z_TERMINUS = 1314.02        # DoI benchmark at the Lagankhel outlet
REPORT_LEN = 10668.5        # GPS-walked length used by the report (§6.1)
NPT_OFFSET = dt.timedelta(hours=5, minutes=45)   # Nepal time = UTC + 5:45

KNOT_STEP = 1000.0          # segment length of the monotone profile (m)
MIN_TAIL = 500.0            # a last segment shorter than this is merged
LOWESS_H = 600.0            # half-window of the unconstrained check curve (m)
GRID_STEP = 25.0
N_BOOT = 1000
SEED = 20220504             # first survey day
MAX_SNAP_M = 50.0           # section photos farther than this from their line are dropped
POI_SNAP_M = 15.0           # POI photos must lie this close to a walked section line
GAP_M = 300.0               # profile stretches with no photo within this are flagged
S_FLOOR = 0.001             # slope used where the fit is flat within GPS resolution (1 in 1,000)

DEPTH_FRACTIONS = (0.25, 0.50, 0.80)   # flow depth / section depth (or diameter)
V_SELF_CLEAN = (0.60, 0.90)            # m/s
V_SCOUR = 2.5                          # m/s, cement-mortar brick / stone masonry
V_SCOUR_WEAK = 1.8                     # m/s, old lime- or mud-mortar masonry
LACEY_Q, LACEY_F = 0.10, 1.0           # as in the report §6.4

# Manning's n (min, normal, max, description) after Chow (1959), Table 5-6.
MANNING_N = {
    "brick":    (0.012, 0.015, 0.018, "brick in cement mortar"),
    "stone":    (0.017, 0.025, 0.030, "cemented rubble (stone) masonry"),
    "concrete": (0.014, 0.017, 0.020, "unfinished concrete"),
    "mixed":    (0.015, 0.020, 0.025, "mixed brick / stone / concrete (interpolated)"),
    "unknown":  (0.015, 0.020, 0.025, "lined, material not recorded (interpolated)"),
    "pipe":     (0.011, 0.013, 0.015, "concrete (hume) pipe with joints / some debris"),
    "pvc":      (0.009, 0.010, 0.011, "PVC pipe"),
    "unlined":  (0.022, 0.027, 0.033, "earth with short grass and few weeds"),
}

# Colours (reference palette of the dataviz method, light mode).
C_SURFACE, C_TEXT, C_TEXT2, C_MUTED, C_GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
C_BLUE, C_BLUE_LIGHT, C_ORANGE, C_AQUA = "#2a78d6", "#cde2fb", "#eb6834", "#1baf7a"


# ── Inputs ──────────────────────────────────────────────────────────────────
def resolve_src(arg):
    for cand in (arg, os.environ.get("RAJKULO_SRC"), r"D:\Rajkulo All Documents"):
        if cand and Path(cand).exists():
            return Path(cand)
    sys.exit("Source folder not found: pass --src or set RAJKULO_SRC")


def load_js_array(path, name):
    text = Path(path).read_text(encoding="utf-8")
    m = re.search(rf"const {name} = (\[.*?\]);\s*(?:\n|$)", text, re.S)
    if not m:
        sys.exit(f"{name} not found in {path}")
    return json.loads(m.group(1)), hashlib.sha1(m.group(1).encode("utf-8")).hexdigest()[:12]


def num(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def main_line(sections):
    """Indices on the intake->terminus path: walk back from the max-chainage section,
    matching each section's start chainage (chainage - sec_len) to an end chainage."""
    have = [s for s in sections if s["chainage"] is not None]
    cur = max(have, key=lambda s: s["chainage"])
    path = [cur["idx"]]
    while True:
        start = cur["chainage"] - (cur["sec_len"] or 0)
        if start < 0.5:
            break
        cands = [s for s in have if s["idx"] not in path and abs(s["chainage"] - start) <= 0.15]
        if not cands:
            break
        nxt = min(cands, key=lambda s: abs(s["chainage"] - start))
        path.append(nxt["idx"])
        cur = nxt
    return set(path)


def load_lining(gpkg):
    """Lining material per Mergin fid (row order + 1, as in build_platform_data.py)."""
    import pyogrio
    df = pyogrio.read_dataframe(gpkg, layer="Survey_new", read_geometry=False)
    out = {}
    for i, r in df.reset_index(drop=True).iterrows():
        photos = {str(r.get(c)) for c in ("Photo1", "Photo2", "Photo3", "Photo4") if r.get(c)}
        out[i + 1] = {"m": r.get("ClinedM"), "other": r.get("ClinedMother"), "photos": photos}
    return out


def classify_material(sec, lin):
    if sec["shape"] == "Circular":
        m = str((lin or {}).get("m") or "").lower()
        return "pvc" if m == "pvc" else "pipe"
    if sec["lined"] == "No":
        return "unlined"
    if not lin:
        return "unknown"
    m = str(lin.get("m") or "").strip().lower()
    o = str(lin.get("other") or "").strip().lower()
    if m in ("brick", "concrete", "stone", "pvc"):
        return m
    if m == "other":
        kinds = {k for k in ("brick", "stone", "concrete") if k in o}
        if len(kinds) > 1:
            return "mixed"
        if kinds:
            return kinds.pop()
    return "unknown"


def read_exif(path):
    from PIL import Image
    from PIL.ExifTags import GPSTAGS, TAGS
    ex = Image.open(path).getexif()
    gps = {GPSTAGS.get(k, k): v for k, v in ex.get_ifd(0x8825).items()}
    base = {TAGS.get(k, k): v for k, v in ex.items()}
    if "GPSAltitude" not in gps or "GPSLatitude" not in gps:
        return None

    def dms(v, ref):
        x = float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
        return -x if ref in ("S", "W") else x

    alt = float(gps["GPSAltitude"])
    if gps.get("GPSAltitudeRef") in (1, b"\x01"):
        alt = -alt
    local = dt.datetime.strptime(base["DateTime"], "%Y:%m:%d %H:%M:%S")
    age = None
    if "GPSTimeStamp" in gps and "GPSDateStamp" in gps:
        h, mi, s = (float(v) for v in gps["GPSTimeStamp"])
        fix = dt.datetime.strptime(gps["GPSDateStamp"], "%Y:%m:%d") + dt.timedelta(hours=h, minutes=mi, seconds=s)
        age = (local - NPT_OFFSET - fix).total_seconds()
    return {"lat": dms(gps["GPSLatitude"], gps["GPSLatitudeRef"]),
            "lon": dms(gps["GPSLongitude"], gps["GPSLongitudeRef"]),
            "alt": alt, "time": local, "fix_age_s": age,
            "device": f"{base.get('Make', '')} {base.get('Model', '')}".strip()}


def project_on_line(lat, lon, coords):
    """Distance (m) from a point to a polyline, and the fraction of polyline length at the foot."""
    kx = 111320.0 * math.cos(math.radians(lat))
    ky = 110574.0
    pts = [((x - lon) * kx, (y - lat) * ky) for x, y in coords]
    if len(pts) == 1:
        return math.hypot(*pts[0]), 0.5
    seglens = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    total = sum(seglens) or 1.0
    best, run = (1e18, 0.5), 0.0
    for (a, b), L in zip(zip(pts, pts[1:]), seglens):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = 0.0 if L == 0 else max(0.0, min(1.0, -(a[0] * dx + a[1] * dy) / (L * L)))
        d = math.hypot(a[0] + t * dx, a[1] + t * dy)
        if d < best[0]:
            best = (d, (run + t * L) / total)
        run += L
    return best


def chainage_of(e, s):
    d, frac = project_on_line(e["lat"], e["lon"], s["coords"])
    return d, (s["chainage"] - s["sec_len"]) + frac * s["sec_len"]


# ── Profile fitting ─────────────────────────────────────────────────────────
def nnls(A, b, tol=1e-10):
    """Lawson-Hanson non-negative least squares."""
    m, n = A.shape
    P = np.zeros(n, bool)
    x = np.zeros(n)
    w = A.T @ (b - A @ x)
    for _ in range(3 * n + 10):
        if P.all() or w[~P].max() <= tol * max(1.0, np.abs(w).max()):
            break
        j = int(np.argmax(np.where(~P, w, -np.inf)))
        P[j] = True
        while True:
            z = np.zeros(n)
            z[P] = np.linalg.lstsq(A[:, P], b, rcond=None)[0]
            if (z[P] > 0).all():
                break
            mask = P & (z <= 0)
            alpha = np.min(x[mask] / (x[mask] - z[mask]))
            x = x + alpha * (z - x)
            P &= x > tol
        x = z
        w = A.T @ (b - A @ x)
    return x


def knots_for(x_end, step=KNOT_STEP, phase=0.0):
    ks = [0.0] + [k for k in np.arange(phase if phase > 0 else step, x_end, step)]
    if x_end - ks[-1] < MIN_TAIL and len(ks) > 1:
        ks.pop()
    return np.array(ks + [x_end])


def seg_lengths(x, knots):
    """L[i, k] = length of segment k that lies upstream of x[i]."""
    x = np.asarray(x, float)[:, None]
    return np.clip(x - knots[None, :-1], 0, np.diff(knots)[None, :])


def fit_monotone(x, alt, knots, w=None, robust_iter=2, constrained=True):
    """alt = c - L @ s + e with s >= 0 (c free). Returns slopes, c, robustness weights.
    constrained=False gives the ordinary (unconstrained) robust least-squares fit."""
    L = seg_lengths(x, knots)
    w = np.ones_like(alt) if w is None else w
    rw = np.ones_like(alt)
    for it in range(robust_iter + 1):
        ww = w * rw
        sw = np.sqrt(ww)
        ym = (ww * alt).sum() / ww.sum()
        Lm = (ww[:, None] * L).sum(0) / ww.sum()
        A = -(L - Lm) * sw[:, None]
        b = (alt - ym) * sw
        s = nnls(A, b) if constrained else np.linalg.lstsq(A, b, rcond=None)[0]
        c = ym + Lm @ s
        res = alt - (c - L @ s)
        if it < robust_iter:
            scale = 6.0 * np.median(np.abs(res))
            if scale <= 0:
                break
            u = np.clip(res / scale, -1, 1)
            rw = (1 - u ** 2) ** 2
    return s, c, rw, res


def profile_z(xq, knots, s):
    return Z_INTAKE - seg_lengths(np.atleast_1d(xq), knots) @ s


def lowess(x, y, grid, h, robust_iter=2):
    """Unconstrained robust local-linear fit (tricube kernel). Level on grid; NaN where
    fewer than 6 photos or too little spread inside the window."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    rw = np.ones_like(y)

    def loclin(x0):
        d = x[None, :] - x0[:, None]
        u = np.abs(d) / h
        w = np.where(u < 1, (1 - u ** 3) ** 3, 0.0) * rw[None, :]
        s0, s1, s2 = w.sum(1), (w * d).sum(1), (w * d * d).sum(1)
        t0, t1 = (w * y).sum(1), (w * d * y).sum(1)
        det = s0 * s2 - s1 * s1
        with np.errstate(invalid="ignore", divide="ignore"):
            spread = np.sqrt(np.maximum(s2 / s0 - (s1 / s0) ** 2, 0))
            ok = ((w > 0).sum(1) >= 6) & (spread > h / 4)
            return np.where(ok, (s2 * t0 - s1 * t1) / det, np.nan)

    for _ in range(robust_iter):
        res = y - loclin(x)
        scale = 6.0 * np.nanmedian(np.abs(res))
        rw = np.where(np.isfinite(res), (1 - np.clip(res / scale, -1, 1) ** 2) ** 2, 1.0)
    return loclin(grid)


def broken_stick_1(x, y, lo=1000.0, hi=8500.0, step=50.0):
    """Continuous two-piece OLS fit; breakpoint by grid search."""
    best = None
    for bk in np.arange(lo, hi + step, step):
        X = np.column_stack([np.ones_like(x), x, np.maximum(0, x - bk)])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        sse = float(((y - X @ coef) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, float(bk), -float(coef[1]), -float(coef[1] + coef[2]))
    return {"break_m": best[1], "slope_upper": best[2], "slope_lower": best[3]}


# ── Hydraulics ──────────────────────────────────────────────────────────────
def flow_geom(kind, a, b, frac):
    """kind 'rect': a=width, b=depth; kind 'circ': a=diameter. Returns A, P."""
    if kind == "rect":
        y = frac * b
        return a * y, a + 2 * y
    D, y = a, frac * a
    th = 2 * math.acos(1 - 2 * y / D)
    return D * D / 8 * (th - math.sin(th)), D * th / 2


def kennedy_vc(kind, a, b, frac, m=1.0):
    """Kennedy's critical velocity 0.55 m D^0.64 with D = hydraulic mean depth (area / top width)."""
    A, _ = flow_geom(kind, a, b, frac)
    if kind == "rect":
        T = a
    else:
        th = 2 * math.acos(1 - 2 * frac)
        T = a * math.sin(th / 2)
    return 0.55 * m * (A / T) ** 0.64


def manning_v(n, A, P, S):
    if S is None or not np.isfinite(S) or S <= 0:
        return 0.0
    return (1.0 / n) * (A / P) ** (2 / 3) * math.sqrt(S)


def lacey_slope(Q, f):
    return f ** (5 / 3) / (3340 * Q ** (1 / 6))


def classify_v(v):
    if v < V_SELF_CLEAN[0]:
        return "below self-cleansing"
    if v < V_SELF_CLEAN[1]:
        return "marginal"
    if v <= V_SCOUR:
        return "self-cleansing"
    return "above scour limit"


def mann_whitney(a, b):
    """Two-sided Mann-Whitney U, normal approximation with tie correction."""
    allv = sorted([(v, 0) for v in a] + [(v, 1) for v in b])
    ranks, ties, i = [0.0] * len(allv), [], 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        for k in range(i, j + 1):
            ranks[k] = (i + j) / 2 + 1
        ties.append(j - i + 1)
        i = j + 1
    n1, n2 = len(a), len(b)
    U1 = sum(r for r, (_, g) in zip(ranks, allv) if g == 0) - n1 * (n1 + 1) / 2
    N = n1 + n2
    sigma = math.sqrt(n1 * n2 / 12 * ((N + 1) - sum(t ** 3 - t for t in ties) / (N * (N - 1))))
    z = (U1 - n1 * n2 / 2) / sigma if sigma else 0.0
    return U1, z, math.erfc(abs(z) / math.sqrt(2))


def fisher_exact(a, b, c, d):
    """Two-sided Fisher exact test for [[a, b], [c, d]]."""
    n, r1, c1 = a + b + c + d, a + b, a + c

    def pmf(k):
        return math.comb(c1, k) * math.comb(n - c1, r1 - k) / math.comb(n, r1)
    p0 = pmf(a)
    return sum(pmf(k) for k in range(max(0, r1 + c1 - n), min(r1, c1) + 1) if pmf(k) <= p0 * (1 + 1e-9))


# ── Analysis ────────────────────────────────────────────────────────────────
def run_profile(pts, x_end, knots, rng, n_boot=N_BOOT):
    """Monotone fit + cluster bootstrap. pts: list of dicts with x, alt, cluster."""
    x = np.array([p["x"] for p in pts])
    alt = np.array([p["alt"] for p in pts])
    s, c, rw, res = fit_monotone(x, alt, knots)
    clusters = defaultdict(list)
    for k, p in enumerate(pts):
        clusters[p["cluster"]].append(k)
    keys = list(clusters)
    boot = np.zeros((n_boot, len(knots) - 1))
    boot_free = np.zeros((n_boot, len(knots) - 1))
    for bi in range(n_boot):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        ids = np.concatenate([clusters[keys[j]] for j in pick])
        boot[bi] = fit_monotone(x[ids], alt[ids], knots, robust_iter=1)[0]
        boot_free[bi] = fit_monotone(x[ids], alt[ids], knots, robust_iter=1, constrained=False)[0]
    s_free = fit_monotone(x, alt, knots, constrained=False)[0]
    return {"knots": knots, "s": s, "s_free": s_free, "offset": Z_INTAKE - c, "rw": rw, "res": res,
            "boot": boot, "boot_free": boot_free, "sigma": float(1.4826 * np.median(np.abs(res)))}


def section_slopes(prof, x0, x1):
    xs = np.array([x0, x1])
    L = seg_lengths(xs, prof["knots"])
    dL = (L[1] - L[0]) / (x1 - x0)
    med = float(dL @ prof["s"])
    b = prof["boot"] @ dL
    bf = prof["boot_free"] @ dL
    # lower bound from the constrained fit (>= 0); upper bound from whichever fit allows
    # the steeper slope, so a binding constraint cannot make the band look narrower than the data.
    return med, float(np.percentile(b, 5)), float(max(np.percentile(b, 95), np.percentile(bf, 95)))


def analyse_sections(sections, main, lining, prof, x_end, fit_pts):
    rows = []
    for s in sections:
        if s["is_connector"] or s["idx"] not in main or s["chainage"] is None or s["sec_len"] is None:
            continue
        b, H, D = num(s["width"]), num(s["height"]), num(s["diam"])
        if s["shape"] == "Rectangular" and b and H:
            kind, ga, gb = "rect", b / 100, H / 100
        elif s["shape"] == "Circular" and D:
            kind, ga, gb = "circ", D / 100, D / 100
        else:
            continue
        x1 = min(s["chainage"], x_end)
        x0 = max(s["chainage"] - s["sec_len"], 0.0)
        if x1 - x0 < 1.0:
            continue
        S_fit, S_lo, S_hi = section_slopes(prof, x0, x1)
        flat = S_fit < S_FLOOR
        S_use = max(S_fit, S_FLOOR)
        mat = classify_material(s, lining.get(s["mergin_fid"]) if s["mergin_fid"] else None)
        n_min, n_nom, n_max, _ = MANNING_N[mat]
        v = {}
        for frac in DEPTH_FRACTIONS:
            A, P = flow_geom(kind, ga, gb, frac)
            v[frac] = (manning_v(n_nom, A, P, S_use), A)
        A, P = flow_geom(kind, ga, gb, 0.5)
        rows.append({
            "idx": s["idx"], "pdf_n": s["pdf_n"], "tole": s["tole"],
            "x0": x0, "x1": s["chainage"], "shape": s["shape"],
            "width_m": ga if kind == "rect" else None, "depth_m": gb if kind == "rect" else None,
            "diam_m": ga if kind == "circ" else None,
            "material": mat, "n_min": n_min, "n_nom": n_nom, "n_max": n_max,
            "S": S_fit, "S_p05": S_lo, "S_p95": S_hi, "S_used": S_use, "flat": flat,
            "v25": v[0.25][0], "v50": v[0.5][0], "v80": v[0.8][0],
            "v_low": manning_v(n_max, A, P, max(S_lo, S_FLOOR)), "v_high": manning_v(n_min, A, P, max(S_hi, S_FLOOR)),
            "Q50_m3s": v[0.5][0] * v[0.5][1], "vc_kennedy50": kennedy_vc(kind, ga, gb, 0.5),
            "class": classify_v(v[0.5][0]), "silting": s["silting"], "flow": s["flow"],
            "n_photos": sum(1 for p in fit_pts if p["cluster"] == s["idx"]),
        })
    return rows


def silting_stats(rows):
    pres = [r for r in rows if r["silting"] == "Present"]
    absn = [r for r in rows if r["silting"] == "Absent"]
    if not pres or not absn:
        return None
    U, z, p = mann_whitney([r["v50"] for r in pres], [r["v50"] for r in absn])
    Us, zs, ps = mann_whitney([r["S"] for r in pres], [r["S"] for r in absn])
    a = sum(r["v50"] < V_SELF_CLEAN[1] for r in pres)
    c = sum(r["v50"] < V_SELF_CLEAN[1] for r in absn)
    return {"present_n": len(pres), "absent_n": len(absn),
            "present_median_v50": float(np.median([r["v50"] for r in pres])),
            "absent_median_v50": float(np.median([r["v50"] for r in absn])),
            "present_median_S": float(np.median([r["S"] for r in pres])),
            "absent_median_S": float(np.median([r["S"] for r in absn])),
            "mwu_v_p": p, "mwu_v_z": z, "mwu_S_p": ps,
            "present_lt_0.9": [a, len(pres)], "absent_lt_0.9": [c, len(absn)],
            "fisher_p": fisher_exact(a, len(pres) - a, c, len(absn) - c),
            "absent_chainages": sorted(round(r["x1"]) for r in absn)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", help='Folder "Rajkulo All Documents" (default: $RAJKULO_SRC)')
    ap.add_argument("--data", default=str(SITE_DATA_JS), help="data.js holding CANAL_SECTIONS / CANAL_POIS")
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--site", action="store_true", help="also write site/profile.js (not used by the site)")
    ap.add_argument("--boot", type=int, default=N_BOOT)
    args = ap.parse_args()

    src = resolve_src(args.src)
    photo_dirs = [src / "Rajkulo All Documents" / "RajkuloSurvey" / "rajkulo_survey",
                  src / "Mergin Maps Data" / "CANAL1"]
    gpkg = src / "Mergin Maps Data" / "CANAL1" / "Syrvey.gpkg"

    sections, data_hash = load_js_array(args.data, "CANAL_SECTIONS")
    try:
        pois, _ = load_js_array(args.data, "CANAL_POIS")
    except SystemExit:
        pois = []
    by_idx = {s["idx"]: s for s in sections}
    main = main_line(sections)
    main_len = max(s["chainage"] for s in sections if s["chainage"] is not None)
    s_mean = (Z_INTAKE - Z_TERMINUS) / main_len
    s_report = (Z_INTAKE - Z_TERMINUS) / REPORT_LEN
    S_lacey = lacey_slope(LACEY_Q, LACEY_F)
    branches = sorted(s["idx"] for s in sections if not s["is_connector"] and s["idx"] not in main)
    print(f"Sections: {len(sections)} (CANAL_SECTIONS sha1 {data_hash}); main line {len(main)}; "
          f"walked branch sections {branches}")
    print(f"Mean slope over main chainage {main_len:.1f} m: {s_mean:.5f} (1 in {1 / s_mean:.1f}); "
          f"report slope {s_report:.5f}; Lacey {S_lacey:.6f}")

    lining = load_lining(gpkg)
    agree = sum(1 for s in sections if s["mergin_fid"] in lining
                and lining[s["mergin_fid"]]["photos"] & set(s["photos"]))
    print(f"Survey_new lining join confirmed by shared photo names for {agree} sections")

    # ── photos ──────────────────────────────────────────────────────────────
    exif_cache = {}

    def exif(p):
        if p not in exif_cache:
            f = next((d / p for d in photo_dirs if (d / p).exists()), None)
            exif_cache[p] = ("missing", None) if f is None else (("ok", read_exif(f)) if read_exif(f) else ("nogps", None))
        return exif_cache[p]

    owners = defaultdict(list)
    for s in sections:
        for p in s["photos"]:
            owners[p].append(s["idx"])
    photos, dropped = [], []
    for p, idxs in owners.items():
        st, e = exif(p)
        if st != "ok":
            continue
        cands = [(chainage_of(e, by_idx[i]), by_idx[i]) for i in idxs
                 if by_idx[i]["coords"] and by_idx[i]["chainage"] is not None]
        if not cands:
            dropped.append((p, "no geometry"))
            continue
        (d, x), s = min(cands, key=lambda c: c[0][0])
        if d > MAX_SNAP_M:
            dropped.append((p, f"{d:.0f} m off line"))
            continue
        photos.append({"photo": p, "source": "section", "cluster": s["idx"], "pdf_n": s["pdf_n"],
                       "x": x, "snap_m": d, "alt": e["alt"], "date": e["time"].date().isoformat(),
                       "time": e["time"], "fix_age_s": e["fix_age_s"], "device": e["device"],
                       "main": s["idx"] in main})
    n_missing = sum(1 for p in owners if exif(p)[0] == "missing")
    n_nogps = sum(1 for p in owners if exif(p)[0] == "nogps")

    # POI photos (sensitivity / closure only), snapped to the nearest walked section line
    walked = [s for s in sections if not s["is_connector"] and s["coords"] and s["chainage"] is not None]
    seen = {p["photo"] for p in photos}
    poi_pts = []
    for q in pois:
        for p in q.get("photos") or []:
            if p in seen:
                continue
            st, e = exif(p)
            if st != "ok":
                continue
            (d, x), s = min(((chainage_of(e, s), s) for s in walked), key=lambda c: c[0][0])
            if d <= POI_SNAP_M:
                seen.add(p)
                poi_pts.append({"photo": p, "source": "poi", "cluster": s["idx"], "pdf_n": s["pdf_n"],
                                "x": x, "snap_m": d, "alt": e["alt"], "date": e["time"].date().isoformat(),
                                "time": e["time"], "fix_age_s": e["fix_age_s"], "device": e["device"],
                                "main": s["idx"] in main})

    fit_pts = sorted((p for p in photos if p["main"]), key=lambda p: p["x"])
    x_end = max(p["x"] for p in fit_pts)
    closure_pts = [p for p in photos + poi_pts if not p["main"] and p["x"] > x_end]
    poi_main = [p for p in poi_pts if p["main"]]
    devices = Counter(p["device"] for p in photos)
    print(f"Section photos: {len(owners)} unique, {len(photos)} snapped (missing file {n_missing}, "
          f"no GPS {n_nogps}, dropped {len(dropped)}); main-line fit set {len(fit_pts)}; "
          f"branch {sum(not p['main'] for p in photos)}; POI photos within {POI_SNAP_M:.0f} m {len(poi_pts)}")
    print(f"  devices {dict(devices)}; max |fix age| {max(abs(p['fix_age_s'] or 0) for p in photos):.0f} s; "
          f"median snap {np.median([p['snap_m'] for p in fit_pts]):.1f} m; profile end {x_end:.0f} m")

    # ── (a) profile ─────────────────────────────────────────────────────────
    rng = np.random.default_rng(SEED)
    knots = knots_for(x_end)
    prof = run_profile(fit_pts, x_end, knots, rng, args.boot)
    grid = np.arange(0.0, x_end + 1e-6, GRID_STEP)
    z_fit = profile_z(grid, knots, prof["s"])
    z_boot = Z_INTAKE - seg_lengths(grid, knots) @ prof["boot"].T
    z_lo, z_hi = np.percentile(z_boot, [5, 95], axis=1)
    z_lin = Z_INTAKE - s_mean * grid
    fx = np.array([p["x"] for p in fit_pts])
    fz = np.array([p["alt"] for p in fit_pts]) + prof["offset"]
    z_lowess = lowess(fx, fz, grid, LOWESS_H)
    gap = np.array([np.min(np.abs(fx - g)) > GAP_M for g in grid])
    tie = np.array([p["alt"] for p in fit_pts if p["x"] <= 100])
    print(f"Monotone fit: datum offset {prof['offset']:+.1f} m (intake-cluster median gives "
          f"{Z_INTAKE - np.median(tie):+.1f} m, n={len(tie)}); robust sigma {prof['sigma']:.1f} m; "
          f"{int((prof['rw'] < 0.5).sum())} photos down-weighted")
    seg_tab = []
    for k in range(len(knots) - 1):
        b = prof["boot"][:, k]
        nk = int(((fx >= knots[k]) & (fx < knots[k + 1] + (k == len(knots) - 2))).sum())
        seg_tab.append({"x0": float(knots[k]), "x1": float(knots[k + 1]), "n_photos": nk,
                        "S": float(prof["s"][k]), "S_free": float(prof["s_free"][k]),
                        "S_p05": float(np.percentile(b, 5)),
                        "S_p95": float(max(np.percentile(b, 95), np.percentile(prof["boot_free"][:, k], 95))),
                        "drop": float(prof["s"][k] * (knots[k + 1] - knots[k])),
                        "drop_linear": float(s_mean * (knots[k + 1] - knots[k]))})
        print(f"  seg {knots[k]:5.0f}-{knots[k + 1]:5.0f} n={nk:3d} S={prof['s'][k]:.4f} "
              f"[{seg_tab[-1]['S_p05']:.4f}, {seg_tab[-1]['S_p95']:.4f}] unconstrained {prof['s_free'][k]:+.4f}")

    stick = broken_stick_1(fx, fz)
    xb = stick["break_m"]

    def drop(prof_, x0, x1):
        L = seg_lengths(np.array([x0, x1]), prof_["knots"])
        dl = L[1] - L[0]
        bd = prof_["boot"] @ dl
        return {"x0": x0, "x1": x1, "drop": float(dl @ prof_["s"]), "p05": float(np.percentile(bd, 5)),
                "p95": float(np.percentile(bd, 95)), "linear": s_mean * (x1 - x0),
                "slope": float(dl @ prof_["s"]) / (x1 - x0)}
    reaches = [drop(prof, 0.0, xb), drop(prof, xb, x_end), drop(prof, 0.0, x_end)]
    for r in reaches:
        print(f"  drop {r['x0']:5.0f}-{r['x1']:5.0f}: {r['drop']:6.1f} m [{r['p05']:.1f}, {r['p95']:.1f}] "
              f"vs linear {r['linear']:.1f} m (mean slope {r['slope']:.4f})")
    dev = z_fit - z_lin
    k_max = int(np.argmax(dev))

    # day statistics: within-day regressions and junction jumps
    days = defaultdict(list)
    for p in fit_pts:
        days[p["date"]].append(p)
    day_fits, junctions = [], []
    for d_, ps in sorted(days.items()):
        xd = np.array([p["x"] for p in ps])
        zd = np.array([p["alt"] for p in ps]) + prof["offset"]
        if len(ps) >= 3 and np.ptp(xd) > 300:
            X = np.column_stack([np.ones_like(xd), xd])
            coef, *_ = np.linalg.lstsq(X, zd, rcond=None)
            res = zd - X @ coef
            se = math.sqrt((res @ res) / (len(xd) - 2) / ((xd - xd.mean()) ** 2).sum())
            day_fits.append({"date": d_, "n": len(ps), "x0": float(xd.min()), "x1": float(xd.max()),
                             "slope": float(-coef[1]), "se": se, "drop": float(-coef[1] * np.ptp(xd)),
                             "drop_linear": float(s_mean * np.ptp(xd))})
    dl_ = sorted(days)
    for d0, d1 in zip(dl_, dl_[1:]):
        a = sorted(days[d0], key=lambda p: p["x"])[-3:]
        b = sorted(days[d1], key=lambda p: p["x"])[:3]
        junctions.append({"from": d0, "to": d1, "gap_m": float(b[0]["x"] - a[-1]["x"]),
                          "jump_m": float(np.median([p["alt"] for p in b]) - np.median([p["alt"] for p in a]))})

    closure = None
    if closure_pts:
        xc = float(np.median([p["x"] for p in closure_pts]))
        zc = float(np.median([p["alt"] for p in closure_pts]) + prof["offset"])
        closure = {"n": len(closure_pts), "x": xc, "z_measured": zc, "z_linear": Z_INTAKE - s_mean * xc,
                   "range": [float(min(p["alt"] for p in closure_pts) + prof["offset"]),
                             float(max(p["alt"] for p in closure_pts) + prof["offset"])]}
        print(f"Closure ({len(closure_pts)} photos at ~{xc:.0f} m, alternative 'Old route'): measured "
              f"{zc:.1f} m vs linear {closure['z_linear']:.1f} m")

    # ── (b) Manning ─────────────────────────────────────────────────────────
    rows = analyse_sections(sections, main, lining, prof, x_end, fit_pts)
    cls = Counter(r["class"] for r in rows)
    print(f"Manning: {len(rows)} sections; classes {dict(cls)}; materials "
          f"{dict(Counter(r['material'] for r in rows))}")
    robust_low = [r for r in rows if r["v_high"] < V_SELF_CLEAN[0]]
    robust_ok = [r for r in rows if r["v_low"] >= V_SELF_CLEAN[1]]
    print(f"  robustly below 0.6 m/s (steepest slope, smoothest n): {len(robust_low)}; "
          f"robustly >= 0.9 m/s (flattest slope, roughest n): {len(robust_ok)}")

    # ── (c) silting ─────────────────────────────────────────────────────────
    silt = silting_stats(rows)
    print(f"Silting: {json.dumps(silt, default=float)}")

    # ── sensitivity ─────────────────────────────────────────────────────────
    def variant(pts, kn, label):
        pr = run_profile(pts, x_end, kn, np.random.default_rng(SEED), max(200, args.boot // 5))
        rr = analyse_sections(sections, main, lining, pr, x_end, pts)
        st = silting_stats(rr)
        c = Counter(r["class"] for r in rr)
        return {"label": label, "offset": pr["offset"],
                "drop_upper": drop(pr, 0.0, xb)["drop"], "drop_lower": drop(pr, xb, x_end)["drop"],
                "below": c.get("below self-cleansing", 0), "marginal": c.get("marginal", 0),
                "ok": c.get("self-cleansing", 0), "scour": c.get("above scour limit", 0),
                "silt_p": st["mwu_v_p"] if st else None,
                "present_med": st["present_median_v50"] if st else None,
                "absent_med": st["absent_median_v50"] if st else None}

    adj = {}
    cum = 0.0
    for j in junctions:
        if j["gap_m"] <= 100:
            cum -= j["jump_m"]
        adj[j["to"]] = cum
    day_adj_pts = [dict(p, alt=p["alt"] + adj.get(p["date"], 0.0)) for p in fit_pts]
    sens = [
        {"label": "Primary: 1 km segments, section photos", "offset": prof["offset"],
         "drop_upper": reaches[0]["drop"], "drop_lower": reaches[1]["drop"],
         "below": cls.get("below self-cleansing", 0), "marginal": cls.get("marginal", 0),
         "ok": cls.get("self-cleansing", 0), "scour": cls.get("above scour limit", 0),
         "silt_p": silt["mwu_v_p"], "present_med": silt["present_median_v50"],
         "absent_med": silt["absent_median_v50"]},
        variant(fit_pts, knots_for(x_end, 750.0), "750 m segments"),
        variant(fit_pts, knots_for(x_end, 1500.0), "1.5 km segments"),
        variant(fit_pts, knots_for(x_end, 1000.0, phase=500.0), "1 km segments shifted by 500 m"),
        variant(sorted(fit_pts + poi_main, key=lambda p: p["x"]), knots, f"+ {len(poi_main)} POI photos"),
        variant(day_adj_pts, knots, "Day offsets removed at the two short-gap junctions"),
    ]
    for v in sens:
        print(f"  {v['label']:<55} upper {v['drop_upper']:5.1f} m  lower {v['drop_lower']:6.1f} m  "
              f"classes {v['below']}/{v['marginal']}/{v['ok']}/{v['scour']}  silting p={v['silt_p']:.4f}")

    # ── outputs ─────────────────────────────────────────────────────────────
    summary = {
        "generated": dt.date.today().isoformat(), "canal_sections_sha1": data_hash,
        "main_chainage_m": main_len, "mean_slope": s_mean, "report_slope": s_report,
        "lacey_slope": S_lacey, "ratio_report_lacey": s_report / S_lacey, "ratio_chainage_lacey": s_mean / S_lacey,
        "photos": {"section_photos_unique": len(owners), "snapped": len(photos), "missing_file": n_missing,
                   "no_gps": n_nogps, "dropped": dropped, "fit": len(fit_pts),
                   "branch": sum(not p["main"] for p in photos), "poi_within_snap": len(poi_pts),
                   "poi_main": len(poi_main), "devices": dict(devices),
                   "median_snap_m": float(np.median([p["snap_m"] for p in fit_pts]))},
        "x_end_m": x_end, "knots": knots.tolist(), "datum_offset_m": prof["offset"],
        "datum_offset_intake_cluster_m": float(Z_INTAKE - np.median(tie)), "intake_cluster_n": int(len(tie)),
        "robust_sigma_m": prof["sigma"], "segments": seg_tab, "broken_stick": stick, "reaches": reaches,
        "max_above_linear_m": float(dev[k_max]), "x_max_above_linear_m": float(grid[k_max]),
        "max_lowess_minus_fit_m": float(np.nanmax(np.abs(z_lowess - z_fit))),
        "day_fits": day_fits, "junctions": junctions, "closure": closure,
        "manning": {"n": len(rows), "classes": dict(cls), "materials": dict(Counter(r["material"] for r in rows)),
                    "robust_below_0.6": len(robust_low), "robust_above_0.9": len(robust_ok),
                    "v50_above_scour": sum(r["v50"] > V_SCOUR for r in rows),
                    "v80_above_scour": sum(r["v80"] > V_SCOUR for r in rows),
                    "v80_above_weak": sum(r["v80"] > V_SCOUR_WEAK for r in rows),
                    "v_high_above_scour": sum(r["v_high"] > V_SCOUR for r in rows),
                    "v50_below_kennedy": sum(r["v50"] < r["vc_kennedy50"] for r in rows),
                    "kennedy_vc50_range": [min(r["vc_kennedy50"] for r in rows), max(r["vc_kennedy50"] for r in rows)],
                    "q50_median_m3s": float(np.median([r["Q50_m3s"] for r in rows])),
                    "q50_range_m3s": [min(r["Q50_m3s"] for r in rows), max(r["Q50_m3s"] for r in rows)],
                    "upper_reach_classes": dict(Counter(r["class"] for r in rows if r["x1"] <= xb)),
                    "lower_reach_classes": dict(Counter(r["class"] for r in rows if r["x1"] > xb)),
                    "upper_reach_silting": dict(Counter(r["silting"] for r in rows if r["x1"] <= xb)),
                    "lower_reach_silting": dict(Counter(r["silting"] for r in rows if r["x1"] > xb)),
                    "first_km_v50_median": float(np.median([r["v50"] for r in rows if r["x1"] <= 1000])),
                    "n_flat": sum(r["flat"] for r in rows),
                    "upper_reach_v50_median": float(np.median([r["v50"] for r in rows if r["x1"] <= xb])),
                    "lower_reach_v50_median": float(np.median([r["v50"] for r in rows if r["x1"] > xb]))},
        "silting": silt, "silting_seasonal_only": silting_stats([r for r in rows if r["flow"] == "Seasonal"]),
        "sensitivity": sens,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    zf = lambda xq: float(profile_z(xq, knots, prof["s"])[0]) if xq <= x_end else None
    with open(OUT_DIR / "hydraulic_recheck_photos.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["photo", "source", "section_idx", "pdf_n", "on_main_line", "used_in_fit", "chainage_m",
                    "snap_dist_m", "gps_alt_raw_m", "z_datum_corrected_m", "z_profile_m", "z_linear_m",
                    "date", "time", "fix_age_s"])
        fit_ids = {id(p) for p in fit_pts}
        for p in sorted(photos + poi_pts, key=lambda p: p["x"]):
            zp = zf(p["x"])
            w.writerow([p["photo"], p["source"], p["cluster"], p["pdf_n"], int(p["main"]), int(id(p) in fit_ids),
                        f"{p['x']:.1f}", f"{p['snap_m']:.1f}", f"{p['alt']:.2f}", f"{p['alt'] + prof['offset']:.2f}",
                        "" if zp is None else f"{zp:.2f}", f"{Z_INTAKE - s_mean * p['x']:.2f}",
                        p["date"], p["time"].isoformat(sep=" "), p["fix_age_s"]])
    with open(OUT_DIR / "hydraulic_recheck_sections.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v) for k, v in r.items()})
    (OUT_DIR / "hydraulic_recheck_summary.json").write_text(json.dumps(summary, indent=2, default=float),
                                                          encoding="utf-8")

    if not args.no_figures:
        figures(fit_pts, poi_main, closure_pts, prof, grid, z_fit, z_lo, z_hi, z_lin, z_lowess, gap,
                seg_tab, s_mean, s_report, S_lacey, rows, silt, x_end, main_len, days, xb)
    write_md_blocks(rows, seg_tab, reaches, sens, summary)
    if args.site:
        write_site_profile(sections, main, prof, x_end, data_hash)
    print("Done.")


# ── Figures ─────────────────────────────────────────────────────────────────
def _style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": C_SURFACE, "axes.facecolor": C_SURFACE, "savefig.facecolor": C_SURFACE,
        "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9, "axes.edgecolor": C_MUTED,
        "axes.labelcolor": C_TEXT2, "xtick.color": C_TEXT2, "ytick.color": C_TEXT2, "text.color": C_TEXT,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": C_GRID,
        "grid.linewidth": 0.6, "legend.frameon": False, "legend.fontsize": 8,
    })
    return plt


def figures(fit_pts, poi_main, closure_pts, prof, grid, z_fit, z_lo, z_hi, z_lin, z_lowess, gap,
            seg_tab, s_mean, s_report, S_lacey, rows, silt, x_end, main_len, days, xb):
    plt = _style()
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    off = prof["offset"]
    km = lambda v: np.asarray(v) / 1000.0

    # H1 — long profile + segment slopes
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(10, 7.2), sharex=True,
                                  gridspec_kw={"height_ratios": [2.2, 1], "hspace": 0.08})
    xg = km(grid)
    ax.fill_between(xg, z_lo, z_hi, color=C_BLUE_LIGHT, lw=0, label="90 % band (section bootstrap)")
    ax.plot(km([0, main_len]), [Z_INTAKE, Z_TERMINUS], color=C_MUTED, ls="--", lw=1.4,
            label="Site 'zcoord': straight line between benchmarks")
    fx = np.array([p["x"] for p in fit_pts])
    fz = np.array([p["alt"] for p in fit_pts]) + off
    w = prof["rw"]
    ax.scatter(km(fx[w >= 0.5]), fz[w >= 0.5], s=14, color=C_BLUE, alpha=0.55, lw=0,
               label=f"Survey photos, GPS altitude + {off:.1f} m datum offset (n={int((w >= 0.5).sum())})")
    if (w < 0.5).any():
        ax.scatter(km(fx[w < 0.5]), fz[w < 0.5], s=16, facecolor="none", edgecolor=C_BLUE, lw=0.9,
                   label="Photo down-weighted as outlier")
    if poi_main:
        ax.scatter(km([p["x"] for p in poi_main]), np.array([p["alt"] for p in poi_main]) + off, s=10,
                   marker="x", color=C_TEXT2, lw=0.7, alpha=0.6, label="POI photos (not used in fit)")
    if closure_pts:
        ax.scatter(km([p["x"] for p in closure_pts]), np.array([p["alt"] for p in closure_pts]) + off, s=22,
                   marker="D", facecolor="none", edgecolor=C_TEXT2, lw=0.9,
                   label="'Old route' photos (closure check)")
    zl = np.where(gap, np.nan, z_lowess)
    ax.plot(xg, zl, color=C_ORANGE, lw=1.0, alpha=0.9, label="Unconstrained LOWESS, 600 m window (check)")
    ax.plot(xg, z_fit, color=C_BLUE, lw=2.2, label="Measured profile: monotone fit, 1 km segments")
    ax.scatter(km([0, main_len]), [Z_INTAKE, Z_TERMINUS], s=46, marker="s", color=C_TEXT, zorder=5,
               label="DoI benchmarks")
    for d, ps in sorted(days.items()):
        x0 = min(p["x"] for p in ps)
        ax.axvline(x0 / 1000, color=C_GRID, lw=0.8, zorder=0)
        ax.text(x0 / 1000 + 0.05, 1492, dt.date.fromisoformat(d).strftime("%-d %b") if os.name != "nt"
                else dt.date.fromisoformat(d).strftime("%#d %b"), fontsize=7.5, color=C_TEXT2, va="top")
    ax.annotate(f"up to {np.nanmax(z_fit - (Z_INTAKE - s_mean * grid)):.0f} m above the straight line",
                xy=(grid[int(np.nanargmax(z_fit - (Z_INTAKE - s_mean * grid)))] / 1000,
                    z_fit[int(np.nanargmax(z_fit - (Z_INTAKE - s_mean * grid)))]),
                xytext=(6.6, 1462), fontsize=8, color=C_TEXT,
                arrowprops=dict(arrowstyle="-", color=C_TEXT2, lw=0.8))
    ax.set_ylabel("Elevation (m above MSL, tied to intake benchmark)")
    ax.set_ylim(1300, 1495)
    ax.set_title("Tikabhairab Rajkulo: long-profile from survey-photo GPS altitude vs the linear zcoord",
                 loc="left", fontweight="bold")
    ax.legend(loc="lower left", ncol=2, fontsize=7.5)

    for sg in seg_tab:
        ax2.fill_between(km([sg["x0"], sg["x1"]]), sg["S_p05"], sg["S_p95"], color=C_BLUE_LIGHT, lw=0)
        ax2.plot(km([sg["x0"], sg["x1"]]), [sg["S"], sg["S"]], color=C_BLUE, lw=2.2)
    ax2.plot([], [], color=C_BLUE, lw=2.2, label="Segment slope, monotone fit (90 % band shaded)")
    ax2.scatter(km([(sg["x0"] + sg["x1"]) / 2 for sg in seg_tab]), [sg["S_free"] for sg in seg_tab], s=22,
                facecolor=C_SURFACE, edgecolor=C_TEXT2, lw=1.0, zorder=4,
                label="Unconstrained fit (negative = apparent rise, i.e. GPS error)")
    ax2.axhline(s_mean, color=C_MUTED, ls="--", lw=1.2, label=f"Mean slope over chainage, {s_mean:.4f} (1 in {1 / s_mean:.0f})")
    ax2.axhline(s_report, color=C_MUTED, ls=":", lw=1.2, label=f"Report's slope, {s_report:.4f} (1 in {1 / s_report:.0f})")
    ax2.axhline(S_lacey, color=C_ORANGE, ls="-", lw=1.0, label=f"Lacey regime slope, {S_lacey:.5f}")
    ax2.set_ylabel("Bed slope (m/m)")
    ax2.set_xlabel("Chainage from intake (km)")
    ax2.set_xlim(-0.1, main_len / 1000 + 0.1)
    ax2.set_ylim(min(-0.002, min(s["S_free"] for s in seg_tab) * 1.2),
                 max(0.05, max(s["S_p95"] for s in seg_tab) * 1.05))
    ax2.legend(loc="upper left", fontsize=7.5)
    fig.text(0.01, 0.005, "Phone GPS altitude (vivo 1919); profile constrained never to rise; segments end at the last "
             "walked section with photos. Script: scripts/hydraulic_recheck.py", fontsize=7, color=C_TEXT2)
    fig.savefig(FIG_DIR / "fig_H1_measured_long_profile.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # H2 — Manning velocity by section along the canal
    fig, ax = plt.subplots(figsize=(10, 4.6))
    ax.axhspan(*V_SELF_CLEAN, color=C_GRID, lw=0, zorder=0, label="Self-cleansing band, 0.6–0.9 m/s")
    ax.axhline(V_SCOUR, color=C_TEXT2, ls="--", lw=1, label="Masonry scour limit, 2.5 m/s")
    ax.axhline(V_SCOUR_WEAK, color=C_TEXT2, ls=":", lw=1, label="Old weak-mortar limit, 1.8 m/s")
    groups = [("Present", C_ORANGE, "o", "Silting recorded"), ("Absent", C_BLUE, "s", "No silting recorded"),
              (None, C_MUTED, "^", "Silting not recorded")]
    for key, col, mk, lab in groups:
        rs = [r for r in rows if (r["silting"] == key if key else r["silting"] not in ("Present", "Absent"))]
        if not rs:
            continue
        xm = km([(r["x0"] + r["x1"]) / 2 for r in rs])
        v = np.array([r["v50"] for r in rs])
        lo = v - np.array([r["v_low"] for r in rs])
        hi = np.array([r["v_high"] for r in rs]) - v
        ax.errorbar(xm, v, yerr=[lo, hi], fmt="none", ecolor=col, elinewidth=0.8, alpha=0.45, capsize=0)
        ax.scatter(xm, v, s=34, marker=mk, color=col, edgecolor=C_SURFACE, lw=1.2, zorder=3,
                   label=f"{lab} (n={len(rs)})")
    ax.axvline(xb / 1000, color=C_TEXT2, lw=0.8, ls="-.")
    ax.text(xb / 1000 + 0.05, 3.85, f"profile break ≈ {xb / 1000:.1f} km", fontsize=7.5, color=C_TEXT2, va="top")
    ax.set_xlim(-0.1, x_end / 1000 + 0.3)
    ax.set_ylim(0, 4.0)
    ax.set_xlabel("Chainage from intake (km)")
    ax.set_ylabel("Manning velocity (m/s)")
    ax.set_title("Predicted velocity per section: half-full flow, nominal n, measured local slope",
                 loc="left", fontweight="bold")
    ax.legend(loc="upper left", fontsize=7.5, ncol=2)
    fig.text(0.01, -0.02, "Whiskers: roughest n with the flattest 5th-percentile slope to smoothest n with the "
             "steepest 95th-percentile slope (clipped at 4 m/s). Where the fitted slope is flat within GPS "
             f"resolution, S = {S_FLOOR} is used.", fontsize=7, color=C_TEXT2)
    fig.savefig(FIG_DIR / "fig_H2_manning_velocity.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # H3 — silting vs predicted velocity
    fig, ax = plt.subplots(figsize=(5.2, 4.2))
    rng = np.random.default_rng(7)
    for i, (key, col, mk, lab) in enumerate(groups[:2]):
        v = np.array([r["v50"] for r in rows if r["silting"] == key])
        ax.scatter(i + rng.uniform(-0.12, 0.12, len(v)), v, s=30, marker=mk, color=col, edgecolor=C_SURFACE,
                   lw=1.0, alpha=0.9)
        ax.plot([i - 0.25, i + 0.25], [np.median(v)] * 2, color=C_TEXT, lw=2)
        ax.text(i + 0.28, np.median(v), f"median {np.median(v):.2f}", va="center", fontsize=8, color=C_TEXT)
    ax.axhspan(*V_SELF_CLEAN, color=C_GRID, lw=0, zorder=0)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([f"Silting recorded\n(n={silt['present_n']})", f"No silting recorded\n(n={silt['absent_n']})"])
    ax.set_xlim(-0.6, 1.9)
    ax.set_ylabel("Manning velocity, half-full (m/s)")
    ax.set_title("Silting vs predicted velocity", loc="left", fontweight="bold")
    pv = silt["mwu_v_p"]
    ax.text(-0.55, ax.get_ylim()[1] * 0.97, "Mann-Whitney " + ("p < 0.001" if pv < 0.001 else f"p = {pv:.3f}"),
            fontsize=8, color=C_TEXT2, va="top")
    ax.text(1.85, sum(V_SELF_CLEAN) / 2, "0.6–0.9 m/s\nself-cleansing", fontsize=7, color=C_TEXT2, ha="right",
            va="center")
    fig.savefig(FIG_DIR / "fig_H3_silting_vs_velocity.png", dpi=160, bbox_inches="tight")
    plt.close(fig)


# ── Site data ───────────────────────────────────────────────────────────────
def write_site_profile(sections, main, prof, x_end, data_hash):
    """site/profile.js: measured elevation (at the section's end chainage, i.e. its Station
    Point) and local bed slope for every main-line section inside the profiled range."""
    knots = prof["knots"]
    out = {}
    for s in sections:
        if s["idx"] not in main or s["chainage"] is None or s["sec_len"] is None:
            continue
        x1 = s["chainage"]
        x0 = max(x1 - s["sec_len"], 0.0)
        if x0 >= x_end:
            continue
        rec = {}
        if x1 <= x_end:
            zb = Z_INTAKE - seg_lengths(np.array([x1]), knots) @ prof["boot"].T
            rec["z"] = round(float(profile_z(x1, knots, prof["s"])[0]), 1)
            rec["z_lo"], rec["z_hi"] = (round(float(v), 1) for v in np.percentile(zb[0], [5, 95]))
        xa, xb = x0, min(x1, x_end)
        if xb - xa >= 1.0:
            S, lo, hi = section_slopes(prof, xa, xb)
            rec["s"], rec["s_lo"], rec["s_hi"] = round(S, 5), round(lo, 5), round(hi, 5)
        if rec:
            out[str(s["pdf_n"])] = rec
    payload = {
        "method": "Monotone piecewise-linear fit (1 km segments) to the EXIF GPS altitude of the survey "
                  "photos, tied to the DoI intake benchmark; 90 % ranges from a section bootstrap. "
                  "See research/hydraulic_recheck.md.",
        "canal_sections_sha1": data_hash, "x_end_m": round(float(x_end), 1),
        "s_flat": S_FLOOR, "sections": out,
    }
    SITE_PROFILE_JS.write_text(
        "// Generated by scripts/hydraulic_recheck.py — DO NOT EDIT BY HAND.\n"
        "// Measured long-profile of the canal from survey-photo GPS altitudes, keyed by PDF section number.\n"
        "const CANAL_PROFILE = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8")
    print(f"Wrote {SITE_PROFILE_JS.relative_to(PROJECT)} ({len(out)} sections)")


# ── Markdown blocks ─────────────────────────────────────────────────────────
def write_md_blocks(rows, seg_tab, reaches, sens, summary):
    if not MD_PATH.exists():
        return
    f2, f3 = (lambda v: f"{v:.2f}"), (lambda v: f"{v:.4f}")
    blocks = {}
    t = ["| Segment (km) | Photos | Slope S (monotone fit) | 90 % range | Unconstrained fit | Drop (m) | "
         "Drop on straight line (m) |",
         "|---|---:|---:|---|---:|---:|---:|"]
    for s in seg_tab:
        t.append(f"| {s['x0'] / 1000:.1f}–{s['x1'] / 1000:.2f} | {s['n_photos']} | {f3(s['S'])} | "
                 f"{f3(s['S_p05'])}–{f3(s['S_p95'])} | {s['S_free']:+.4f} | {s['drop']:.1f} | {s['drop_linear']:.1f} |")
    blocks["segment-table"] = "\n".join(t)
    t = ["| Reach (km) | Measured drop (m) | 90 % range (m) | Mean slope | Straight-line drop (m) |",
         "|---|---:|---|---:|---:|"]
    for r in reaches:
        t.append(f"| {r['x0'] / 1000:.2f}–{r['x1'] / 1000:.2f} | {r['drop']:.1f} | {r['p05']:.1f}–{r['p95']:.1f} | "
                 f"{f3(r['slope'])} | {r['linear']:.1f} |")
    blocks["reach-table"] = "\n".join(t)
    t = ["| Variant | Datum offset (m) | Drop above break (m) | Drop below break (m) | Below / marginal / "
         "self-cleansing / above scour | Silting median V present vs absent (m/s) | Mann-Whitney p |",
         "|---|---:|---:|---:|---|---|---:|"]
    for v in sens:
        t.append(f"| {v['label']} | {v['offset']:+.1f} | {v['drop_upper']:.1f} | {v['drop_lower']:.1f} | "
                 f"{v['below']} / {v['marginal']} / {v['ok']} / {v['scour']} | "
                 f"{v['present_med']:.2f} vs {v['absent_med']:.2f} | "
                 f"{'< 0.001' if v['silt_p'] < 0.001 else format(v['silt_p'], '.3f')} |")
    blocks["sensitivity-table"] = "\n".join(t)
    t = ["| PDF # | Tole | Chainage (m) | Shape, size (cm) | Lining → n | Slope S (90 % range) | "
         "V at y = 0.25 / 0.5 / 0.8 depth (m/s) | V range (m/s) | Class (y = 0.5) | Silting |",
         "|---:|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        size = (f"rect {r['width_m'] * 100:.0f}×{r['depth_m'] * 100:.0f}" if r["shape"] == "Rectangular"
                else f"pipe Ø{r['diam_m'] * 100:.0f}")
        t.append(f"| {r['pdf_n']} | {r['tole']} | {r['x0']:.0f}–{r['x1']:.0f} | {size} | {r['material']} → "
                 f"{r['n_nom']:.3f} | {(f'flat, {S_FLOOR} used' if r['flat'] else f3(r['S']))} "
                 f"[{f3(r['S_p05'])}–{f3(r['S_p95'])}] | "
                 f"{f2(r['v25'])} / {f2(r['v50'])} / {f2(r['v80'])} | {f2(r['v_low'])}–{f2(r['v_high'])} | "
                 f"{r['class']} | {r['silting'] if r['silting'] in ('Present', 'Absent') else '—'} |")
    blocks["section-table"] = "\n".join(t)
    c = summary["manning"]["classes"]
    t = ["| Class (half-full, nominal n, fitted slope) | Sections |", "|---|---:|"]
    for k in ("below self-cleansing", "marginal", "self-cleansing", "above scour limit"):
        t.append(f"| {k} | {c.get(k, 0)} |")
    blocks["class-table"] = "\n".join(t)

    md = MD_PATH.read_text(encoding="utf-8")
    for name, body in blocks.items():
        md = re.sub(rf"(<!-- BEGIN AUTO: {name} -->).*?(<!-- END AUTO: {name} -->)",
                    lambda m: m.group(1) + "\n" + body + "\n" + m.group(2), md, flags=re.S)
    MD_PATH.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
