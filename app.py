import streamlit as st
import os
import psycopg
import pandas as pd
import re
import unicodedata
import pydeck as pdk  # <--- ADDED THIS IMPORT
import math
from urllib.parse import quote_plus
from datetime import datetime
from fpdf import FPDF

# 1. IMPORTS CHECK
try:
    from langchain_groq import ChatGroq
    from langchain_community.tools import TavilySearchResults
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from streamlit_option_menu import option_menu
except ImportError as e:
    st.error(f"❌ Missing Library: {e}")
    st.stop()

# 2. PAGE CONFIG
st.set_page_config(page_title="Travel Strategy AI", page_icon="🧠", layout="wide")

# 3. LOAD SECRETS
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- CONSTANTS ---
POPULAR_CITIES = [
    "Paris, France", "London, UK", "New York, USA", "Tokyo, Japan", 
    "Rome, Italy", "Sydney, Australia", "Cape Town, South Africa", 
    "Rio de Janeiro, Brazil", "Dubai, UAE", "Singapore", "Barcelona, Spain",
    "Kyoto, Japan", "Bangkok, Thailand", "Istanbul, Turkey", "Marrakech, Morocco",
    "Lisbon, Portugal", "Seoul, South Korea", "Mexico City, Mexico"
]

MONTHS = [
    "January", "February", "March", "April", "May", "June", 
    "July", "August", "September", "October", "November", "December"
]

# 4. DATABASE CONNECTION
def get_connection():
    db_url = os.getenv('DATABASE_URL')
    if not db_url: return None
    try:
        return psycopg.connect(db_url, sslmode='require')
    except Exception: return None

# 5. DATABASE FUNCTIONS
def save_itinerary(dest, month, text):
    conn = get_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO saved_itineraries (destination, trip_days, itinerary_text)
                VALUES (%s, %s, %s)
            """, (f"{dest} [{month}]", 0, text))
            conn.commit()
        conn.close()
        st.toast("✅ Intel Saved!")

def update_itinerary(trip_id, new_text):
    conn = get_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE saved_itineraries SET itinerary_text = %s WHERE id = %s", (new_text, trip_id))
            conn.commit()
        conn.close()
        st.toast("✅ Updated!")

def delete_itinerary(trip_id):
    conn = get_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM saved_itineraries WHERE id = %s", (trip_id,))
            conn.commit()
        conn.close()
        st.toast("🗑️ Deleted!")

def get_history():
    conn = get_connection()
    if not conn: return []
    with conn.cursor() as cur:
        cur.execute("SELECT id, destination, created_at FROM saved_itineraries ORDER BY created_at DESC")
        return cur.fetchall()

def get_itinerary_details(trip_id):
    conn = get_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("SELECT destination, itinerary_text FROM saved_itineraries WHERE id = %s", (trip_id,))
            return cur.fetchone()
    return None

def save_chat_message(trip_id, role, content):
    conn = get_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO trip_chats (trip_id, role, content)
                VALUES (%s, %s, %s)
            """, (trip_id, role, content))
            conn.commit()
        conn.close()

def load_chat_history(trip_id):
    conn = get_connection()
    if not conn: return []
    with conn.cursor() as cur:
        cur.execute("""
            SELECT role, content FROM trip_chats 
            WHERE trip_id = %s 
            ORDER BY created_at ASC
        """, (trip_id,))
        rows = cur.fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]

