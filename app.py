import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json

# ==============================
# Google Drive credentials
# ==============================
FOLDER_ID = "10ZRhsEccCCy9qo-RB_z2VuMRUReLbIuL"  # Flashcards folder ID
SERVICE_ACCOUNT_FILE = "service_key.json"       # local fallback

def build_drive_service():
    """Build a Drive v3 client from either secrets or local file."""
    creds = None
    try:
        # Prefer Streamlit Cloud secret (no file needed)
        if "gcp_service_account" in st.secrets:
            info = st.secrets["gcp_service_account"]
            creds = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )
        else:
            # Local development fallback
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE,
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )
    except Exception as e:
        st.error("Failed to load Google credentials. "
                 "Use `st.secrets['gcp_service_account']` on Cloud or a local service_key.json.")
        st.stop()

    return build("drive", "v3", credentials=creds)

service = build_drive_service()

def get_files_from_folder(folder_id: str):
    """Return all image files (id, name) inside a Drive folder (handles pagination)."""
    query = f"'{folder_id}' in parents and mimeType contains 'image/'"
    files, page_token = [], None
    while True:
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name)",
            pageSize=200,
            pageToken=page_token,
        ).execute()
        files.extend(results.get("files", []))
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return files


# ==============================
# Streamlit app state & layout
# ==============================
st.set_page_config(page_title="BCA Flashcards", layout="wide")

if "mode" not in st.session_state:
    st.session_state.mode = "home"
if "cards" not in st.session_state:
    st.session_state.cards = []
if "current" not in st.session_state:
    st.session_state.current = 0

# Global styles
st.markdown(
    """
    <style>
      body { background: #0e0f12; }
      .title { text-align:center; font-size:36px; font-weight:800; color:#fff; margin-top:8vh; }
      .subtitle { text-align:center; font-size:16px; color:#9aa0a6; }
      .center { display:flex; justify-content:center; align-items:center; }
      .input-wrap { max-width: 780px; margin: 24px auto; }
      .stTextInput > div > div > input {
        font-size:20px; padding:12px 18px; border-radius:25px; height:52px;
      }
      .gallery { display:flex; flex-wrap:wrap; justify-content:center; gap:15px; max-width:70%; margin: 24px auto; }
      .gallery img { width:120px; height:auto; border-radius:10px; box-shadow:0 0 10px rgba(255,255,255,0.15); }
      .btn-primary {
        background:#ff4b4b; color:white; font-size:18px; font-weight:700;
        padding:14px 40px; border-radius:10px; border:none;
      }
      .present-img {
        display:flex; justify-content:center; align-items:center;
        min-height: calc(100vh - 180px);
      }
      .present-img img {
        max-height: 90vh; max-width: 90vw;
        border-radius: 16px; box-shadow: 0 0 40px rgba(255,255,255,0.25);
      }
      .nav-wrap { max-width: 760px; margin: 16px auto 48px; }
      .nav-btn {
        width: 100%; height: 56px; font-size: 18px; font-weight: 700;
        border-radius: 12px;
      }
      .prev { background:#2b2f36; color:#e6e9ee; }
      .exit { background:#3a3f46; color:#e6e9ee; }
      .next { background:#ff4b4b; color:#fff; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================
# Home: enter comma-separated words
# ==============================
if st.session_state.mode == "home":
    st.markdown("<div class='title'>BCA Flashcards</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>Type words (comma separated), then press Enter.</div>",
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown("<div class='input-wrap'>", unsafe_allow_html=True)
        words = st.text_input(
            "Flashcards",
            placeholder="e.g., bucket, apple, maze, rabbit",
            label_visibility="collapsed",
            key="word_input",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # When the user types, try loading immediately (same behavior as before)
    if words:
        all_files = get_files_from_folder(FOLDER_ID)
        file_map = {f["name"].rsplit(".", 1)[0].lower(): f["id"] for f in all_files}

        selected_urls = []
        for w in [w.strip().lower() for w in words.split(",") if w.strip()]:
            if w in file_map:
                selected_urls.append(f"https://drive.google.com/uc?id={file_map[w]}")

        if selected_urls:
            st.session_state.cards = selected_urls
            st.session_state.mode = "gallery"
            st.rerun()
        else:
            st.warning("No matching flashcards found. Try again.")


# ==============================
# Gallery: preview thumbnails
# ==============================
elif st.session_state.mode == "gallery":
    st.markdown("<div class='title'>BCA Flashcards</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Preview your flashcards below.</div>", unsafe_allow_html=True)

    # keep the input visible in gallery (per your UX)
    with st.container():
        st.markdown("<div class='input-wrap'>", unsafe_allow_html=True)
        words_again = st.text_input(
            "Edit words",
            value=st.session_state.get("word_input", ""),
            placeholder="e.g., bucket, apple, maze, rabbit",
            label_visibility="collapsed",
            key="word_input_gallery",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if words_again != st.session_state.get("word_input", ""):
            # if edited, recompute selection
            all_files = get_files_from_folder(FOLDER_ID)
            file_map = {f["name"].rsplit(".", 1)[0].lower(): f["id"] for f in all_files}
            selected_urls = []
            for w in [w.strip().lower() for w in words_again.split(",") if w.strip()]:
                if w in file_map:
                    selected_urls.append(f"https://drive.google.com/uc?id={file_map[w]}")
            st.session_state.cards = selected_urls

    if st.session_state.cards:
        st.markdown("<div class='gallery'>", unsafe_allow_html=True)
        for url in st.session_state.cards:
            st.image(url, width=120)
        st.markdown("</div>", unsafe_allow_html=True)

        # Presentation button (centered)
        col = st.container()
        with col:
            _, c2, _ = st.columns([1, 2, 1])
            with c2:
                if st.button("Presentation ▶", use_container_width=True, type="primary"):
                    st.session_state.mode = "present"
                    st.session_state.current = 0
                    st.rerun()
    else:
        st.info("No cards loaded yet. Type words above.")


# ==============================
# Presentation: full-screen style with big buttons
# ==============================
elif st.session_state.mode == "present":
    if not st.session_state.cards:
        st.warning("No cards to present. Returning to Gallery…")
        st.session_state.mode = "gallery"
        st.rerun()

    # Image area
    url = st.session_state.cards[st.session_state.current]
    st.markdown("<div class='present-img'>", unsafe_allow_html=True)
    st.image(url, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Navigation buttons (Prev / Exit / Next)
    st.markdown("<div class='nav-wrap'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1], gap="large")
    with c1:
        if st.button("⟵ Prev", key="prev_btn", use_container_width=True):
            st.session_state.current = (st.session_state.current - 1) % len(st.session_state.cards)
            st.rerun()
    with c2:
        if st.button("Exit", key="exit_btn", use_container_width=True):
            st.session_state.mode = "gallery"
            st.rerun()
    with c3:
        if st.button("Next ⟶", key="next_btn", use_container_width=True):
            st.session_state.current = (st.session_state.current + 1) % len(st.session_state.cards)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

