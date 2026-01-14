import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
import random
import re
import base64

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


def play_sound(sound_type):
    """소리 재생 함수"""
    if sound_type == "correct":
        # 딩동댕 소리 - 성공음
        st.markdown("""
            <audio autoplay>
                <source src="https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3" type="audio/mpeg">
            </audio>
        """, unsafe_allow_html=True)
    elif sound_type == "wrong":
        # 삑 소리 - 오답음
        st.markdown("""
            <audio autoplay>
                <source src="https://assets.mixkit.co/active_storage/sfx/2955/2955-preview.mp3" type="audio/mpeg">
            </audio>
        """, unsafe_allow_html=True)
    elif sound_type == "celebration":
        # 와아~ 축하 소리
        st.markdown("""
            <audio autoplay>
                <source src="https://assets.mixkit.co/active_storage/sfx/1435/1435-preview.mp3" type="audio/mpeg">
            </audio>
        """, unsafe_allow_html=True)


# ==============================
# Streamlit UI 설정
# ==============================
st.set_page_config(page_title="BCA Flashcards", layout="wide")

# 반응형 CSS 추가
st.markdown("""
    <style>
        /* 반응형 이미지 크기 조정 */
        img {
            max-width: 100%;
            height: auto;
        }
        
        /* 모바일 */
        @media (max-width: 768px) {
            .stImage img {
                max-height: 300px;
            }
        }
        
        /* 태블릿 */
        @media (min-width: 769px) and (max-width: 1024px) {
            .stImage img {
                max-height: 400px;
            }
        }
        
        /* 데스크톱 */
        @media (min-width: 1025px) {
            .stImage img {
                max-height: 500px;
            }
        }
    </style>
""", unsafe_allow_html=True)

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
if "slap_answered" not in st.session_state:
    st.session_state.slap_answered = []
if "memory_flipped" not in st.session_state:
    st.session_state.memory_flipped = []
if "memory_matched" not in st.session_state:
    st.session_state.memory_matched = []


# ==============================
# 1단계: 단어 입력 화면
# ==============================
if st.session_state.mode == "home":
    st.title("📚 BCA Flashcards")
    st.subheader("Type words (comma separated), then press Enter.")

    words = st.text_input(
        "Flashcards",
        placeholder="e.g., bucket, apple, maze, rabbit",
        label_visibility="collapsed",
        key="word_input",
        on_change=None  # Will process on Enter
    )

    # ✅ Check Existing Words button
    col1, col2 = st.columns([1, 3])
    
    with col1:
        check_button = st.button("🔍 Check Existing Words", use_container_width=True)
    
    if check_button and words:
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
        found_words = []
        not_found = []
        
        for word in input_words:
            if word in file_map:
                found_words.append(f"{word} ({len(file_map[word])} cards)")
            else:
                not_found.append(word)
        
        # 결과 표시
        st.markdown("---")
        if found_words:
            st.success(f"✅ **Found ({len(found_words)} words):**")
            st.write(", ".join(found_words))
        
        if not_found:
            st.error(f"❌ **Not Found ({len(not_found)} words):**")
            st.write(", ".join(not_found))
            
            # Copy button for missing words
            missing_text = ", ".join(not_found)
            st.code(missing_text, language=None)
            if st.button("📋 Copy Missing Words to Clipboard"):
                st.write("Copy this text: " + missing_text)
    
    elif not words and check_button:
        st.warning("⚠️ Please enter some words first.")

    # Process words when entered (on Enter key or after input)
    if words and not check_button:
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
    st.title("📚 BCA Flashcards")
    st.subheader("Preview your flashcards. Select the ones you want.")

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
                            to_add.append(f"https://drive.google.com/thumbnail?id={file_id}&sz=w800")

                if to_add:
                    st.session_state.cards = list(dict.fromkeys(st.session_state.cards + to_add))
                st.session_state.show_input = False
                st.rerun()

    # -------------------------
    # Gallery
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
        # Game Buttons
        # -------------------------
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🎮 Games & Activities")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("▶ Presentation", use_container_width=True):
                st.session_state.mode = "present"
                st.session_state.current = 0
                st.rerun()
        
        with col2:
            if st.button("🔍 Hide & Seek", use_container_width=True):
                if st.session_state.selected_cards:
                    st.session_state.mode = "hide_seek"
                    st.session_state.current = 0
                    st.session_state.zoom_level = 1
                    st.rerun()
        
        with col3:
            if st.button("🧠 Memory Game", use_container_width=True):
                if len(st.session_state.selected_cards) >= 4:
                    st.session_state.mode = "memory_setup"
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🎯 Slap the Board Game")
        st.write("Select number of cards to show:")
        
        slap_cols = st.columns(3)
        
        with slap_cols[0]:
            if st.button("4 Cards (2x2)", key="slap_4", use_container_width=True):
                if len(st.session_state.selected_cards) >= 4:
                    st.session_state.mode = "slap_board"
                    st.session_state.game_cards = random.sample(st.session_state.selected_cards, 4)
                    st.session_state.slap_answered = []
                    st.rerun()
        
        with slap_cols[1]:
            if st.button("6 Cards (2x3)", key="slap_6", use_container_width=True):
                if len(st.session_state.selected_cards) >= 6:
                    st.session_state.mode = "slap_board"
                    st.session_state.game_cards = random.sample(st.session_state.selected_cards, 6)
                    st.session_state.slap_answered = []
                    st.rerun()
        
        with slap_cols[2]:
            if st.button("8 Cards (4x2)", key="slap_8", use_container_width=True):
                if len(st.session_state.selected_cards) >= 8:
                    st.session_state.mode = "slap_board"
                    st.session_state.game_cards = random.sample(st.session_state.selected_cards, 8)
                    st.session_state.slap_answered = []
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.mode = "home"
            st.rerun()