# 6. AI GENERATION LOGIC
def generate_intel(destination, month):
    groq_api = os.getenv("GROQ_API_KEY")
    tavily_api = os.getenv("TAVILY_API_KEY")

    if not groq_api or not tavily_api:
        st.error("❌ Keys missing.")
        st.stop()

    search_query = f"""
    cultural etiquette and tipping rules {destination}
    must eat local dishes food guide {destination} not restaurants
    neighborhood guide {destination} vibe check
    weather and packing tips {destination} in {month}
    common tourist scams {destination}
    coordinates of major neighborhoods {destination}
    """
    
    tavily = TavilySearchResults(max_results=3)
    search_docs = tavily.invoke(search_query)
    search_context = "\n".join([f"- {d['content']} (Source: {d['url']})" for d in search_docs])

    llm = ChatGroq(
        groq_api_key=groq_api,
        model_name=st.session_state.get('groq_model_gen', os.getenv('GROQ_MODEL_INTEL', 'llama-3.3-70b-versatile')),
        temperature=float(st.session_state.get('groq_temp_gen', os.getenv('GROQ_TEMP_INTEL', '0.3')))
    )

    prompt = ChatPromptTemplate.from_template("""
    You are a cynical, expert local guide. Provide "Ground Truth" intelligence.
    
    CONTEXT:
    {context}
    
    REQUEST:
    Destination: {destination}
    Month: {month}
    
    STRICT RULES:
    1. FOOD & NEIGHBORHOODS: Must come from Context or static knowledge.
    2. WEATHER: If Context missing, use INTERNAL KNOWLEDGE for averages.
    3. NO FLUFF.
    
    FORMAT (Markdown):
    
    ## 🍝 Gastronomy (What to order)
    * **[Dish]:** [Desc].
    
    ## 🏘️ Neighborhoods
    * **[Area]:** [Vibe].
    
    ## ⚠️ Logistics
    * **Tips:** [Rule].
    * **Transport:** [Best method].
    * **Safety:** [Scams].
    
    ## 🎒 Seasonal ({month})
    * **Weather:** [Avg Temp/Rain].
    * **Crowds:** [High/Low].

    (---PAGE BREAK---)
    
    ### COORDINATES
    List 3-4 major locations or districts mentioned above in this exact format: Name | Latitude | Longitude
    Example:
    Eiffel Tower Sector | 48.8584 | 2.2945
    Le Marais | 48.8566 | 2.3522
    """)

    chain = prompt | llm | StrOutputParser()
    return chain.stream({"context": search_context, "destination": destination, "month": month})

def run_chat_response(guide_context, user_query):
    groq_api = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(
        groq_api_key=groq_api,
        model_name=st.session_state.get('groq_model_chat', os.getenv('GROQ_MODEL_CHAT', 'llama-3.1-8b-instant')),
        temperature=float(st.session_state.get('groq_temp_chat', os.getenv('GROQ_TEMP_CHAT', '0.5')))
    )
    
    prompt = ChatPromptTemplate.from_template("""
    You are a helpful assistant answering questions about a specific travel guide.
    
    THE GUIDE:
    {guide_context}
    
    USER QUESTION:
    {user_query}
    
    Answer based ONLY on the information in the guide provided above. If the answer is not in the guide, say "That information is not in this specific briefing." Keep answers concise.
    """)
    
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"guide_context": guide_context, "user_query": user_query})
    return response


def run_gen_response(guide_context, user_query):
    """Run the generation model (selected in sidebar) with the guide as context.
    Returns the model's string response.
    """
    groq_api = os.getenv("GROQ_API_KEY")
    if not groq_api:
        return ""

    llm = ChatGroq(
        groq_api_key=groq_api,
        model_name=st.session_state.get('groq_model_gen', os.getenv('GROQ_MODEL_INTEL', 'llama-3.3-70b-versatile')),
        temperature=float(st.session_state.get('groq_temp_gen', os.getenv('GROQ_TEMP_INTEL', '0.3')))
    )

    prompt = ChatPromptTemplate.from_template("""
    You are a concise assistant that extracts or summarizes information from the provided guide.

    THE GUIDE:
    {guide_context}

    USER REQUEST:
    {user_query}

    Answer concisely and only using information in the guide. If the guide does not mention the requested item, reply exactly: No short description available.
    """)

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"guide_context": guide_context, "user_query": user_query})

# ==========================================
# 4. UTILITY LAYER (Map & PDF)
# ==========================================

