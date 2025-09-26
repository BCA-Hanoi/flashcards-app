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

    # 초기화
    if "selected_cards" not in st.session_state:
        st.session_state.selected_cards = []

    # 보기 옵션 (기본 8열)
    if "gallery_cols" not in st.session_state:
        st.session_state.gallery_cols = 8

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📒 8 per row"):
            st.session_state.gallery_cols = 8
            st.rerun()
    with col2:
        if st.button("📗 3 per row"):
            st.session_state.gallery_cols = 3
            st.rerun()

    # 카드 출력
if st.session_state.cards:
    cols = st.columns(st.session_state.gallery_cols)
    for i, url in enumerate(st.session_state.cards):
        with cols[i % st.session_state.gallery_cols]:
            # ✅ 디버깅용: 현재 URL을 보여줌
            st.caption(url)

            # 체크박스
            checked = url in st.session_state.selected_cards
            if st.checkbox(f"Card {i+1}", value=checked, key=f"chk_{i}"):
                if url not in st.session_state.selected_cards:
                    st.session_state.selected_cards.append(url)
            else:
                if url in st.session_state.selected_cards:
                    st.session_state.selected_cards.remove(url)

            # ✅ 이미지 출력
            st.image(url, use_container_width=True)


        # 버튼 (중앙 정렬)
        button_cols = st.columns([1,1,1,1])
        with button_cols[0]:
            if st.button("✅ Select All"):
                st.session_state.selected_cards = st.session_state.cards.copy()
                st.rerun()
        with button_cols[1]:
            if st.button("❌ Clear All"):
                st.session_state.selected_cards = []
                st.rerun()
        with button_cols[2]:
            if st.button("▶ Presentation"):
                if st.session_state.selected_cards:
                    st.session_state.cards = st.session_state.selected_cards.copy()
                st.session_state.mode = "present"
                st.session_state.current = 0
                st.rerun()
        with button_cols[3]:
            if st.button("🏠 Back to Home"):
                st.session_state.mode = "home"
                st.rerun()
    else:
        st.warning("⚠️ No cards loaded. Please go back and try again.")


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
