import streamlit as st
import os
import psycopg
from datetime import datetime

# 1. IMPORTS
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
    """
    
    tavily = TavilySearchResults(max_results=3)
    search_docs = tavily.invoke(search_query)
    search_context = "\n".join([f"- {d['content']} (Source: {d['url']})" for d in search_docs])

    llm = ChatGroq(
        groq_api_key=groq_api,
        model_name="llama-3.3-70b-versatile",
        temperature=0.3
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
    """)

    chain = prompt | llm | StrOutputParser()
    return chain.stream({"context": search_context, "destination": destination, "month": month})

# --- STATE MANAGEMENT ---
if 'active_trip_id' not in st.session_state:
    st.session_state['active_trip_id'] = None

# ==========================================
# 🧭 MODERN SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    # 1. The Modern Menu (Transparent & Native Look)
    selected = option_menu(
        menu_title=None,  # Hide title to make it cleaner
        options=["New Search", "My Library"],  
        icons=["search", "book"],  
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"font-size": "14px"}, 
            "nav-link": {"font-size": "14px", "text-align": "left", "margin": "0px", "--hover-color": "#262730"},
            "nav-link-selected": {"background-color": "#FF4B4B"}, # Standard Streamlit Red
        }
    )
    
    st.divider()
    
    # 2. Contextual Options (Only shows when viewing a trip)
    if selected == "My Library" and st.session_state['active_trip_id']:
        st.caption("Trip Settings")
        
        # Edit Toggle
        edit_mode = st.toggle("Enable Editing", value=False)
        
        st.write("") # Spacer
        
        # Big Clear Delete Button
        if st.button("🗑️ Delete this Guide", type="primary", use_container_width=True):
            delete_itinerary(st.session_state['active_trip_id'])
            st.session_state['active_trip_id'] = None # Reset
            st.rerun()

# ==========================================
# PAGE 1: NEW SEARCH
# ==========================================
if selected == "New Search":
    st.title("🧠 Travel Intelligence AI")
    st.markdown("Your **Pre-Trip Strategic Briefing**. Cultural truths, logistics, and local norms.")

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            destination = st.selectbox("Where are you going?", options=sorted(POPULAR_CITIES))
        with col2:
            current_idx = datetime.now().month - 1
            month = st.selectbox("Travel Month", MONTHS, index=current_idx)

    if st.button("Generate Intelligence 🧠", type="primary"):
        st.subheader(f"Strategy for {destination} in {month}")
        response_container = st.empty()
        full_response = ""
        
        try:
            stream = generate_intel(destination, month)
            for chunk in stream:
                full_response += chunk
                response_container.markdown(full_response + "▌")
            response_container.markdown(full_response)
            
            # Temporary State for Saving
            st.session_state['temp_generated'] = full_response
            st.session_state['temp_dest'] = destination
            st.session_state['temp_month'] = month
            
        except Exception as e:
            st.error(f"Error: {e}")

    # Save Button
    if 'temp_generated' in st.session_state:
        st.divider()
        if st.button("💾 Save to Library"):
            save_itinerary(
                st.session_state['temp_dest'],
                st.session_state['temp_month'],
                st.session_state['temp_generated']
            )
            del st.session_state['temp_generated'] # Clear after save
            st.toast("Saved! Check 'My Library'")

# ==========================================
# PAGE 2: MY TRIPS LIBRARY
# ==========================================
elif selected == "My Library":
    
    # SCENARIO A: LIST VIEW (No specific trip selected)
    if st.session_state['active_trip_id'] is None:
        st.title("🗂️ My Saved Intel")
        
        history = get_history()
        
        if not history:
            st.info("You haven't saved any trips yet. Go to 'New Search' to create one.")
        else:
            # Display trips as a GRID of cards
            # We create rows of 2 columns
            for i in range(0, len(history), 2):
                cols = st.columns(2)
                # Process up to 2 items per row
                for j in range(2):
                    if i + j < len(history):
                        trip = history[i + j]
                        t_id, t_dest, t_date = trip
                        
                        with cols[j].container(border=True):
                            st.subheader(t_dest)
                            st.caption(f"Created: {t_date.strftime('%Y-%m-%d')}")
                            
                            if st.button(f"📂 Open Guide", key=f"open_{t_id}", use_container_width=True):
                                st.session_state['active_trip_id'] = t_id
                                st.rerun()

    # SCENARIO B: DETAIL VIEW (Viewing one trip)
    else:
        trip_id = st.session_state['active_trip_id']
        data = get_itinerary_details(trip_id)
        
        if data:
            dest_title, content = data
            
            # Header Row
            c1, c2 = st.columns([6, 1])
            with c1:
                st.title(f"✈️ {dest_title}")
            with c2:
                if st.button("❌ Close"):
                    st.session_state['active_trip_id'] = None
                    st.rerun()
            
            st.divider()
            
            # Check Sidebar toggle for Edit Mode
            if 'edit_mode' in locals() and edit_mode:
                with st.form("edit_form"):
                    new_text = st.text_area("Edit notes:", value=content, height=600)
                    if st.form_submit_button("💾 Save Updates", type="primary"):
                        update_itinerary(trip_id, new_text)
                        st.rerun()
            else:
                # READ MODE
                st.markdown(content)
                
        else:
            st.error("Trip not found.")
            st.session_state['active_trip_id'] = None
            st.rerun()