import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account

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
    # 풀스크린 스타일
    st.markdown(
        """
        <style>
            .block-container { padding:0; margin:0; max-width:100%; }
            header, footer, .stToolbar { visibility:hidden; height:0px; }
            body { background:black; margin:0; padding:0; }
            .present-img {
                display:flex; justify-content:center; align-items:center;
                height:100vh; width:100vw;
            }
            .present-img img {
                max-height:95vh; max-width:95vw; border-radius:15px;
                box-shadow:0 0 40px rgba(255,255,255,0.3);
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 현재 이미지 표시
    if st.session_state.cards:
        url = st.session_state.cards[st.session_state.current]
        st.markdown(f"<div class='present-img'><img src='{url}'></div>", unsafe_allow_html=True)

    # 🔑 키 이벤트: streamlit-js-eval 사용
    from streamlit_js_eval import streamlit_js_eval

    # 이벤트에서 필요한 값 2개를 받아온다: key, timestamp
    res = streamlit_js_eval(
        js_expressions=["event.key", "event.timeStamp"],
        events="keydown",
        key="present_key_events"
    )
st.write("DEBUG key:", res)

    # 디바운싱: 같은 키 이벤트가 중복 반영되지 않도록 timeStamp로 막기
    if isinstance(res, list) and len(res) == 2:
        key_pressed, ts = res[0], res[1]
        last_ts = st.session_state.get("last_key_ts")
        if ts != last_ts:
            st.session_state["last_key_ts"] = ts

            if key_pressed in ["Enter", " ", "ArrowRight"]:
                st.session_state.current = (st.session_state.current + 1) % len(st.session_state.cards)
                st.rerun()
            elif key_pressed == "ArrowLeft":
                st.session_state.current = (st.session_state.current - 1) % len(st.session_state.cards)
                st.rerun()
            elif key_pressed == "Escape":
                st.session_state.mode = "gallery"
                st.rerun()