# --- NEW MAP FUNCTION ---
def display_labeled_map(df):
    """
    Displays a map with red dots and text labels using PyDeck.
    """
    if df.empty:
        st.warning("No coordinates found to map.")
        return

    # 1. Determine Center of Map
    midpoint = (df["lat"].mean(), df["lon"].mean())

    # 2. Set the View State
    view_state = pdk.ViewState(
        latitude=midpoint[0],
        longitude=midpoint[1],
        zoom=11,
        pitch=0,
    )

    # compute small pixel offsets for labels when points are clustered
    # to reduce overlap: for clusters of nearby points, place labels around a circle
    df = df.copy()
    offsets_x = [0] * len(df)
    offsets_y = [0] * len(df)
    text_sizes = [14] * len(df)

    # threshold in degrees (approx). 0.002 ~= ~200m depending on latitude
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
            # position this label around a small circle based on its index among neighbors
            idx_in_group = sorted([i] + neighbors).index(i)
            angle = (2 * math.pi * idx_in_group) / group_size
            radius = 14 + 4 * min(4, group_size)
            offsets_x[i] = int(radius * math.cos(angle))
            offsets_y[i] = int(radius * math.sin(angle))
            text_sizes[i] = max(10, 14 - group_size)

    df['offset_x'] = offsets_x
    df['offset_y'] = offsets_y
    df['text_size'] = text_sizes

    # 3. Create a colored halo layer for visibility (larger, semi-transparent)
    halo_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_fill_color=[255, 75, 75, 120],  # red translucent halo for contrast
        get_radius=150,
        pickable=False,
    )

    # 4. Create a pin icon layer using TextLayer with an emoji (works without external sprites)
    df['pin'] = '📍'
    pin_layer = pdk.Layer(
        "TextLayer",
        data=df,
        get_position='[lon, lat]',
        get_text='pin',
        get_color=[255, 75, 75, 255],  # red pin
        get_size=28,
        get_alignment_baseline="'center'",
        get_pixel_offset='[0, 0]'
    )

    # 5. Create a text shadow layer (for accessibility) and the main white text label
    text_shadow_layer = pdk.Layer(
        "TextLayer",
        data=df,
        get_position='[lon, lat]',
        get_text='name',
        get_color=[0, 0, 0, 200],  # black shadow
        get_size='text_size',
        get_alignment_baseline="'bottom'",
        get_pixel_offset='[offset_x + 1, offset_y + 1]'
    )

    text_layer = pdk.Layer(
        "TextLayer",
        data=df,
        get_position='[lon, lat]',
        get_text='name',
        get_color=[255, 255, 255, 230],  # white text for contrast
        get_size='text_size',
        get_alignment_baseline="'bottom'",
        get_pixel_offset='[offset_x, offset_y]'
    )

    # 5. Render
    # Map style: prefer Mapbox Dark when a token is available; otherwise use public Carto dark basemap
    mb_token = os.getenv("MAPBOX_API_KEY") or os.getenv("MAPBOX_TOKEN") or os.getenv("MAPBOX_API_TOKEN")
    # Use Mapbox dark style when a Mapbox token is available; otherwise use a public dark basemap
    deck_kwargs = {}
    if mb_token:
        deck_kwargs = {"mapbox_key": mb_token}
        map_style = 'mapbox://styles/mapbox/dark-v10'
    else:
        map_style = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'

    # assemble layers and include the text shadow layer for better label readability
    layers = [halo_layer, pin_layer, text_shadow_layer, text_layer]

    # Build deck args with chosen basemap style
    deck_args = {
        "initial_view_state": view_state,
        "layers": layers,
        "tooltip": {"text": "{name}"},
    }
    if map_style:
        deck_args["map_style"] = map_style
    # merge any deck kwargs (e.g., mapbox_key)
    deck_args.update(deck_kwargs)

    st.pydeck_chart(pdk.Deck(**deck_args))

