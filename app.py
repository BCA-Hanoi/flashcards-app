import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
import random
import re
import time

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


def clean_filename(filename):
    """파일명에서 확장자와 (1), (2) 같은 중복 번호 제거"""
    # 확장자 제거
    name = filename.rsplit(".", 1)[0]
    # (숫자) 패턴 제거 - 예: "apple (1)" -> "apple"
    name = re.sub(r'\s*\(\d+\)$', '', name)
    return name.strip().lower()


# ==============================
# Streamlit UI 설정
# ==============================
st.set_page_config(page_title="BCA Flashcards", layout="wide")

# Session State 초기화
if "mode" not in st.session_state:
    st.session_state.mode = "home"
if "cards" not in st.session_state:
    st.session_state.cards = []
if "current" not in st.session_state:
    st.session_state.current = 0
if "game_cards" not in st.session_state:
    st.session_state.game_cards = []
if "zoom_level" not in st.session_state:
    st.session_state.zoom_level = 1
if "game_score" not in st.session_state:
    st.session_state.game_score = 0
if "missing_card_idx" not in st.session_state:
    st.session_state.missing_card_idx = None
if "speed_quiz_index" not in st.session_state:
    st.session_state.speed_quiz_index = 0


# ==============================
# 1단계: 단어 입력 화면
# ==============================
if st.session_state.mode == "home":
    st.title("🎴 BCA Flashcards")
    st.subheader("Type words (comma separated), then press Enter.")

    words = st.text_input(
        "Flashcards",
        placeholder="e.g., bucket, apple, maze, rabbit",
        label_visibility="collapsed",
        key="word_input"
    )

    # ✅ Check Existing Words 버튼
    if st.button("🔍 Check Existing Words"):
        if words:
            all_files = get_files_from_folder(FOLDER_ID)
            
            # 파일명 매핑 (중복 허용)
            file_map = {}
            for f in all_files:
                clean_name = clean_filename(f["name"])
                if clean_name not in file_map:
                    file_map[clean_name] = []
                file_map[clean_name].append({
                    "id": f["id"],
                    "original_name": f["name"]
                })
            
            input_words = [w.strip().lower() for w in words.split(",")]
            found_words = {}
            not_found = []
            
            for word in input_words:
                if word in file_map:
                    found_words[word] = file_map[word]
                else:
                    not_found.append(word)
            
            # 결과 표시
            st.markdown("---")
            if found_words:
                st.success(f"✅ **Found ({len(found_words)} words):**")
                for word, files in found_words.items():
                    st.write(f"**{word}** ({len(files)}장)")
                    cols = st.columns(min(len(files), 5))
                    for i, file_info in enumerate(files[:5]):
                        with cols[i]:
                            url = f"https://drive.google.com/thumbnail?id={file_info['id']}&sz=w200"
                            st.image(url, caption=file_info['original_name'], use_container_width=True)
            
            if not_found:
                st.error(f"❌ **Not Found ({len(not_found)} words):**")
                st.write(", ".join(not_found))
        else:
            st.warning("⚠️ Please enter some words first.")

    if words:
        all_files = get_files_from_folder(FOLDER_ID)

        # 파일명 매핑 (중복 허용)
        file_map = {}
        for f in all_files:
            clean_name = clean_filename(f["name"])
            if clean_name not in file_map:
                file_map[clean_name] = []
            file_map[clean_name].append(f["id"])

        selected = []
        for w in [w.strip().lower() for w in words.split(",")]:
            if w in file_map:
                # 같은 단어의 모든 이미지 추가
                for file_id in file_map[w]:
                    selected.append(f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000")

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
    st.title("🎴 BCA Flashcards")
    st.subheader("Preview your flashcards below. Select the ones you want.")

    # -------------------------
    # Add More 입력창 토글
    # -------------------------
    if "show_input" not in st.session_state:
        st.session_state.show_input = False
    if "selected_cards" not in st.session_state:
        st.session_state.selected_cards = st.session_state.cards.copy()

    if st.button("➕ Add More"):
        st.session_state.show_input = not st.session_state.show_input
        st.rerun()

    if st.session_state.show_input:
        new_words = st.text_input(
            "Add Flashcards",
            placeholder="e.g., rabbit, lion, sun",
            label_visibility="collapsed",
            key="word_input_gallery"
        )
        if st.button("Add Now"):
            if new_words:
                all_files = get_files_from_folder(FOLDER_ID)
                file_map = {}
                for f in all_files:
                    clean_name = clean_filename(f["name"])
                    if clean_name not in file_map:
                        file_map[clean_name] = []
                    file_map[clean_name].append(f["id"])
                
                to_add = []
                for w in [w.strip().lower() for w in new_words.split(",")]:
                    if w in file_map:
                        for file_id in file_map[w]:
                            to_add.append(f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000")

                if to_add:
                    st.session_state.cards = list(dict.fromkeys(st.session_state.cards + to_add))
                st.session_state.show_input = False
                st.rerun()

    # -------------------------
    # 갤러리
    # -------------------------
    if st.session_state.cards:
        new_selection = []
        num_cols = 8
        cols = st.columns(num_cols)

        for i, url in enumerate(st.session_state.cards):
            with cols[i % num_cols]:
                st.image(url, use_container_width=True)
                default_checked = st.session_state.get(f"chk_{i}", url in st.session_state.selected_cards)
                checked = st.checkbox(f"Card {i+1}", key=f"chk_{i}", value=default_checked)
                if checked:
                    new_selection.append(url)

        st.session_state.selected_cards = new_selection

        # -------------------------
        # 버튼들
        # -------------------------
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
        
        with col1:
            if st.button("▶ Presentation"):
                st.session_state.mode = "present"
                st.session_state.current = 0
                st.rerun()
        
        with col2:
            if st.button("🎲 Random 2"):
                if len(st.session_state.selected_cards) >= 2:
                    st.session_state.game_cards = random.sample(st.session_state.selected_cards, 2)
                    st.session_state.mode = "random_show"
                    st.rerun()
        
        with col3:
            if st.button("🎲 Random 4"):
                if len(st.session_state.selected_cards) >= 4:
                    st.session_state.game_cards = random.sample(st.session_state.selected_cards, 4)
                    st.session_state.mode = "random_show"
                    st.rerun()
        
        with col4:
            if st.button("🎲 Random 6"):
                if len(st.session_state.selected_cards) >= 6:
                    st.session_state.game_cards = random.sample(st.session_state.selected_cards, 6)
                    st.session_state.mode = "random_show"
                    st.rerun()
        
        with col5:
            if st.button("🔍 Hide & Seek"):
                if st.session_state.selected_cards:
                    st.session_state.mode = "hide_seek"
                    st.session_state.current = 0
                    st.session_state.zoom_level = 1
                    st.rerun()
        
        with col6:
            if st.button("🤔 What's Missing"):
                if len(st.session_state.selected_cards) >= 5:
                    st.session_state.mode = "whats_missing"
                    st.session_state.game_cards = random.sample(st.session_state.selected_cards, min(6, len(st.session_state.selected_cards)))
                    st.session_state.missing_card_idx = None
                    st.rerun()
        
        with col7:
            if st.button("⚡ Speed Quiz"):
                if st.session_state.selected_cards:
                    st.session_state.mode = "speed_quiz"
                    st.session_state.game_cards = random.sample(st.session_state.selected_cards, min(10, len(st.session_state.selected_cards)))
                    st.session_state.speed_quiz_index = 0
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🏠 Home"):
            st.session_state.mode = "home"
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
                height:90vh;
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


# ==============================
# Random Show Mode (2/4/6개 랜덤)
# ==============================
elif st.session_state.mode == "random_show":
    st.title("🎲 Random Cards")
    
    if st.session_state.game_cards:
        cols = st.columns(len(st.session_state.game_cards))
        for i, url in enumerate(st.session_state.game_cards):
            with cols[i]:
                st.image(url, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Shuffle Again"):
            num = len(st.session_state.game_cards)
            if len(st.session_state.selected_cards) >= num:
                st.session_state.game_cards = random.sample(st.session_state.selected_cards, num)
                st.rerun()
    with col2:
        if st.button("⬅ Back to Gallery"):
            st.session_state.mode = "gallery"
            st.rerun()


# ==============================
# Hide & Seek Game (숨은 그림 찾기)
# ==============================
elif st.session_state.mode == "hide_seek":
    st.title("🔍 Hide & Seek - Guess the Card!")
    
    if st.session_state.selected_cards:
        current_card = st.session_state.selected_cards[st.session_state.current]
        
        # 줌 레벨에 따른 크기 조절 (1=매우 확대, 4=전체)
        zoom_sizes = {
            1: "?sz=w1000",  # 원본 크기로 표시하되 CSS로 확대
            2: "?sz=w1000",
            3: "?sz=w1000",
            4: "?sz=w1000"
        }
        
        # CSS로 이미지 크롭/확대 효과
        zoom_styles = {
            1: "transform: scale(4); object-fit: cover; height: 400px; width: 400px; object-position: 30% 30%;",
            2: "transform: scale(2.5); object-fit: cover; height: 500px; width: 500px; object-position: 40% 40%;",
            3: "transform: scale(1.5); object-fit: cover; height: 600px; width: 600px;",
            4: "object-fit: contain; max-height: 700px; max-width: 100%;"
        }
        
        st.markdown(f"""
            <div style="display: flex; justify-content: center; align-items: center; overflow: hidden; height: 500px; background: #f0f0f0; border-radius: 10px;">
                <img src="{current_card}{zoom_sizes[st.session_state.zoom_level]}" 
                     style="{zoom_styles[st.session_state.zoom_level]} border-radius: 10px;">
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💡 Hint (Show More)", use_container_width=True):
                if st.session_state.zoom_level < 4:
                    st.session_state.zoom_level += 1
                    st.rerun()
        
        with col2:
            if st.button("➡ Next Card", use_container_width=True):
                st.session_state.current = (st.session_state.current + 1) % len(st.session_state.selected_cards)
                st.session_state.zoom_level = 1
                st.rerun()
        
        with col3:
            if st.button("🔄 Reset Zoom", use_container_width=True):
                st.session_state.zoom_level = 1
                st.rerun()
        
        with col4:
            if st.button("⬅ Back", use_container_width=True):
                st.session_state.mode = "gallery"
                st.rerun()


# ==============================
# What's Missing Game
# ==============================
elif st.session_state.mode == "whats_missing":
    st.title("🤔 What's Missing?")
    
    if st.session_state.missing_card_idx is None:
        st.subheader("Remember these cards!")
        cols = st.columns(len(st.session_state.game_cards))
        for i, url in enumerate(st.session_state.game_cards):
            with cols[i]:
                st.image(url, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Ready! Hide One Card", use_container_width=True):
            st.session_state.missing_card_idx = random.randint(0, len(st.session_state.game_cards) - 1)
            st.rerun()
    
    else:
        st.subheader("Which card is missing?")
        remaining_cards = [card for i, card in enumerate(st.session_state.game_cards) if i != st.session_state.missing_card_idx]
        
        cols = st.columns(len(remaining_cards))
        for i, url in enumerate(remaining_cards):
            with cols[i]:
                st.image(url, use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👀 Show Answer", use_container_width=True):
                st.image(st.session_state.game_cards[st.session_state.missing_card_idx], width=300)
        
        with col2:
            if st.button("🔄 Play Again", use_container_width=True):
                st.session_state.game_cards = random.sample(st.session_state.selected_cards, min(6, len(st.session_state.selected_cards)))
                st.session_state.missing_card_idx = None
                st.rerun()
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⬅ Back to Gallery"):
        st.session_state.mode = "gallery"
        st.rerun()


# ==============================
# Speed Quiz Game
# ==============================
elif st.session_state.mode == "speed_quiz":
    st.title("⚡ Speed Quiz!")
    
    if st.session_state.speed_quiz_index < len(st.session_state.game_cards):
        current_card = st.session_state.game_cards[st.session_state.speed_quiz_index]
        
        # 진행 상황 표시
        st.progress((st.session_state.speed_quiz_index + 1) / len(st.session_state.game_cards))
        st.subheader(f"Card {st.session_state.speed_quiz_index + 1} / {len(st.session_state.game_cards)}")
        
        # 카드 표시
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(current_card, use_container_width=True)
        
        # 자동 넘김 (3초)
        time.sleep(0.1)  # 약간의 딜레이
        
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("➡ Next (or wait 3 sec)", use_container_width=True, key="next_card"):
                st.session_state.speed_quiz_index += 1
                st.rerun()
        
        with col2:
            if st.button("⏸ Pause", use_container_width=True):
                st.session_state.mode = "gallery"
                st.rerun()
        
        # 자동 타이머 (JavaScript)
        st.markdown("""
            <script>
                setTimeout(function() {
                    window.location.reload();
                }, 3000);
            </script>
        """, unsafe_allow_html=True)
    
    else:
        st.success("🎉 Quiz Complete!")
        st.balloons()
        
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Play Again", use_container_width=True):
                st.session_state.game_cards = random.sample(st.session_state.selected_cards, min(10, len(st.session_state.selected_cards)))
                st.session_state.speed_quiz_index = 0
                st.rerun()
        
        with col2:
            if st.button("⬅ Back to Gallery", use_container_width=True):
                st.session_state.mode = "gallery"
                st.rerun()
