import os
import re
from urllib.parse import urlparse

from fpdf import FPDF

# Guides are Markdown for reading, then a machine-readable block of map points:
#
#   ## Gastronomy ...
#   (---PAGE BREAK---)
#   ### COORDINATES
#   Le Marais | 48.8566 | 2.3622
PAGE_BREAK = re.compile(r"\(?-{3}\s*page break\s*-{3}\)?", re.IGNORECASE)
POINT = re.compile(r"([^|\n]+)\|\s*(-?\d+(?:\.\d+)?)\s*\|\s*(-?\d+(?:\.\d+)?)")

# DejaVu Sans ships with the repo (Bitstream Vera licence, see pdf-fonts/LICENSE.txt).
FONT_DIR = os.getenv("PDF_FONT_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf-fonts"))


def guide_body(text):
    """The readable part of a guide, without the coordinates block."""
    return PAGE_BREAK.split(text, maxsplit=1)[0].rstrip()


def extract_map_data(text):
    """[{'name', 'lat', 'lon'}] from the coordinates block (or anywhere, for older guides)."""
    parts = PAGE_BREAK.split(text, maxsplit=1)
    source = parts[1] if len(parts) > 1 else text
    points = []
    for raw_name, lat, lon in POINT.findall(source):
        name = re.sub(r"[*\-\[\]#]", "", raw_name).strip()
        lat, lon = float(lat), float(lon)
        if name and -90 <= lat <= 90 and -180 <= lon <= 180:
            points.append({"name": name, "lat": lat, "lon": lon})
    return points


def source_label(url):
    host = urlparse(url).netloc
    return host[4:] if host.startswith("www.") else host or url


def compose_guide(body, sources=(), locations=()):
    """Rebuild a guide from its readable body, the research sources and map points."""
    text = guide_body(body)
    if sources:
        text += "\n\n## Sources\n" + "\n".join(f"* [{source_label(url)}]({url})" for url in sources)
    if locations:
        text += "\n\n(---PAGE BREAK---)\n\n### COORDINATES\n" + "\n".join(
            f"{loc['name']} | {loc['lat']} | {loc['lon']}" for loc in locations)
    return text


def _plain(line, keep_bold=False):
    """Markdown inline formatting for the PDF: [label](url) -> label (url), *italic* -> italic,
    and **bold** kept for fpdf2's own markdown (or removed)."""
    line = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1 (\2)", line)
    line = line.replace("--", "–").replace("__", "_")  # fpdf2 reads these as underline/italic markers
    if not keep_bold:
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
    return re.sub(r"(?<![\w*])\*(?!\*)(\S.*?)(?<!\*)\*(?![\w*])", r"\1", line)


def create_pdf(destination, content):
    pdf = FPDF()
    regular = os.path.join(FONT_DIR, "DejaVuSans.ttf")
    bold = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
    if os.path.exists(regular) and os.path.exists(bold):
        pdf.add_font("Body", "", regular)
        pdf.add_font("Body", "B", bold)
        font, clean = "Body", (lambda s: s)
    else:  # core fonts only cover Latin-1
        font, clean = "Helvetica", (lambda s: s.encode("latin-1", "replace").decode("latin-1"))

    pdf.set_margins(18, 18, 18)
    pdf.add_page()
    pdf.set_font(font, "B", 18)
    pdf.multi_cell(0, 10, clean(f"Travel guide: {destination}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for raw in guide_body(content).split("\n"):
        line = raw.strip()
        if not line:
            pdf.ln(2)
            continue
        heading = re.match(r"^#{1,6}\s+(.*)$", line)
        if heading:
            pdf.ln(3)
            pdf.set_font(font, "B", 13)
            pdf.multi_cell(0, 8, clean(_plain(heading.group(1))), new_x="LMARGIN", new_y="NEXT")
            continue
        pdf.set_font(font, "", 11)
        item = re.match(r"^[*-]\s+(.*)$", line)
        text = f"•  {_plain(item.group(1), keep_bold=True)}" if item else _plain(line, keep_bold=True)
        pdf.multi_cell(0, 6.5, clean(text), new_x="LMARGIN", new_y="NEXT", markdown=True)
    return bytes(pdf.output())