def extract_map_data(text):
    data = []
    # Regex captures: Name | Lat | Lon
    pattern = r"([^|\n]+)\|\s*(-?\d+\.?\d+)\s*\|\s*(-?\d+\.?\d+)"
    
    matches = re.findall(pattern, text)
    
    for match in matches:
        try:
            raw_name = match[0].strip()
            # Clean up Markdown junk (e.g., "**Eiffel Tower**" -> "Eiffel Tower")
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
    """More robust extraction:
    - remove coordinate blocks
    - look for explicit labeled lines ("Name: desc", "**Name**: desc", list items)
    - prefer sentences containing the name (case-insensitive)
    - fallback to token-overlap scoring picking the best sentence
    - normalize and shortify the extracted description
    """
    summaries = []
    if not text or not names:
        return summaries

    # remove COORDINATES blocks and single-line coordinate lines
    clean_text = re.sub(r"(?mi)^\s*#{1,3}\s*COORDINATES.*$(?:\n(?:.*\|.*\|.*$))*", "", text)
    clean_text = re.sub(r"(?m)^[^\n|]+\|\s*-?\d+\.?\d*\s*\|\s*-?\d+\.?\d*\s*$", "", clean_text)

    # split into sentences and lines
    sentences = re.split(r'(?<=[.!?])\s+', clean_text)
    lower_sentences = [s.lower() for s in sentences]
    # accent-stripped versions for more robust matching (e.g., Sagrada Família -> sagrada familia)
    def strip_accents(s: str) -> str:
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    lower_sentences_norm = [strip_accents(s) for s in lower_sentences]
    lines = [l.strip() for l in clean_text.splitlines() if l.strip()]
    paragraphs = [p.strip() for p in clean_text.split('\n\n') if p.strip()]

    # helper shortify (prefer first sentence, then two clauses)
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

    # small alias map for common variants (extend as needed)
    alias_map = {
        "colosseum": ["colosseo", "il colosseo", "colosseum"],
        "grand palace": ["grand palace", "the grand palace"],
        "eiffel tower": ["eiffel tower", "la tour eiffel", "tour eiffel"],
    }

    for name in names:
        name_l = name.lower()
        name_norm = strip_accents(name_l)
        desc = ""

        # 1) explicit labeled line patterns (case-insensitive)
        label_re = re.compile(rf"(?mi)^\s*(?:\*\*|\*|\-|\u2022\s*)*{re.escape(name)}\s*[:\-–—]\s*(.+)$")
        for ln in lines:
            m = label_re.match(ln)
            if m:
                desc = m.group(1).strip()
                break

        # 2) list-style '**[Area]:** desc' from prompt patterns
        if not desc:
            pattern = re.compile(rf"(?mi)\*\s*\*\*?\s*{re.escape(name)}\*\*?\s*[:\-–—]?\s*(.+)")
            for ln in lines:
                m = pattern.search(ln)
                if m:
                    desc = m.group(1).strip()
                    break

        # 3) sentence-level exact match (case-insensitive); also try accent-stripped matching
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

        # 4) paragraph-level match (also try accent-stripped)
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

        # 5) token-overlap fuzzy match: pick sentence with best token overlap
        if not desc:
            name_tokens = [t for t in re.findall(r"\w+", name_norm) if len(t) > 2]
            best_score = 0
            best_idx = None
            for idx, s_lower in enumerate(lower_sentences):
                if not s_lower: continue
                s_norm = lower_sentences_norm[idx]
                match_count = sum(1 for t in name_tokens if t in s_norm)
                score = match_count / max(1, len(name_tokens))
                if score > best_score:
                    best_score = score
                    best_idx = idx
            if best_score >= 0.4 and best_idx is not None:
                desc = sentences[best_idx].strip()

        # Clean extracted description
        if desc:
            # remove coordinate fragments and markdown markers
            desc = re.sub(r"\|\s*-?\d+\.?\d*\s*\|\s*-?\d+\.?\d*", "", desc)
            desc = re.sub(r"\*\*(.*?)\*\*", r"\1", desc)
            desc = re.sub(r"\*(.*?)\*", r"\1", desc)
            desc = re.sub(r"^\s*#{1,6}\s*", "", desc)
            desc = re.sub(r"^[\W_]+", "", desc)
            # remove leading section words/emojis
            desc = re.sub(r"^(?:🏘️\s*)?(?:Neighborhoods|Gastronomy|COORDINATES|COORDINATE|Coordinates)[:\-\s]*", "", desc, flags=re.I)
            # remove potential leading repeated name
            try:
                desc = re.sub(rf"^\s*{re.escape(name)}\s*[:\-–—]\s*", "", desc, flags=re.I)
            except re.error:
                pass
            desc = re.sub(r"\s{2,}", " ", desc).strip()
            # if desc too short or equals name, discard
            if not desc or desc.lower() == name_l or len(desc.split()) < 3:
                desc = ""
            else:
                desc = shortify(desc, max_words=10)

        if not desc:
            desc = "No short description available."

        summaries.append({"name": name, "desc": desc})

    return summaries


