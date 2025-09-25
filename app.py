import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ==============================
# Google Drive 연결 설정 (Secrets 사용)
# ==============================
# 🔑 Streamlit Cloud > Secrets Manager에 저장한 키 사용
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],   # [gcp_service_account] 블록 전체를 읽음
    scopes=["https://www.googleapis.com/auth/drive.readonly"]
)

service = build("drive", "v3", credentials=creds)

FOLDER_ID = "10ZRhsEccCCy9qo-RB_z2VuMRUReLbIuL"  # Flashcards 이미지 폴더 ID

def get_files_from_folder(folder_id):
    """폴더 안의 모든 이미지 파일 가져오기 (페이지네이션 포함)"""
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
    st.markdown(
        """
        <style>
            body {background-color:black;}
            .title {text-align:center; font-size:36px; font-weight:bold; color:white; margin-top:15%;}
            .subtitle {text-align:center; font-size:16px; color:gray;}
            .stTextInput>div>div>input {font-size:20px; padding:10px; border-radius:25px;}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='title'>BCA Flashcards</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Type words (comma separated), then press Enter.</div>", unsafe_allow_html=True)

    words = st.text_input(
        "Flashcards",
        placeholder="e.g., bucket, apple, maze, rabbit",
        label_visibility="collapsed",
        key="word_input"
    )

    if words:
        all_files = get_files_from_folder(FOLDER_ID)
        st.write("DEBUG files:", all_files[:5])   # ✅ 디버그 출력
        file_map = {f["name"].rsplit(".", 1)[0].lower(): f["id"] for f in all_files}
        selected = []
        for w in [w.strip().lower() for w in words.split(",")]:
            if w in file_map:
                selected.append(f"https://drive.google.com/uc?id={file_map[w]}")

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
    st.markdown(
        """
        <style>
            .title {text-align:center; font-size:28px; font-weight:bold; color:white; margin-top:40px;}
            .subtitle {text-align:center; font-size:16px; color:gray; margin-bottom:20px;}
            .gallery {display:flex; flex-wrap:wrap; justify-content:center; gap:15px; max-width:70%; margin:auto;}
            .gallery img {width:120px; height:auto; border-radius:10px; box-shadow:0 0 10px rgba(255,255,255,0.2);}
            .btn-center {text-align:center; margin-top:30px;}
            .btn-present {background:#ff4b4b; color:white; font-size:18px; font-weight:bold; padding:12px 40px; border-radius:8px;}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='title'>BCA Flashcards</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Preview your flashcards below.</div>", unsafe_allow_html=True)

    if st.session_state.cards:
        st.markdown("<div class='gallery'>", unsafe_allow_html=True)
        for url in st.session_state.cards:
            st.image(url, width=120)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='btn-center'>", unsafe_allow_html=True)
        if st.button("Presentation ▶", key="present_btn"):
            st.session_state.mode = "present"
            st.session_state.current = 0
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ No cards loaded. Please go back and try again.")
        if st.button("Back to Home"):
            st.session_state.mode = "home"
            st.rerun()


# ==============================
# 3단계: Presentation 전체화면 모드
# ==============================
elif st.session_state.mode == "present":
    st.markdown(
        """
        <style>
            body { margin:0; padding:0; background:black; }
            .present-img {
                display:flex;
                justify-content:center;
                align-items:center;
                height:100vh;
            }
            .present-img img {
                max-height: 95vh;
                max-width: 95vw;
                border-radius: 15px;
                box-shadow: 0 0 40px rgba(255,255,255,0.3);
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.cards:
        url = st.session_state.cards[st.session_state.current]
        st.markdown("<div class='present-img'>", unsafe_allow_html=True)
        st.image(url, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # 키보드 네비게이션 안내 (streamlit_js_event_listener 없이 기본 구조)
        st.markdown(
            """
            <script>
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Enter' || event.key === ' ' || event.key === 'ArrowRight') {
                    window.parent.postMessage({isStreamlitMessage: true, type: 'nextCard'}, '*');
                } else if (event.key === 'ArrowLeft') {
                    window.parent.postMessage({isStreamlitMessage: true, type: 'prevCard'}, '*');
                } else if (event.key === 'Escape') {
                    window.parent.postMessage({isStreamlitMessage: true, type: 'exit'}, '*');
                }
            });
            </script>
            """,
            unsafe_allow_html=True
        )

        # 버튼 대신 이벤트 처리 (Session State 업데이트)
        if "nav_event" not in st.session_state:
            st.session_state.nav_event = None

        if st.session_state.nav_event == "nextCard":
            st.session_state.current = (st.session_state.current + 1) % len(st.session_state.cards)
            st.session_state.nav_event = None
            st.rerun()
        elif st.session_state.nav_event == "prevCard":
            st.session_state.current = (st.session_state.current - 1) % len(st.session_state.cards)
            st.session_state.nav_event = None
            st.rerun()
        elif st.session_state.nav_event == "exit":
            st.session_state.mode = "gallery"
            st.session_state.nav_event = None
            st.rerun()
    else:
        st.warning("⚠️ No cards to present. Returning to Gallery...")
        st.session_state.mode = "gallery"
        st.rerun()
