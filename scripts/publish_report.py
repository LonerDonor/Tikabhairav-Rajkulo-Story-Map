"""Publish the report and its key diagrams to the web platform.

Exports the built report to site/downloads/ as a PDF (through Microsoft Word,
when it is installed; --docx also copies the Word file) and writes web-sized copies of the key
figures to site/figures/ for the platform's "Study" tab.

Run after scripts/build_figures.py and scripts/build_docx.py:
    python scripts/publish_report.py            # figures + report files
    python scripts/publish_report.py --no-pdf   # skip the Word PDF export
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parent.parent
RESEARCH = PROJECT / "research"
FIGURES = RESEARCH / "figures"
SITE_FIG = PROJECT / "site" / "figures"
SITE_DL = PROJECT / "site" / "downloads"
REPORT_DOCX = RESEARCH / "Tikabhairab_Rajkulo_Report_v2.docx"
REPORT_NAME = "Tikabhairab_Rajkulo_Report_v2"

# Figures shown in the Study tab (source file in research/figures → web file in site/figures).
WEB_FIGURES = {
    "fig_2_1_system_schematic.png": "fig_2_1_system.png",
    "fig_5_1_flow_regime.png": "fig_5_1_flow.png",
    "fig_6_1_survey_attributes.png": "fig_6_1_attributes.png",
    "fig_4_1_intake_schematic.png": "fig_4_1_intake.jpg",
    "map_8_1_priority.png": "map_8_1_priority.jpg",
    "fig_9_1_stakeholders.png": "fig_9_1_stakeholders.png",
    "fig_10_1_phasing.png": "fig_10_1_phasing.png",
}
MAX_W = 1600


def export_figures():
    SITE_FIG.mkdir(parents=True, exist_ok=True)
    for src, dst in WEB_FIGURES.items():
        im = Image.open(FIGURES / src)
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        out = SITE_FIG / dst
        if dst.endswith(".jpg"):
            im.convert("RGB").save(out, quality=82, optimize=True, progressive=True)
        else:
            im.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(out, optimize=True)
        print(f"  {out.relative_to(PROJECT)}  {out.stat().st_size // 1024} KB")


def export_pdf(docx, pdf):
    """Export through Microsoft Word (Windows). Returns True on success."""
    ps = (f"$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
          f"try {{ $d = $w.Documents.Open('{docx}', $false, $true); $d.ExportAsFixedFormat('{pdf}', 17); "
          f"$d.Close($false) }} finally {{ $w.Quit() }}")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, timeout=300,
                       capture_output=True)
        return pdf.exists()
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  PDF export skipped ({type(e).__name__}); Microsoft Word is needed for it.")
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-pdf", action="store_true", help="do not export the PDF through Word")
    ap.add_argument("--docx", action="store_true", help="also copy the Word file into site/downloads/")
    args = ap.parse_args()
    if not REPORT_DOCX.exists():
        sys.exit(f"Build the report first: {REPORT_DOCX} is missing")

    print("Web figures:")
    export_figures()

    SITE_DL.mkdir(parents=True, exist_ok=True)
    if args.docx:   # ~10 MB with photographs; the Word file normally stays in research/
        shutil.copy2(REPORT_DOCX, SITE_DL / f"{REPORT_NAME}.docx")
        print(f"Report: site/downloads/{REPORT_NAME}.docx")
    if not args.no_pdf:
        pdf = SITE_DL / f"{REPORT_NAME}.pdf"
        if export_pdf(REPORT_DOCX, pdf):
            print(f"Report: site/downloads/{REPORT_NAME}.pdf  {pdf.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
