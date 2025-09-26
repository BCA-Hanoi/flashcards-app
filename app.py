# ==============================
# 2단계: 갤러리 미리보기 화면
# ==============================
elif st.session_state.mode == "gallery":
    st.title("BCA Flashcards")
    st.subheader("Preview your flashcards below.")

    if st.session_state.cards:
        # 반응형 갤러리 (기본 8열)
        cols = st.columns(st.session_state.gallery_cols)
        for i, url in enumerate(st.session_state.cards):
            with cols[i % st.session_state.gallery_cols]:
                st.image(url, use_container_width=True)

        # ===== 버튼 영역 (왼쪽 정렬) =====
        st.markdown("<br>", unsafe_allow_html=True)  # 여백
        button_cols = st.columns([1,1,1,1,6])  # 버튼 4개 + 오른쪽 여백
        with button_cols[0]:
            if st.button("➕ Add More", key="add_more"):
                st.session_state.mode = "home"
                st.rerun()
        with button_cols[1]:
            if st.button("▶ Presentation", key="present_btn"):
                st.session_state.mode = "present"
                st.session_state.current = 0
                st.rerun()
        with button_cols[2]:
            if st.button("⬅ Home", key="back_home"):
                st.session_state.mode = "home"
                st.rerun()
        with button_cols[3]:
            if st.button("🗑 Clear All", key="clear_all"):
                st.session_state.cards = []
                st.rerun()

    else:
        st.warning("⚠️ No cards loaded. Please go back and try again.")
        if st.button("⬅ Back to Home", key="back_home_empty"):
            st.session_state.mode = "home"
            st.rerun()
