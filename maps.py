import re
import pandas as pd
from fpdf import FPDF

def extract_map_data(text):
    data = []
    pattern = r"([^|\n]+)\|\s*(-?\d+\.?\d+)\s*\|\s*(-?\d+\.?\d+)"
    matches = re.findall(pattern, text)
    for match in matches:
        try:
            raw_name = match[0].strip()
            name = re.sub(r"[\*\-\[\]]", "", raw_name).strip()
            lat = float(match[1])
            lon = float(match[2])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                data.append({"name": name, "lat": lat, "lon": lon})
        except ValueError:
            continue
    if data:
        return pd.DataFrame(data)
    return pd.DataFrame()


def clean_text_for_pdf(text):
    return text.encode('latin-1', 'ignore').decode('latin-1')


def create_pdf(destination, content):
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            clean_dest = clean_text_for_pdf(destination)
            self.cell(0, 10, f'Travel Intel: {clean_dest}', 0, 1, 'C')
            self.ln(10)

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_content = clean_text_for_pdf(content)
    clean_content = clean_content.split("(---PAGE BREAK---)")[0]
    clean_content = re.sub(r'\*\*(.*?)\*\*', r'\1', clean_content)
    lines = clean_content.split('\n')
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.startswith('## '):
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, stripped_line.replace('## ', ''), 0, 1)
            pdf.set_font("Arial", size=12)
        elif stripped_line.startswith('* '):
            pdf.multi_cell(0, 8, f"  - {stripped_line.replace('* ', '')}")
        else:
            pdf.multi_cell(0, 8, stripped_line)
    return pdf.output(dest='S').encode('latin-1', 'ignore')