# ==============================
# Slap the Board Game
# ==============================
elif st.session_state.mode == "slap_board":
    st.title("🎯 Slap the Board!")
    st.subheader(f"Find the correct card! ({len(st.session_state.game_cards)} cards)")
    
    if "selected_slap_card" not in st.session_state:
        st.session_state.selected_slap_card = None
    
    if st.session_state.game_cards:
        num_cards = len(st.session_state.game_cards)
        
        # Determine grid layout
        if num_cards == 4:
            cols_per_row = 2  # 2x2
        elif num_cards == 6:
            cols_per_row = 3  # 2x3
        elif num_cards == 8:
            cols_per_row = 4  # 4x2
        else:
            cols_per_row = min(5, num_cards)
        
        # Display cards in grid
        for row_start in range(0, num_cards, cols_per_row):
            row_cards = st.session_state.game_cards[row_start:row_start + cols_per_row]
            cols = st.columns(len(row_cards))
            
            for i, url in enumerate(row_cards):
                card_idx = row_start + i
                with cols[i]:
                    if card_idx in st.session_state.slap_answered:
                        # Show trophy instead of card
                        st.markdown("""
                            <div style="text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; height: 350px; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                                <div style="font-size: 80px;">🏆</div>
                                <div style="color: white; font-size: 24px; font-weight: bold; margin-top: 10px;">Correct!</div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Make card clickable (A4 ratio)
                        if st.button(f"Select Card {card_idx + 1}", key=f"slap_card_{card_idx}", use_container_width=True):
                            st.session_state.selected_slap_card = card_idx
                            st.rerun()
                        
                        # Display card image on top of button with A4 ratio
                        st.markdown(f"""
                            <div style="margin-top: -40px; pointer-events: none;">
                                <img src="{url}" style="width: 100%; height: 350px; object-fit: contain; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); background: white;">
                            </div>
                        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Show Correct/Wrong buttons if a card is selected
        if st.session_state.selected_slap_card is not None:
            st.info(f"Card {st.session_state.selected_slap_card + 1} selected! Is it correct?")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("✅ Correct!", use_container_width=True, type="primary"):
                    st.session_state.slap_answered.append(st.session_state.selected_slap_card)
                    st.session_state.selected_slap_card = None
                    play_sound("correct")
                    st.rerun()
            
            with col2:
                if st.button("❌ Wrong!", use_container_width=True):
                    st.session_state.selected_slap_card = None
                    play_sound("wrong")
                    st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Control buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("➡ Next Round", use_container_width=True):
                st.session_state.game_cards = random.sample(st.session_state.selected_cards, len(st.session_state.game_cards))
                st.session_state.slap_answered = []
                st.session_state.selected_slap_card = None
                st.rerun()
        
        with col2:
            if st.button("⬅ Back to Gallery", use_container_width=True):
                st.session_state.mode = "gallery"
                st.session_state.selected_slap_card = None
                st.rerun()


# ==============================
# Memory Game Setup
# ==============================
elif st.session_state.mode == "memory_setup":
    st.title("🧠 Memory Game Setup")
    st.subheader("How many pairs do you want?")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.write("")  # Empty space
    
    with col2:
        if st.button("4 Cards (2 pairs)", use_container_width=True):
            pairs = random.sample(st.session_state.selected_cards, min(2, len(st.session_state.selected_cards)))
            st.session_state.game_cards = pairs + pairs
            random.shuffle(st.session_state.game_cards)
            st.session_state.memory_flipped = []
            st.session_state.memory_matched = []
            st.session_state.mode = "memory_game"
            st.rerun()
    
    with col3:
        st.write("")  # Empty space
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.write("")
    
    with col2:
        if st.button("8 Cards (4 pairs)", use_container_width=True):
            pairs = random.sample(st.session_state.selected_cards, min(4, len(st.session_state.selected_cards)))
            st.session_state.game_cards = pairs + pairs
            random.shuffle(st.session_state.game_cards)
            st.session_state.memory_flipped = []
            st.session_state.memory_matched = []
            st.session_state.mode = "memory_game"
            st.rerun()
    
    with col3:
        st.write("")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⬅ Back to Gallery"):
        st.session_state.mode = "gallery"
        st.rerun()


# ==============================
# Memory Game
# ==============================
elif st.session_state.mode == "memory_game":
    st.title("🧠 Memory Game")
    st.subheader("Find matching pairs!")
    
    # Card back colors and numbers
    colors = ["#9B59B6", "#3498DB", "#2ECC71", "#E67E22", "#E74C3C", "#F39C12"]
    color_names = ["Purple", "Blue", "Green", "Orange", "Red", "Yellow"]
    
    # Add waiting state for wrong matches
    if "memory_waiting" not in st.session_state:
        st.session_state.memory_waiting = False
    
    if st.session_state.game_cards:
        num_cards = len(st.session_state.game_cards)
        
        # Always show 4 cards per row
        num_cols = 4
        
        for row_start in range(0, num_cards, num_cols):
            row_cards = st.session_state.game_cards[row_start:row_start + num_cols]
            cols = st.columns(len(row_cards))
            
            for i, url in enumerate(row_cards):
                card_idx = row_start + i
                color_idx = card_idx % len(colors)
                
                with cols[i]:
                    if card_idx in st.session_state.memory_matched:
                        # Matched card - show with green circle overlay (A4 ratio: 1:1.414)
                        st.markdown(f"""
                            <div style="position: relative;
                                        width: 100%;
                                        height: 300px;
                                        overflow: hidden;
                                        border-radius: 10px;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        background: white;
                                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                                <img src="{url}" style="width: 100%; height: 100%; object-fit: contain; border-radius: 10px;">
                                <div style="position: absolute;
                                            top: 50%;
                                            left: 50%;
                                            transform: translate(-50%, -50%);
                                            width: 75%;
                                            height: 75%;
                                            border: 8px solid #00ff00;
                                            border-radius: 50%;
                                            background: rgba(0, 255, 0, 0.25);
                                            display: flex;
                                            align-items: center;
                                            justify-content: center;">
                                    <span style="color: #00ff00; font-size: 60px; font-weight: bold;">✓</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    elif card_idx in st.session_state.memory_flipped:
                        # Flipped card - show image (A4 ratio)
                        st.markdown(f"""
                            <div style="width: 100%;
                                        height: 300px;
                                        overflow: hidden;
                                        border-radius: 10px;
                                        display: flex;
                                        align-items: center;
                                        justify-content: center;
                                        background: white;
                                        border: 3px solid gold;
                                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                                <img src="{url}" style="width: 100%; height: 100%; object-fit: contain; border-radius: 10px;">
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        # Face-down card - show colored back (A4 ratio)
                        card_display_num = card_idx + 1
                        
                        st.markdown(f"""
                            <div style="background: {colors[color_idx]}; 
                                        height: 300px;
                                        border-radius: 10px; 
                                        display: flex; 
                                        flex-direction: column;
                                        align-items: center; 
                                        justify-content: center;
                                        width: 100%;
                                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                                <span style="color: white; font-size: 60px; font-weight: bold;">{card_display_num}</span>
                                <span style="color: rgba(255,255,255,0.8); font-size: 14px; margin-top: 8px;">{color_names[color_idx]}</span>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Button below card
                        if not st.session_state.memory_waiting:
                            if st.button(f"Click Card {card_display_num}", 
                                       key=f"mem_{card_idx}", 
                                       use_container_width=True):
                                st.session_state.memory_flipped.append(card_idx)
                                
                                # Check if 2 cards are flipped
                                if len(st.session_state.memory_flipped) == 2:
                                    idx1, idx2 = st.session_state.memory_flipped
                                    # Check if they match
                                    if st.session_state.game_cards[idx1] == st.session_state.game_cards[idx2]:
                                        st.session_state.memory_matched.extend([idx1, idx2])
                                        st.session_state.memory_flipped = []
                                        play_sound("correct")
                                    else:
                                        # Wrong match - set waiting state to show both cards
                                        st.session_state.memory_waiting = True
                                
                                st.rerun()
    
    # Handle wrong match waiting period
    if st.session_state.memory_waiting:
        play_sound("wrong")
        st.warning("⏳ Take a look at both cards...")
        
        # Auto-hide after delay using JavaScript
        st.markdown("""
            <script>
                setTimeout(function() {
                    window.location.reload();
                }, 2000);
            </script>
        """, unsafe_allow_html=True)
        
        # Reset after showing
        import time
        time.sleep(2)
        st.session_state.memory_flipped = []
        st.session_state.memory_waiting = False
        st.rerun()
    
    # Check if game is complete
    if len(st.session_state.memory_matched) == len(st.session_state.game_cards):
        st.success("🎉 You found all pairs!")
        play_sound("celebration")
        st.balloons()
    
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 New Game", use_container_width=True):
            st.session_state.mode = "memory_setup"
            st.session_state.memory_waiting = False
            st.rerun()
    with col2:
        if st.button("⬅ Back to Gallery", use_container_width=True):
            st.session_state.mode = "gallery"
            st.session_state.memory_waiting = False
            st.rerun()


# ==============================
# Presentation Mode
# ==============================
# ==============================
# Presentation Mode
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
# Hide & Seek Game
# ==============================
elif st.session_state.mode == "hide_seek":
    st.title("🔍 Hide & Seek - Guess the Card!")
    
    if st.session_state.selected_cards:
        current_card = st.session_state.selected_cards[st.session_state.current]
        
        # Zoom styles
        zoom_styles = {
            1: "transform: scale(4); object-fit: cover; height: 400px; width: 400px; object-position: 30% 30%;",
            2: "transform: scale(2.5); object-fit: cover; height: 500px; width: 500px; object-position: 40% 40%;",
            3: "transform: scale(1.5); object-fit: cover; height: 600px; width: 600px;",
            4: "object-fit: contain; max-height: 700px; max-width: 100%;"
        }
        
        st.markdown(f"""
            <div style="display: flex; justify-content: center; align-items: center; overflow: hidden; height: 500px; background: #f0f0f0; border-radius: 10px;">
                <img src="{current_card}?sz=w800" 
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
# What's Missing Game - REMOVED
# ==============================
