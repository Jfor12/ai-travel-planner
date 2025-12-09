import os
import re
import math
import unicodedata
import pandas as pd
import pydeck as pdk
from fpdf import FPDF
from urllib.parse import quote_plus


def display_labeled_map(df):
    if df.empty:
        try:
            import streamlit as st
            st.warning("No coordinates found to map.")
        except Exception:
            pass
        return

    midpoint = (df["lat"].mean(), df["lon"].mean())
    view_state = pdk.ViewState(latitude=midpoint[0], longitude=midpoint[1], zoom=11, pitch=0)

    df = df.copy()
    offsets_x = [0] * len(df)
    offsets_y = [0] * len(df)
    text_sizes = [14] * len(df)

    threshold_deg = 0.002
    coords = list(zip(df['lat'].tolist(), df['lon'].tolist()))
    for i, (lat_i, lon_i) in enumerate(coords):
        neighbors = []
        for j, (lat_j, lon_j) in enumerate(coords):
            if i == j:
                continue
            if abs(lat_i - lat_j) <= threshold_deg and abs(lon_i - lon_j) <= threshold_deg:
                neighbors.append(j)

        if neighbors:
            group_size = 1 + len(neighbors)
            idx_in_group = sorted([i] + neighbors).index(i)
            angle = (2 * math.pi * idx_in_group) / group_size
            radius = 14 + 4 * min(4, group_size)
            offsets_x[i] = int(radius * math.cos(angle))
            offsets_y[i] = int(radius * math.sin(angle))
            text_sizes[i] = max(10, 14 - group_size)

    df['offset_x'] = offsets_x
    df['offset_y'] = offsets_y
    df['text_size'] = text_sizes
    halo_layer = pdk.Layer("ScatterplotLayer", data=df, get_position='[lon, lat]', get_fill_color=[255, 75, 75, 120], get_radius=150, pickable=False)
    df['pin'] = '📍'
    pin_layer = pdk.Layer("TextLayer", data=df, get_position='[lon, lat]', get_text='pin', get_color=[255, 75, 75, 255], get_size=28, get_alignment_baseline="'center'", get_pixel_offset='[0, 0]')
    text_shadow_layer = pdk.Layer("TextLayer", data=df, get_position='[lon, lat]', get_text='name', get_color=[0, 0, 0, 200], get_size='text_size', get_alignment_baseline="'bottom'", get_pixel_offset='[offset_x + 1, offset_y + 1]')
    text_layer = pdk.Layer("TextLayer", data=df, get_position='[lon, lat]', get_text='name', get_color=[255, 255, 255, 230], get_size='text_size', get_alignment_baseline="'bottom'", get_pixel_offset='[offset_x, offset_y]')

    mb_token = os.getenv("MAPBOX_API_KEY") or os.getenv("MAPBOX_TOKEN") or os.getenv("MAPBOX_API_TOKEN")
    deck_kwargs = {}
    if mb_token:
        deck_kwargs = {"mapbox_key": mb_token}
        map_style = 'mapbox://styles/mapbox/dark-v10'
    else:
        map_style = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'

    layers = [halo_layer, pin_layer, text_shadow_layer, text_layer]
    deck_args = {"initial_view_state": view_state, "layers": layers, "tooltip": {"text": "{name}"}}
    if map_style:
        deck_args["map_style"] = map_style
    deck_args.update(deck_kwargs)

    import streamlit as st
    st.pydeck_chart(pdk.Deck(**deck_args))


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