def generate_place_summary(guide_text, place_name):
    """Generate a concise one-line summary for a place using the chat LLM.
    Falls back to a standard message if generation fails or the guide lacks info.
    """
    try:
        # Ask the generation model a short question, passing the guide as the context
        user_question = f"Provide a concise one-line (max 15 words) description of '{place_name}' based ONLY on the guide provided. If the guide does not mention the place, reply exactly: No short description available. Keep answer brief and factual."
        response = run_gen_response(guide_text, user_question)
        clean = response.strip()
        if not clean or 'not in this specific briefing' in clean.lower() or 'no short description' in clean.lower():
            return "No short description available."
        # keep only first line and truncate to ~15 words if necessary
        first_line = clean.splitlines()[0]
        words = first_line.split()
        if len(words) > 15:
            return ' '.join(words[:15]) + '...'
        return first_line
    except Exception:
        return "No short description available."


# NOTE: coordinate-stripping is done inline where needed to avoid an extra helper function.

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
    """Return a Wikipedia search URL for a place name, optionally scoped to the destination city."""
    query = name
    if dest:
        try:
            city = dest.split(',')[0]
            query = f"{name} {city}"
        except Exception:
            query = name
    return f"https://en.wikipedia.org/wiki/Special:Search?search={quote_plus(query)}"


def place_reference_url(name, dest=None, coords=None):
    """Return a helpful reference URL for a place.
    - If `coords` (lat, lon) provided, return a Google Maps coordinate link (fast and direct).
    - Otherwise, fall back to a Google site:wikipedia.org search scoped to the city (more likely to hit the exact page).
    """
    if coords and isinstance(coords, (list, tuple)) and len(coords) == 2:
        lat, lon = coords
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            return f"https://www.google.com/maps/search/?api=1&query={lat_f},{lon_f}"
        except Exception:
            pass

    # Fallback: Google search targeted to Wikipedia (more likely to surface the encyclopedia page)
    query = name
    if dest:
        try:
            city = dest.split(',')[0]
            query = f"{name} {city}"
        except Exception:
            query = name
    search_q = quote_plus(f"site:wikipedia.org {query}")
    return f"https://www.google.com/search?q={search_q}"

# ==========================================
# 5. UI LAYER
# ==========================================

if 'active_trip_id' not in st.session_state:
    st.session_state['active_trip_id'] = None
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

with st.sidebar:
    selected = option_menu(
        menu_title=None, 
        options=["New Search", "My Library"],  
        icons=["search", "book"],  
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"font-size": "14px"}, 
            "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px", "--hover-color": "#262730"},
            "nav-link-selected": {"background-color": "#FF4B4B"},
        }
    )
    
    st.divider()

    # Sidebar simplified: model selection removed (use env vars or defaults)
    st.divider()

    if selected == "My Library" and st.session_state['active_trip_id']:
        st.caption("Trip Settings")
        edit_mode = st.toggle("Enable Editing", value=False)
        st.write("")
        if st.button("🗑️ Delete this Guide", type="primary"): 
            delete_itinerary(st.session_state['active_trip_id'])
            st.session_state['active_trip_id'] = None
            st.rerun()

