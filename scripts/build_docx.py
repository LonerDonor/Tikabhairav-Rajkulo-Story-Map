"""Build a styled .docx from the v2 markdown report.

Handles: headings (# / ## / ###), paragraphs, **bold**/*italic* inline,
markdown pipe tables, bullet lists, numbered lists, blockquotes,
horizontal rules, fenced math blocks ($$...$$), italic-asterisked notes.
"""

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor, Cm, Inches, Emu

HERE = Path(__file__).parent          # scripts/
RESEARCH = HERE.parent / "research"   # reports, figures
SRC = RESEARCH / "Tikabhairab_Rajkulo_Report_v2.md"
OUT = RESEARCH / "Tikabhairab_Rajkulo_Report_v2.docx"
FIGURES_DIR = RESEARCH / "figures"

# Map figure/map references in the markdown to PNG filenames in figures/
FIGURE_FILES = {
    ("FIGURE", "2.1"):  "fig_2_1_system_schematic.png",
    ("FIGURE", "4.1"):  "fig_4_1_intake_schematic.png",
    ("FIGURE", "5.1"):  "fig_5_1_flow_regime.png",
    ("FIGURE", "6.1"):  "fig_6_1_survey_attributes.png",     # from scripts/build_figures.py
    ("FIGURE", "9.1"):  "fig_9_1_stakeholders.png",
    ("FIGURE", "10.1"): "fig_10_1_phasing.png",
    ("MAP",    "4.1"):  "map_4_1_alignment.png",
    ("MAP",    "5.1"):  "map_5_1_contamination.png",
    ("MAP",    "8.1"):  "map_8_1_priority.png",
}


def resolve_output(path: Path) -> Path:
    """If the target file is locked (open in Word), fall back to a versioned name."""
    if not path.exists():
        return path
    try:
        with open(path, "ab"):
            pass
        return path
    except PermissionError:
        i = 2
        while True:
            alt = path.with_name(f"{path.stem}_v{i}{path.suffix}")
            if not alt.exists():
                return alt
            try:
                with open(alt, "ab"):
                    pass
                return alt
            except PermissionError:
                i += 1

ACCENT = RGBColor(0x1F, 0x4E, 0x79)  # deep blue used in the original PDF


def set_cell_shading(cell, color_hex):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tc_pr.append(shd)


def set_cell_borders(cell, color_hex="1F4E79", size="8"):
    tc_pr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        b = OxmlElement(f"w:{edge}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), size)
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), color_hex)
        tcBorders.append(b)
    tc_pr.append(tcBorders)


