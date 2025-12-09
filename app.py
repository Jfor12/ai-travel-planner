import streamlit as st

# Load environment variables from .env (if present) before importing app modules
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; environment may be provided by host
    pass

# Delegate to modularized UI
try:
    from ui import run_app
except Exception as e:
    st.error(f"❌ Failed to load application modules: {e}")
    raise


if __name__ == "__main__":
    run_app()