# --- PAGE 1: NEW SEARCH ---
if selected == "New Search":
    st.session_state["chat_history"] = []
    
    st.title("🧠 Travel Intelligence AI")
    st.markdown("Your **Pre-Trip Strategic Briefing**.")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            destination = st.selectbox("Where are you going?", options=sorted(POPULAR_CITIES))
        with col2:
            current_idx = datetime.now().month - 1
            month = st.selectbox("Travel Month", MONTHS, index=current_idx)

    # Clear cached generated data if the user changed destination or month
    if (
        st.session_state.get('last_selected_dest') != destination
        or st.session_state.get('last_selected_month') != month
    ):
        for k in ['gen_summaries_new', 'temp_generated_full', 'temp_dest', 'temp_month']:
            if k in st.session_state:
                del st.session_state[k]
        st.session_state['last_selected_dest'] = destination
        st.session_state['last_selected_month'] = month

    if st.button("Generate Intelligence 🧠", type="primary"):
        st.subheader(f"Strategy for {destination} in {month}")
        response_container = st.empty()
        full_response = ""
        
        try:
            stream = generate_intel(destination, month)
            for chunk in stream:
                full_response += chunk
                clean_chunk = full_response.split("(---PAGE BREAK---)")[0]
                response_container.markdown(clean_chunk + "▌")
            
            final_display_text = full_response.split("(---PAGE BREAK---)")[0]
            # Strip any coordinate lists from the display (map already shows them)
            display_no_coords = re.sub(r"(?mi)^\s*#{1,3}\s*COORDINATES.*$(?:\n(?:.*\|.*\|.*$))*", "", final_display_text)
            # Replace 'Name | lat | lon' with just 'Name' (works inline or on separate lines)
            display_no_coords = re.sub(r"(?m)([^\n|]+?)\s*\|\s*-?\d+\.?\d*\s*\|\s*-?\d+\.?\d*", lambda m: m.group(1).strip(), display_no_coords)
            display_no_coords = re.sub(r"\n{3,}", "\n\n", display_no_coords).strip()
            response_container.markdown(display_no_coords)
            
            st.session_state['temp_generated_full'] = full_response
            st.session_state['temp_dest'] = destination
            st.session_state['temp_month'] = month
            
        except Exception as e:
            st.error(f"Error: {e}")

    if 'temp_generated_full' in st.session_state:
        map_df = extract_map_data(st.session_state['temp_generated_full'])
        
        st.divider()
        st.subheader("📍 Key Locations")

        # --- SHOW COMPACT LIST OF KEY LOCATIONS (NAME + SHORT DESCRIPTION) ---
        if not map_df.empty:
            # build summaries from the original generated content (keeps context for descriptions)
            raw_text = st.session_state.get('temp_generated_full', '')
            # deduplicate preserving order
            seen = set()
            loc_names = []
            for n in map_df['name']:
                if n not in seen:
                    seen.add(n)
                    loc_names.append(n)
            # Map style selection removed; render with default dark style

            # Show only place titles as quick reference links (avoids clutter)
            # map names to coordinates so we can prefer direct map links
            coords_by_name = {r['name']: (r['lat'], r['lon']) for _, r in map_df.iterrows()}
            for name in loc_names:
                coords = coords_by_name.get(name)
                url = place_reference_url(name, st.session_state.get('temp_dest'), coords=coords)
                st.markdown(f"- [{name}]({url})")

            # --- MAP VISUALIZATION UPDATED HERE ---
            display_labeled_map(map_df)
        else:
            st.warning("No coordinates found for map.")
            with st.expander("Debug: Check Raw Output"):
                st.text(st.session_state['temp_generated_full'])

        st.divider()
        if st.button("💾 Save to Library"):
            save_itinerary(
                st.session_state['temp_dest'],
                st.session_state['temp_month'],
                st.session_state['temp_generated_full']
            )
            del st.session_state['temp_generated_full']
            st.toast("Saved! Check 'My Library'")
            st.rerun()

