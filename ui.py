import streamlit as st
import os
import re
from datetime import datetime

# Use standard Streamlit radio as a lightweight sidebar menu (avoids custom component issues)

try:
    import ai
    import db
    import maps
except Exception as e:
    st.error(f"❌ Failed to import modules: {e}")
    st.stop()


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


def run_app():
    st.set_page_config(page_title="Travel Strategy AI", page_icon="🧠", layout="wide")

    if 'active_trip_id' not in st.session_state:
        st.session_state['active_trip_id'] = None
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    with st.sidebar:
        selected = st.selectbox(
            label="Navigation",
            options=["New Search", "My Library"],
            index=0,
            key="ui_sidebar_select_v1",
            label_visibility="collapsed",
        )
        st.divider()
        st.divider()

        if selected == "My Library" and st.session_state['active_trip_id']:
            st.caption("Trip Settings")
            edit_mode = st.toggle("Enable Editing", value=False)
            st.write("")
            if st.button("🗑️ Delete this Guide", type="primary"):
                db.delete_itinerary(st.session_state['active_trip_id'])
                st.session_state['active_trip_id'] = None
                st.rerun()

        # Author signature / contact (adjust links as needed)
        st.markdown(
            "---\n"
            "**Built by:** Jacopo Fornesi   "
            "[LinkedIn](https://www.linkedin.com/in/jacopo-fornesi) • "
            "[GitHub](https://github.com/Jfor12) • "
            "[Email](mailto:jacopofornesi@hotmail.com)",
            unsafe_allow_html=True,
        )

    # --- PAGE 1: NEW SEARCH ---
    if selected == "New Search":
        st.session_state["chat_history"] = []
        st.title("🧠 Travel Intelligence AI")
        st.markdown("Your **Pre-Trip Strategic Briefing**.")

        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                destination = st.selectbox("Where are you going?", options=sorted(POPULAR_CITIES), key="ui_dest_select_v1")
            with col2:
                current_idx = datetime.now().month - 1
                month = st.selectbox("Travel Month", MONTHS, index=current_idx, key="ui_month_select_v1")

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
                stream = ai.generate_intel(destination, month)
                for chunk in stream:
                    full_response += chunk
                    clean_chunk = full_response.split("(---PAGE BREAK---)")[0]
                    response_container.markdown(clean_chunk + "▌")

                final_display_text = full_response.split("(---PAGE BREAK---)")[0]
                display_no_coords = re.sub(r"(?mi)^\s*#{1,3}\s*COORDINATES.*$(?:\n(?:.*\|.*\|.*$))*", "", final_display_text)
                display_no_coords = re.sub(r"(?m)([^\n|]+?)\s*\|\s*-?\d+\.?\d*\s*\|\s*-?\d+\.?\d*", lambda m: m.group(1).strip(), display_no_coords)
                display_no_coords = re.sub(r"\n{3,}", "\n\n", display_no_coords).strip()
                response_container.markdown(display_no_coords)

                st.session_state['temp_generated_full'] = full_response
                st.session_state['temp_dest'] = destination
                st.session_state['temp_month'] = month
            except Exception as e:
                st.error(f"Error: {e}")

        if 'temp_generated_full' in st.session_state:
            map_df = maps.extract_map_data(st.session_state['temp_generated_full'])
            st.divider()
            st.subheader("📍 Key Locations")
            if not map_df.empty:
                raw_text = st.session_state.get('temp_generated_full', '')
                seen = set()
                loc_names = []
                for n in map_df['name']:
                    if n not in seen:
                        seen.add(n)
                        loc_names.append(n)
                coords_by_name = {r['name']: (r['lat'], r['lon']) for _, r in map_df.iterrows()}
                for name in loc_names:
                    coords = coords_by_name.get(name)
                    url = maps.place_reference_url(name, st.session_state.get('temp_dest'), coords=coords)
                    st.markdown(f"- [{name}]({url})")
                maps.display_labeled_map(map_df)
            else:
                st.warning("No coordinates found for map.")
                with st.expander("Debug: Check Raw Output"):
                    st.text(st.session_state['temp_generated_full'])

            st.divider()
            if st.button("💾 Save to Library"):
                db.save_itinerary(
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
            history = db.get_history()
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
            data = db.get_itinerary_details(trip_id)
            if data:
                dest_title, full_content = data
                display_content = full_content.split("(---PAGE BREAK---)")[0]
                display_content = re.sub(r"(?mi)^\s*#{1,3}\s*COORDINATES.*$(?:\n(?:.*\|.*\|.*$))*", "", display_content)
                display_content = re.sub(r"(?m)([^\n|]+?)\s*\|\s*-?\d+\.?\d*\s*\|\s*-?\d+\.?\d*", lambda m: m.group(1).strip(), display_content)
                display_content = re.sub(r"\n{3,}", "\n\n", display_content).strip()

                c1, c2, c3 = st.columns([6, 1, 1])
                with c1:
                    st.title(f"✈️ {dest_title}")
                with c2:
                    pdf_data = maps.create_pdf(dest_title, full_content)
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
                            db.update_itinerary(trip_id, new_text)
                            st.rerun()
                else:
                    st.markdown(display_content)

                    map_df = maps.extract_map_data(full_content)
                    st.divider()
                    st.subheader("📍 Key Locations")
                    if not map_df.empty:
                        seen = set()
                        loc_names = []
                        for n in map_df['name']:
                            if n not in seen:
                                seen.add(n)
                                loc_names.append(n)
                        with st.container():
                            coords_by_name = {r['name']: (r['lat'], r['lon']) for _, r in map_df.iterrows()}
                            for name in loc_names:
                                coords = coords_by_name.get(name)
                                url = maps.place_reference_url(name, dest_title, coords=coords)
                                st.markdown(f"- [{name}]({url})")
                        maps.display_labeled_map(map_df)
                    else:
                        st.info("No map data available for this trip.")

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
                            response = ai.run_chat_response(display_content, prompt)
                            st.markdown(response)

                        st.session_state["chat_history"].append({"role": "assistant", "content": response})
                        db.save_chat_message(trip_id, "user", prompt)
                        db.save_chat_message(trip_id, "assistant", response)
            else:
                st.error("Trip not found.")
                st.session_state['active_trip_id'] = None
                st.rerun()