def add_figure_image(doc, image_path: Path, label: str, description: str, max_width_cm: float = 15.5):
    """Embed an actual PNG figure with caption beneath."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.add_picture(str(image_path), width=Cm(max_width_cm))

    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    cap.paragraph_format.left_indent = Cm(0.4)
    cap.paragraph_format.right_indent = Cm(0.4)
    cap.paragraph_format.space_before = Pt(2)
    cap.paragraph_format.space_after = Pt(10)
    r = cap.add_run(f"{label}. ")
    r.bold = True
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x40, 0x40, 0x40)
    r2 = cap.add_run(description)
    r2.italic = True
    r2.font.size = Pt(9)
    r2.font.color.rgb = RGBColor(0x40, 0x40, 0x40)


def add_figure_placeholder(doc, label, description, height_cm=9.0):
    """Insert a bordered, fixed-height reserved-space box for a figure/map,
    followed by the descriptive caption."""
    # Bordered box
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    row = table.rows[0]
    row.height = Cm(height_cm)
    # set exact row height
    trHeight = OxmlElement("w:trHeight")
    trHeight.set(qn("w:val"), str(int(height_cm * 567)))  # cm to twips approx
    trHeight.set(qn("w:hRule"), "exact")
    trPr = row._tr.get_or_add_trPr()
    trPr.append(trHeight)

    cell = row.cells[0]
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    set_cell_shading(cell, "FAFAFA")
    set_cell_borders(cell, color_hex="B0B0B0", size="6")
    # Clear default paragraph and add placeholder text
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"[ {label} — insert image here ]")
    r.italic = True
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0x90, 0x90, 0x90)

    # Caption paragraph beneath
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    cap.paragraph_format.left_indent = Cm(0.4)
    cap.paragraph_format.right_indent = Cm(0.4)
    cap.paragraph_format.space_before = Pt(2)
    cap.paragraph_format.space_after = Pt(10)
    r = cap.add_run(f"{label}. ")
    r.bold = True
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x40, 0x40, 0x40)
    r2 = cap.add_run(description)
    r2.italic = True
    r2.font.size = Pt(9)
    r2.font.color.rgb = RGBColor(0x40, 0x40, 0x40)


def add_inline(paragraph, text):
    """Parse **bold**, *italic*, and `code` runs into a paragraph."""
    # tokenize on **...** then *...* then `...`
    pattern = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            paragraph.add_run(text[pos:m.start()])
        tok = m.group(0)
        if tok.startswith("**"):
            r = paragraph.add_run(tok[2:-2])
            r.bold = True
        elif tok.startswith("`"):
            r = paragraph.add_run(tok[1:-1])
            r.font.name = "Consolas"
        else:
            r = paragraph.add_run(tok[1:-1])
            r.italic = True
        pos = m.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def is_table_row(line):
    return line.strip().startswith("|") and line.strip().endswith("|")


def is_table_separator(line):
    return bool(re.match(r"\s*\|[\s\-:|]+\|\s*$", line))


def parse_table(lines, i):
    """Returns (rows, new_index). rows[0] is the header row."""
    rows = []
    while i < len(lines) and is_table_row(lines[i]):
        # skip separator
        if is_table_separator(lines[i]):
            i += 1
            continue
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        rows.append(cells)
        i += 1
    return rows, i


def add_table(doc, rows):
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    # normalize row lengths
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    table = doc.add_table(rows=len(rows), cols=ncols)
    table.style = "Light Grid Accent 1"
    table.autofit = True
    for r_idx, row in enumerate(rows):
        for c_idx, cell_text in enumerate(row):
            cell = table.rows[r_idx].cells[c_idx]
            # clear existing
            cell.text = ""
            p = cell.paragraphs[0]
            add_inline(p, cell_text)
            if r_idx == 0:
                # header row: bold + shading
                for run in p.runs:
                    run.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                set_cell_shading(cell, "1F4E79")
    # spacing after table
    doc.add_paragraph()


def configure_styles(doc):
    styles = doc.styles

    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    for lvl, size, color, italic, space_before, space_after in [
        ("Title", 28, ACCENT, False, 0, 18),
        ("Heading 1", 22, ACCENT, False, 18, 6),
        ("Heading 2", 16, ACCENT, False, 12, 4),
        ("Heading 3", 13, ACCENT, True, 8, 2),
    ]:
        s = styles[lvl]
        s.font.name = "Calibri"
        s.font.size = Pt(size)
        s.font.color.rgb = color
        s.font.bold = True
        s.font.italic = italic
        s.paragraph_format.space_before = Pt(space_before)
        s.paragraph_format.space_after = Pt(space_after)


def add_horizontal_rule(doc):
    p = doc.add_paragraph()
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "1F4E79")
    pBdr.append(bottom)
    pPr.append(pBdr)


def is_list_item(line):
    return bool(re.match(r"^\s*[-*]\s+", line)) or bool(re.match(r"^\s*\d+\.\s+", line))


def list_item_text(line):
    m = re.match(r"^\s*[-*]\s+(.*)$", line)
    if m:
        return ("bullet", m.group(1))
    m = re.match(r"^\s*\d+\.\s+(.*)$", line)
    if m:
        return ("number", m.group(1))
    return None


def main():
    md = SRC.read_text(encoding="utf-8").splitlines()
    doc = Document()
    configure_styles(doc)

    # A4 portrait with reasonable margins
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)

    i = 0
    in_math = False
    math_buffer = []

    while i < len(md):
        line = md[i]
        stripped = line.strip()

        # fenced math
        if stripped.startswith("$$"):
            # toggle
            if not in_math:
                in_math = True
                math_buffer = []
                # content after $$ on same line?
                rest = stripped[2:].strip()
                if rest.endswith("$$"):
                    # single-line math
                    math_buffer.append(rest[:-2].strip())
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r = p.add_run(math_buffer[0])
                    r.italic = True
                    r.font.name = "Cambria Math"
                    in_math = False
                elif rest:
                    math_buffer.append(rest)
                i += 1
                continue
            else:
                # closing
                content = " ".join(math_buffer).strip()
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = p.add_run(content)
                r.italic = True
                r.font.name = "Cambria Math"
                in_math = False
                math_buffer = []
                i += 1
                continue
        if in_math:
            math_buffer.append(stripped)
            i += 1
            continue

        # blank line
        if not stripped:
            i += 1
            continue

        # horizontal rule
        if stripped == "---":
            add_horizontal_rule(doc)
            i += 1
            continue

        # headings
        if stripped.startswith("# "):
            doc.add_heading(stripped[2:].strip(), level=0)
            i += 1
            continue
        if stripped.startswith("## "):
            doc.add_heading(stripped[3:].strip(), level=1)
            i += 1
            continue
        if stripped.startswith("### "):
            doc.add_heading(stripped[4:].strip(), level=2)
            i += 1
            continue
        if stripped.startswith("#### "):
            doc.add_heading(stripped[5:].strip(), level=3)
            i += 1
            continue

        # blockquote
        if stripped.startswith("> "):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.right_indent = Cm(0.6)
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            # collect contiguous quote lines
            quote_lines = []
            while i < len(md) and md[i].strip().startswith("> "):
                quote_lines.append(md[i].strip()[2:])
                i += 1
            text = " ".join(quote_lines)
            add_inline(p, text)
            for run in p.runs:
                run.italic = True
            # shade
            pPr = p._p.get_or_add_pPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), "E8EEF7")
            pPr.append(shd)
            continue

        # table
        if is_table_row(line):
            rows, i = parse_table(md, i)
            # filter separator if present in middle
            rows = [r for r in rows if not all(re.match(r"^[\s\-:]+$", c) for c in r)]
            add_table(doc, rows)
            continue

        # list (could span multiple lines)
        if is_list_item(line):
            while i < len(md) and is_list_item(md[i]):
                kind_text = list_item_text(md[i])
                if kind_text is None:
                    break
                kind, text = kind_text
                style = "List Bullet" if kind == "bullet" else "List Number"
                p = doc.add_paragraph(style=style)
                add_inline(p, text)
                i += 1
            continue

        # paragraph (collect until blank line)
        para_lines = [stripped]
        i += 1
        while i < len(md):
            nxt = md[i]
            if (not nxt.strip()) or nxt.strip().startswith("#") or nxt.strip().startswith("---") \
                or nxt.strip().startswith("> ") or is_table_row(nxt) or is_list_item(nxt) \
                or nxt.strip().startswith("$$"):
                break
            para_lines.append(nxt.strip())
            i += 1
        full = " ".join(para_lines)
        p = doc.add_paragraph()
        # detect italic-wrapped figure / table captions: starts with ***...*** or *[...]*
        if full.startswith("***") and full.endswith("***"):
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(full[3:-3])
            r.italic = True
            r.bold = True
            r.font.size = Pt(10)
        elif full.startswith("*[") and full.endswith("]*"):
            # figure / map placeholder — embed PNG if available, otherwise reserved box
            inner = full[2:-2]  # strip *[ and ]*
            m = re.match(r"^(FIGURE|MAP)\s+([\d.]+)\s*:\s*(.*)$", inner, re.IGNORECASE)
            if m:
                kind = m.group(1).upper()
                num = m.group(2)
                desc = m.group(3)
                label = f"{kind} {num}"
                # remove the empty paragraph we just opened
                p._element.getparent().remove(p._element)
                key = (kind, num)
                fname = FIGURE_FILES.get(key)
                image_path = (FIGURES_DIR / fname) if fname else None
                if image_path and image_path.is_file():
                    width_cm = 14.0 if kind == "MAP" else 15.5
                    add_figure_image(doc, image_path, label, desc, max_width_cm=width_cm)
                else:
                    height = 11.0 if kind == "MAP" else 9.0
                    add_figure_placeholder(doc, label, desc, height_cm=height)
                continue
            else:
                # fall back: treat as italic note
                p.paragraph_format.left_indent = Cm(0.4)
                p.paragraph_format.right_indent = Cm(0.4)
                r = p.add_run(inner)
                r.italic = True
                r.font.color.rgb = RGBColor(0x70, 0x70, 0x70)
                pPr = p._p.get_or_add_pPr()
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:color"), "auto")
                shd.set(qn("w:fill"), "F2F2F2")
                pPr.append(shd)
        elif full.startswith("*") and full.endswith("*") and not full.startswith("**"):
            r = p.add_run(full[1:-1])
            r.italic = True
        else:
            add_inline(p, full)
        p.alignment = p.alignment or WD_ALIGN_PARAGRAPH.JUSTIFY

    out_path = resolve_output(OUT)
    doc.save(out_path)
    if out_path != OUT:
        print(f"Note: {OUT.name} is locked (open in Word). Wrote to {out_path.name} instead.")
    else:
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
