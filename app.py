import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
from streamlit_js_eval import streamlit_js_eval

# ==============================
# Google Drive 연결 설정 (Secrets 사용)
# ==============================
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/drive.readonly"]
)

service = build("drive", "v3", credentials=creds)

FOLDER_ID = "10ZRhsEccCCy9qo-RB_z2VuMRUReLbIuL"  # Flashcards 이미지 폴더 ID


def get_files_from_folder(folder_id):
    """폴더 안의 모든 이미지 파일 가져오기"""
    query = f"'{folder_id}' in parents and mimeType contains 'image/'"
    files = []
    page_token = None
    while True:
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name)",
            pageSize=200,
            pageToken=page_token
        ).execute()
        files.extend(results.get("files", []))
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    return files


# ==============================
# Streamlit UI 설정
# ==============================
st.set_page_config(page_title="BCA Flashcards", layout="wide")

if "mode" not in st.session_state:
    st.session_state.mode = "home"
if "cards" not in st.session_state:
    st.session_state.cards = []
if "current" not in st.session_state:
    st.session_state.current = 0


# ==============================
# 1단계: 단어 입력 화면
# ==============================
if st.session_state.mode == "home":
    st.title("BCA Flashcards")
    st.subheader("Type words (comma separated), then press Enter.")

    words = st.text_input(
        "Flashcards",
        placeholder="e.g., bucket, apple, maze, rabbit",
        label_visibility="collapsed",
        key="word_input"
    )

    if words:
        all_files = get_files_from_folder(FOLDER_ID)

        # 확장자 제거 + 소문자 변환
        file_map = {
            f["name"].rsplit(".", 1)[0].strip().lower(): f["id"]
            for f in all_files
        }

        selected = []
        for w in [w.strip().lower() for w in words.split(",")]:
            if w in file_map:
                # ✅ 썸네일 API 사용 (sz=w1000 : 최대 1000px)
                selected.append(
                    f"https://drive.google.com/thumbnail?id={file_map[w]}&sz=w1000"
                )

        if selected:
            st.session_state.cards = selected
            st.session_state.mode = "gallery"
            st.rerun()
        else:
            st.warning("⚠️ No matching flashcards found. Try again.")


# ==============================
# 2단계: 갤러리 미리보기 화면
# ==============================
elif st.session_state.mode == "gallery":
    st.title("BCA Flashcards")
    st.subheader("Preview your flashcards below.")

    if st.session_state.cards:
        cols = st.columns(10)
        for i, url in enumerate(st.session_state.cards):
            with cols[i % 10]:
                st.image(url, use_container_width=True)

        if st.button("Presentation ▶"):
            st.session_state.mode = "present"
            st.session_state.current = 0
            st.rerun()
    else:
        st.warning("⚠️ No cards loaded. Please go back and try again.")
        if st.button("Back to Home"):
            st.session_state.mode = "home"
            st.rerun()


# ==============================
# 3단계: Presentation 전체화면 모드 (키보드 네비게이션: Enter/Space/→, ←, ESC)
# ==============================
elif st.session_state.mode == "present":
    st.markdown(
        """
        <style>
            html, body, .block-container {
                height: 100%;
                margin: 0 !important;
                padding: 0 !important;
                background: black;
                overflow: hidden;
            }
            header, footer, .stToolbar {visibility: hidden; height: 0;}
            .present-container {
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                height: 100vh;
                width: 100vw;
            }
            .present-img {
                flex: 1;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .present-img img {
                max-height: 85vh;   /* 이미지가 화면 세로에 맞게 */
                max-width: 90vw;    /* 가로는 비율 유지 */
                object-fit: contain;
                border-radius: 15px;
                box-shadow: 0 0 30px rgba(255,255,255,0.3);
            }
            .present-controls {
                text-align: center;
                margin: 10px;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.cards:
        url = st.session_state.cards[st.session_state.current]

        # 전체 컨테이너
        st.markdown("<div class='present-container'>", unsafe_allow_html=True)

        # 이미지
        st.markdown(f"<div class='present-img'><img src='{url}'></div>", unsafe_allow_html=True)

        # 버튼
        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            if st.button("◀ Prev"):
                st.session_state.current = (st.session_state.current - 1) % len(st.session_state.cards)
                st.rerun()
        with col2:
            if st.button("Exit"):
                st.session_state.mode = "gallery"
                st.rerun()
        with col3:
            if st.button("Next ▶"):
                st.session_state.current = (st.session_state.current + 1) % len(st.session_state.cards)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
