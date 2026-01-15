import streamlit as st
import random

# ==============================
# 페이지 설정
# ==============================
st.set_page_config(
    page_title="Phonics Games - BCA",
    page_icon="📚",
    layout="wide"
)

# ==============================
# 사운드 재생 체크
# ==============================
if "pending_sound" in st.session_state and st.session_state.pending_sound:
    sound_type = st.session_state.pending_sound
    st.session_state.pending_sound = None
    
    sound_urls = {
        "correct": "https://drive.google.com/uc?export=download&id=1VOt1cg8jjaMC13qSwNROU-9Q5HpLhxyr",
        "wrong": "https://www.soundjay.com/buttons/sounds/button-10.mp3"
    }
    
    if sound_type in sound_urls:
        st.markdown(f"""
            <audio autoplay>
                <source src="{sound_urls[sound_type]}" type="audio/mpeg">
            </audio>
        """, unsafe_allow_html=True)


def play_sound(sound_type):
    """소리 재생 함수"""
    st.session_state.pending_sound = sound_type


def display_spot_letter(i, letter, spot_answered):
    """Spot It letter card 표시"""
    if i in spot_answered:
        st.markdown(f"""
            <div style="position: relative; text-align: center; height: 200px; 
                        background: white; border-radius: 10px; 
                        display: flex; align-items: center; justify-content: center;">
                <span style="color: #cccccc; font-size: 100px; font-weight: bold;">{letter}</span>
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                            width: 80%; height: 80%; border: 8px solid #00ff00; border-radius: 50%; 
                            background: rgba(0, 255, 0, 0.3); display: flex; align-items: center; justify-content: center;">
                    <span style="color: #00ff00; font-size: 60px; font-weight: bold;">✓</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div style="text-align: center; height: 200px; 
                        background: white; border-radius: 10px; 
                        display: flex; align-items: center; justify-content: center;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
                <span style="color: #333; font-size: 100px; font-weight: bold; font-family: Arial, sans-serif;">
                    {letter}
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        col_o, col_x = st.columns(2)
        
        with col_o:
            if st.button("⭕", key=f"spot_correct_{i}", use_container_width=True):
                st.session_state.spot_answered.append(i)
                play_sound("correct")
                st.rerun()
        
        with col_x:
            if st.button("❌", key=f"spot_wrong_{i}", use_container_width=True):
                play_sound("wrong")
                st.rerun()


# ==============================
# Session State 초기화
# ==============================
if "phonics_mode" not in st.session_state:
    st.session_state.phonics_mode = "home"


# ==============================
# 홈 화면
# ==============================
if st.session_state.phonics_mode == "home":
    st.title("📚 Phonics Games")
    st.subheader("Level 1: Alphabet Recognition")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎰 Letter Spinner", use_container_width=True, type="primary"):
            st.session_state.phonics_mode = "letter_spinner_setup"
            st.rerun()
    
    with col2:
        if st.button("🎯 Spot It!", use_container_width=True, type="primary"):
            st.session_state.phonics_mode = "spot_it_setup"
            st.rerun()


# ==============================
# Letter Spinner Setup
# ==============================
elif st.session_state.phonics_mode == "letter_spinner_setup":
    st.title("🎰 Letter Spinner Setup")
    st.subheader("Choose your letter range:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        letter_range = st.selectbox(
            "Letter Range:",
            ["A-Z (All)", "A-M (First Half)", "N-Z (Second Half)", "Vowels Only (A,E,I,O,U)", "Custom"],
            key="letter_range"
        )
    
    with col2:
        case_type = st.radio(
            "Case:",
            ["Uppercase", "Lowercase", "Mixed"],
            horizontal=True,
            key="case_type"
        )
    
    if letter_range == "Custom":
        custom_letters = st.text_input(
            "Enter letters (separated by comma):",
            placeholder="A, B, C, D, E",
            key="custom_letters"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶ Start Game", use_container_width=True, type="primary"):
            if letter_range == "A-Z (All)":
                letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            elif letter_range == "A-M (First Half)":
                letters = list("ABCDEFGHIJKLM")
            elif letter_range == "N-Z (Second Half)":
                letters = list("NOPQRSTUVWXYZ")
            elif letter_range == "Vowels Only (A,E,I,O,U)":
                letters = list("AEIOU")
            else:
                if "custom_letters" in st.session_state and st.session_state.custom_letters:
                    letters = [l.strip().upper() for l in st.session_state.custom_letters.split(",")]
                else:
                    st.warning("Please enter custom letters!")
                    st.stop()
            
            if case_type == "Lowercase":
                letters = [l.lower() for l in letters]
            elif case_type == "Mixed":
                letters = letters + [l.lower() for l in letters]
            
            st.session_state.spinner_letters = letters
            st.session_state.phonics_mode = "letter_spinner"
            st.session_state.spinning = False
            st.session_state.current_letter = random.choice(letters)
            st.rerun()
    
    with col2:
        if st.button("⬅ Back", use_container_width=True):
            st.session_state.phonics_mode = "home"
            st.rerun()


# ==============================
# Letter Spinner Game
# ==============================
elif st.session_state.phonics_mode == "letter_spinner":
    st.title("🎰 Letter Spinner")
    
    if "spinning" not in st.session_state:
        st.session_state.spinning = False
    if "current_letter" not in st.session_state:
        st.session_state.current_letter = random.choice(st.session_state.spinner_letters)
    
    st.markdown(f"""
        <div style="display: flex; justify-content: center; align-items: center; height: 400px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
            <span style="color: white; font-size: 200px; font-weight: bold; font-family: Arial, sans-serif;">
                {st.session_state.current_letter}
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🎲 Start Spin", use_container_width=True, type="primary", disabled=st.session_state.spinning):
            st.session_state.spinning = True
            for _ in range(10):
                st.session_state.current_letter = random.choice(st.session_state.spinner_letters)
            st.rerun()
    
    with col2:
        if st.button("⏸ Stop", use_container_width=True, disabled=not st.session_state.spinning):
            st.session_state.spinning = False
            play_sound("correct")
            st.rerun()
    
    with col3:
        if st.button("➡ Next", use_container_width=True):
            st.session_state.current_letter = random.choice(st.session_state.spinner_letters)
            st.session_state.spinning = False
            st.rerun()
    
    with col4:
        if st.button("⬅ Back", use_container_width=True):
            st.session_state.phonics_mode = "letter_spinner_setup"
            st.rerun()
    
    if st.session_state.spinning:
        import time
        time.sleep(0.1)
        st.session_state.current_letter = random.choice(st.session_state.spinner_letters)
        st.rerun()


# ==============================
# Spot It Setup
# ==============================
elif st.session_state.phonics_mode == "spot_it_setup":
    st.title("🎯 Spot It! Setup")
    st.subheader("Choose your settings:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        letter_range = st.selectbox(
            "Letter Range:",
            ["A-Z (All)", "A-M (First Half)", "N-Z (Second Half)", "Vowels Only", "Custom"],
            key="spot_letter_range"
        )
    
    with col2:
        num_cards = st.selectbox(
            "Number of Cards:",
            [4, 8, 12],
            key="spot_num_cards"
        )
    
    case_type = st.radio(
        "Case:",
        ["Uppercase", "Lowercase", "Mixed"],
        horizontal=True,
        key="spot_case_type"
    )
    
    if letter_range == "Custom":
        custom_letters = st.text_input(
            "Enter letters (separated by comma):",
            placeholder="A, B, C, D, E",
            key="spot_custom_letters"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶ Start Game", use_container_width=True, type="primary"):
            if letter_range == "A-Z (All)":
                letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
            elif letter_range == "A-M (First Half)":
                letters = list("ABCDEFGHIJKLM")
            elif letter_range == "N-Z (Second Half)":
                letters = list("NOPQRSTUVWXYZ")
            elif letter_range == "Vowels Only":
                letters = list("AEIOU")
            else:
                if st.session_state.get("spot_custom_letters"):
                    letters = [l.strip().upper() for l in st.session_state.spot_custom_letters.split(",")]
                else:
                    st.warning("Please enter custom letters!")
                    st.stop()
            
            if case_type == "Lowercase":
                letters = [l.lower() for l in letters]
            elif case_type == "Mixed":
                letters = letters + [l.lower() for l in letters]
            
            if len(letters) < num_cards:
                st.warning(f"Not enough letters! Need at least {num_cards} letters.")
                st.stop()
            
            st.session_state.spot_letters = random.sample(letters, num_cards)
            st.session_state.spot_answered = []
            st.session_state.phonics_mode = "spot_it"
            st.rerun()
    
    with col2:
        if st.button("⬅ Back", use_container_width=True):
            st.session_state.phonics_mode = "home"
            st.rerun()


# ==============================
# Spot It Game
# ==============================
elif st.session_state.phonics_mode == "spot_it":
    st.title("🎯 Spot It!")
    
    st.markdown("### 👨‍🏫 Teacher: Call out a letter!")
    target_letter = st.text_input(
        "Which letter should students find?",
        placeholder="Type a letter (e.g., A, b, M)",
        max_chars=1,
        key="target_letter_input"
    )
    
    if target_letter:
        st.info(f"🎯 Target Letter: **{target_letter}**")
    
    st.markdown("---")
    
    if "spot_answered" not in st.session_state:
        st.session_state.spot_answered = []
    
    num_cards = len(st.session_state.spot_letters)
    num_cols = 8
    
    if num_cards <= 8:
        empty_cols_before = (num_cols - num_cards) // 2
        cols = st.columns(num_cols)
        
        for i, letter in enumerate(st.session_state.spot_letters):
            col_position = empty_cols_before + i
            
            with cols[col_position]:
                display_spot_letter(i, letter, st.session_state.spot_answered)
    else:
        first_row_count = (num_cards + 1) // 2
        second_row_count = num_cards - first_row_count
        
        empty_cols_before_1 = (num_cols - first_row_count) // 2
        cols1 = st.columns(num_cols)
        
        for i in range(first_row_count):
            col_position = empty_cols_before_1 + i
            letter = st.session_state.spot_letters[i]
            
            with cols1[col_position]:
                display_spot_letter(i, letter, st.session_state.spot_answered)
        
        empty_cols_before_2 = (num_cols - second_row_count) // 2
        cols2 = st.columns(num_cols)
        
        for j in range(second_row_count):
            i = first_row_count + j
            col_position = empty_cols_before_2 + j
            letter = st.session_state.spot_letters[i]
            
            with cols2[col_position]:
                display_spot_letter(i, letter, st.session_state.spot_answered)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("➡ Next Round", use_container_width=True):
            random.shuffle(st.session_state.spot_letters)
            st.session_state.spot_answered = []
            st.rerun()
    
    with col2:
        if st.button("⬅ Back", use_container_width=True):
            st.session_state.phonics_mode = "home"
            st.rerun()
