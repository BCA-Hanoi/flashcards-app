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
    st.subheader("Preview your flashcards below. Select the ones you want for presentation.")

    # -------------------------
    # 선택 상태 초기화
    # -------------------------
    if "selected_cards" not in st.session_state:
        st.session_state.selected_cards = st.session_state.cards.copy()

    # -------------------------
    # 썸네일 그리드 (반응형 8열)
    # -------------------------
    num_cols = 8
    cols = st.columns(num_cols)

    for i, url in enumerate(st.session_state.cards):
        with cols[i % num_cols]:
            checked = url in st.session_state.selected_cards
            new_val = st.checkbox(
                "", value=checked, key=f"chk_{i}"
            )
            st.image(url, use_container_width=True)
            # 체크 상태 반영
            if new_val and url not in st.session_state.selected_cards:
                st.session_state.selected_cards.append(url)
            elif not new_val and url in st.session_state.selected_cards:
                st.session_state.selected_cards.remove(url)

    # -------------------------
    # 버튼 UI (중앙 정렬)
    # -------------------------
    st.markdown(
        """
        <style>
        .button-bar {
            display: flex;
            justify-content: center;   /* 중앙 정렬 */
            gap: 15px;                 /* 버튼 간격 */
            margin-top: 20px;
        }
        .button-bar button {
            background-color: #444;
            color: white;
            font-size: 16px;
            padding: 8px 20px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }
        .button-bar button:hover {
            background-color: #666;
        }
        </style>

        <div class="button-bar">
            <form action="" method="get">
                <button name="action" value="select_all">✅ Select All</button>
                <button name="action" value="clear_all">❌ Clear All</button>
                <button name="action" value="present">▶ Presentation</button>
                <button name="action" value="home">🏠 Back to Home</button>
            </form>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------
    # 버튼 동작 처리
    # -------------------------
    action = st.query_params.get("action", None)

    if action == "select_all":
        st.session_state.selected_cards = st.session_state.cards.copy()
        st.query_params.clear()
        st.rerun()

    elif action == "clear_all":
        st.session_state.selected_cards = []
        st.query_params.clear()
        st.rerun()

    elif action == "present":
        if st.session_state.selected_cards:
            st.session_state.cards = st.session_state.selected_cards.copy()
        st.session_state.mode = "present"
        st.session_state.current = 0
        st.query_params.clear()
        st.rerun()

    elif action == "home":
        st.session_state.mode = "home"
        st.query_params.clear()
        st.rerun()


# ==============================
# 3단계: Presentation 전체화면 모드
# ==============================
elif st.session_state.mode == "present":
    st.markdown(
        """
        <style>
            .block-container {padding:0; margin:0; max-width:100%;}
            header, footer, .stToolbar {visibility:hidden; height:0;}
            body {background:black; margin:0; padding:0;}
            .present-img {
                display:flex;
                justify-content:center;
                align-items:center;
                height:90vh;   /* 이미지 영역 */
            }
            .present-img img {
                max-height:90vh;
                max-width:90vw;
                border-radius:15px;
                box-shadow:0 0 40px rgba(255,255,255,0.3);
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    if st.session_state.cards:
        url = st.session_state.cards[st.session_state.current]
        st.markdown(f"<div class='present-img'><img src='{url}'></div>", unsafe_allow_html=True)

        # 버튼은 present 모드에서만 표시
        col1, col2, col3 = st.columns([1,1,1])
        with col1:
            if st.button("◀ Prev", use_container_width=True):
                st.session_state.current = (st.session_state.current - 1) % len(st.session_state.cards)
                st.rerun()

        with col2:
            if st.button("Exit", use_container_width=True):
                st.session_state.mode = "gallery"
                st.rerun()

        with col3:
            if st.button("Next ▶", use_container_width=True):
                st.session_state.current = (st.session_state.current + 1) % len(st.session_state.cards)
                st.rerun()