# --- PAGE 2: MY LIBRARY ---
elif selected == "My Library":
    if st.session_state['active_trip_id'] is None:
        st.title("🗂️ My Saved Intel")
        history = get_history()
        if not history:
            st.info("No saved trips yet.")
        else:
            for i in range(0, len(history), 2):
                cols = st.columns(2)
                for j in range(2):
                    if i + j < len(history):
                        trip = history[i + j]
                        t_id, t_dest, t_date = trip
                        with cols[j].container(border=True):
                            st.subheader(t_dest)
                            st.caption(f"Created: {t_date.strftime('%Y-%m-%d')}")
                            if st.button(f"📂 Open Guide", key=f"open_{t_id}"):
                                st.session_state['active_trip_id'] = t_id
                                st.session_state["chat_history"] = []
                                st.rerun()
    else:
        trip_id = st.session_state['active_trip_id']
        data = get_itinerary_details(trip_id)
        
        if data:
            dest_title, full_content = data
            display_content = full_content.split("(---PAGE BREAK---)")[0]
            # Hide raw coordinate lists from the on-screen guide view
            display_content = re.sub(r"(?mi)^\s*#{1,3}\s*COORDINATES.*$(?:\n(?:.*\|.*\|.*$))*", "", display_content)
            # Replace 'Name | lat | lon' patterns with just the Name (keeps place names)
            display_content = re.sub(r"(?m)([^\n|]+?)\s*\|\s*-?\d+\.?\d*\s*\|\s*-?\d+\.?\d*", lambda m: m.group(1).strip(), display_content)
            display_content = re.sub(r"\n{3,}", "\n\n", display_content).strip()

            c1, c2, c3 = st.columns([6, 1, 1])
            with c1:
                st.title(f"✈️ {dest_title}")
            with c2:
                pdf_data = create_pdf(dest_title, full_content)
                st.download_button(label="📄 PDF", data=pdf_data, file_name=f"{dest_title}_Intel.pdf", mime='application/pdf')
            with c3:
                if st.button("❌ Close"):
                    st.session_state['active_trip_id'] = None
                    st.rerun()
            
            st.divider()
            
            if 'edit_mode' in locals() and edit_mode:
                with st.form("edit_form"):
                    new_text = st.text_area("Edit notes:", value=full_content, height=600)
                    if st.form_submit_button("💾 Save Updates", type="primary"):
                        update_itinerary(trip_id, new_text)
                        st.rerun()
            else:
                st.markdown(display_content)

                map_df = extract_map_data(full_content)

                st.divider()
                st.subheader("📍 Key Locations")

                # Show compact list of key locations above the map
                if not map_df.empty:
                    raw_text = full_content
                    # deduplicate preserving order
                    seen = set()
                    loc_names = []
                    for n in map_df['name']:
                        if n not in seen:
                            seen.add(n)
                            loc_names.append(n)
                    with st.container():
                        # Map style selection removed; render with default dark style

                        # Show only titles as links to reference (prefer Google Maps when coords exist)
                        coords_by_name = {r['name']: (r['lat'], r['lon']) for _, r in map_df.iterrows()}
                        for name in loc_names:
                            coords = coords_by_name.get(name)
                            url = place_reference_url(name, dest_title, coords=coords)
                            st.markdown(f"- [{name}]({url})")


                    # Map follows the summaries
                    display_labeled_map(map_df)
                else:
                    st.info("No map data available for this trip.")
                    # Fallback to empty labeled map structure if needed, or just skip
                    
                st.divider()
                st.subheader("💬 Chat with this Guide")

                for message in st.session_state["chat_history"]:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

                if prompt := st.chat_input("Ask a follow-up question..."):
                    st.session_state["chat_history"].append({"role": "user", "content": prompt})
                    with st.chat_message("user"):
                        st.markdown(prompt)

                    with st.chat_message("assistant"):
                        response = run_chat_response(display_content, prompt)
                        st.markdown(response)
                    
                    st.session_state["chat_history"].append({"role": "assistant", "content": response})
                    save_chat_message(trip_id, "user", prompt)
                    save_chat_message(trip_id, "assistant", response)

        else:
            st.error("Trip not found.")
            st.session_state['active_trip_id'] = None
            st.rerun()