def get_location_summaries(text, names, max_len=140):
    summaries = []
    if not text or not names:
        return summaries
    clean_text = re.sub(r"(?mi)^\s*#{1,3}\s*COORDINATES.*$(?:\n(?:.*\|.*\|.*$))*", "", text)
    clean_text = re.sub(r"(?m)^[^\n|]+\|\s*-?\d+\.?\d*\s*\|\s*-?\d+\.?\d*\s*$", "", clean_text)
    sentences = re.split(r'(?<=[.!?])\s+', clean_text)
    lower_sentences = [s.lower() for s in sentences]

    def strip_accents(s: str) -> str:
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    lower_sentences_norm = [strip_accents(s) for s in lower_sentences]
    lines = [l.strip() for l in clean_text.splitlines() if l.strip()]
    paragraphs = [p.strip() for p in clean_text.split('\n\n') if p.strip()]

    def shortify(s, max_words=10):
        s = s.strip()
        if not s:
            return s
        words = s.split()
        if len(words) <= max_words:
            return s
        parts = re.split(r'(?<=[.!?])\s+', s)
        if parts and len(parts[0].split()) <= max_words:
            return parts[0].strip() + '...'
        clauses = [p.strip() for p in s.split(',') if p.strip()]
        if len(clauses) >= 2:
            short = ', '.join(clauses[:2])
        else:
            short = clauses[0] if clauses else s
        short_words = short.split()
        if len(short_words) > max_words:
            return ' '.join(short_words[:max_words]) + '...'
        return short + '...'

    alias_map = {
        "colosseum": ["colosseo", "il colosseo", "colosseum"],
        "grand palace": ["grand palace", "the grand palace"],
        "eiffel tower": ["eiffel tower", "la tour eiffel", "tour eiffel"],
    }

    for name in names:
        name_l = name.lower()
        name_norm = strip_accents(name_l)
        desc = ""
        label_re = re.compile(rf"(?mi)^\s*(?:\*\*|\*|\-|\u2022\s*)*{re.escape(name)}\s*[:\-–—]\s*(.+)$")
        for ln in lines:
            m = label_re.match(ln)
            if m:
                desc = m.group(1).strip()
                break
        if not desc:
            pattern = re.compile(rf"(?mi)\*\s*\*\*?\s*{re.escape(name)}\*\*?\s*[:\-–—]?\s*(.+)")
            for ln in lines:
                m = pattern.search(ln)
                if m:
                    desc = m.group(1).strip()
                    break
        if not desc:
            for idx, s_lower in enumerate(lower_sentences):
                if name_l in s_lower or any(a in s_lower for a in alias_map.get(name_l, [])):
                    desc = sentences[idx].strip()
                    break
            if not desc:
                for idx, s_norm in enumerate(lower_sentences_norm):
                    if name_norm in s_norm or any(strip_accents(a) in s_norm for a in alias_map.get(name_l, [])):
                        desc = sentences[idx].strip()
                        break
        if not desc:
            for p in paragraphs:
                p_l = p.lower()
                if name_l in p_l or any(a in p_l for a in alias_map.get(name_l, [])):
                    desc = p.split('\n')[0].strip()
                    break
            if not desc:
                for p in paragraphs:
                    p_norm = strip_accents(p.lower())
                    if name_norm in p_norm or any(strip_accents(a) in p_norm for a in alias_map.get(name_l, [])):
                        desc = p.split('\n')[0].strip()
                        break
        if not desc:
            name_tokens = [t for t in re.findall(r"\w+", name_norm) if len(t) > 2]
            best_score = 0
            best_idx = None
            for idx, s_lower in enumerate(lower_sentences):
                if not s_lower:
                    continue
                s_norm = lower_sentences_norm[idx]
                match_count = sum(1 for t in name_tokens if t in s_norm)
                score = match_count / max(1, len(name_tokens))
                if score > best_score:
                    best_score = score
                    best_idx = idx
            if best_score >= 0.4 and best_idx is not None:
                desc = sentences[best_idx].strip()
        if desc:
            desc = re.sub(r"\|\s*-?\d+\.?\d*\s*\|\s*-?\d+\.?\d*", "", desc)
            desc = re.sub(r"\*\*(.*?)\*\*", r"\1", desc)
            desc = re.sub(r"\*(.*?)\*", r"\1", desc)
            desc = re.sub(r"^\s*#{1,6}\s*", "", desc)
            desc = re.sub(r"^[\W_]+", "", desc)
            desc = re.sub(r"^(?:🏘️\s*)?(?:Neighborhoods|Gastronomy|COORDINATES|COORDINATE|Coordinates)[:\-\s]*", "", desc, flags=re.I)
            try:
                desc = re.sub(rf"^\s*{re.escape(name)}\s*[:\-–—]\s*", "", desc, flags=re.I)
            except re.error:
                pass
            desc = re.sub(r"\s{2,}", " ", desc).strip()
            if not desc or desc.lower() == name_l or len(desc.split()) < 3:
                desc = ""
            else:
                desc = shortify(desc, max_words=10)
        if not desc:
            desc = "No short description available."
        summaries.append({"name": name, "desc": desc})
    return summaries


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


def wikipedia_search_url(name, dest=None):
    query = name
    if dest:
        try:
            city = dest.split(',')[0]
            query = f"{name} {city}"
        except Exception:
            query = name
    return f"https://en.wikipedia.org/wiki/Special:Search?search={quote_plus(query)}"


def place_reference_url(name, dest=None, coords=None):
    if coords and isinstance(coords, (list, tuple)) and len(coords) == 2:
        lat, lon = coords
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            return f"https://www.google.com/maps/search/?api=1&query={lat_f},{lon_f}"
        except Exception:
            pass
    query = name
    if dest:
        try:
            city = dest.split(',')[0]
            query = f"{name} {city}"
        except Exception:
            query = name
    search_q = quote_plus(f"site:wikipedia.org {query}")
    return f"https://www.google.com/search?q={search_q}"
