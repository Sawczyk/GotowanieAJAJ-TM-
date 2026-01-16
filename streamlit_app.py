import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Ustawienia strony - tryb szeroki i fajna ikona
st.set_page_config(page_title="Mój Planer Posiłków", layout="wide", initial_sidebar_state="collapsed")

# Stylowanie przycisków za pomocą CSS, aby wyglądały jak duże kafle
st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        height: 100px;
        font-size: 20px;
        font-weight: bold;
        border-radius: 15px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🍴 Menu Główne")

# --- INICJALIZACJA DANYCH ---
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = pd.DataFrame([
        {"Nazwa": "Jajecznica", "Typ": "Śniadanie", "Skladniki": "jajka, masło"},
        {"Nazwa": "Kurczak", "Typ": "Lunch", "Skladniki": "kurczak, ryż"},
        {"Nazwa": "Kanapki", "Typ": "Kolacja", "Skladniki": "chleb, ser"}
    ])

if 'plan' not in st.session_state:
    dni = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]
    st.session_state.plan = pd.DataFrame({"Data": dni, "Śniadanie": "", "Lunch": "", "Kolacja": ""})

if 'page' not in st.session_state:
    st.session_state.page = "Home"

# --- NAWIGACJA ---
def set_page(name):
    st.session_state.page = name

# --- DASHBOARD (PULPIT) ---
if st.session_state.page == "Home":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📅 MÓJ PLAN"):
            set_page("Plan")
            st.rerun()
            
    with col2:
        if st.button("➕ DODAJ PRZEPIS"):
            set_page("Dodaj")
            st.rerun()
            
    with col3:
        if st.button("🛒 LISTA ZAKUPÓW"):
            set_page("Zakupy")
            st.rerun()

# --- WIDOK: PLANOWANIE ---
elif st.session_state.page == "Plan":
    if st.button("⬅ Powrót do Menu"):
        set_page("Home")
        st.rerun()
        
    st.subheader("Kalendarz posiłków (30 dni)")
    
    # Wyświetlamy edytor danych z listami rozwijanymi
    options_s = [""] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == "Śniadanie"]['Nazwa'].tolist()
    options_l = [""] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == "Lunch"]['Nazwa'].tolist()
    options_k = [""] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == "Kolacja"]['Nazwa'].tolist()

    edited_plan = st.data_editor(
        st.session_state.plan,
        use_container_width=True,
        column_config={
            "Data": st.column_config.Column(disabled=True),
            "Śniadanie": st.column_config.SelectboxColumn("Śniadanie", options=options_s),
            "Lunch": st.column_config.SelectboxColumn("Lunch", options=options_l),
            "Kolacja": st.column_config.SelectboxColumn("Kolacja", options=options_k),
        },
        hide_index=True
    )
    
    if st.button("Zapisz zmiany w planie"):
        st.session_state.plan = edited_plan
        st.success("Plan zapisany!")

# --- WIDOK: DODAWANIE ---
elif st.session_state.page == "Dodaj":
    if st.button("⬅ Powrót do Menu"):
        set_page("Home")
        st.rerun()
        
    st.subheader("Dodaj nowe danie")
    with st.form("recipe_form"):
        n = st.text_input("Nazwa dania")
        t = st.selectbox("Typ", ["Śniadanie", "Lunch", "Kolacja"])
        s = st.text_area("Składniki (rozdziel przecinkiem)")
        if st.form_submit_button("Dodaj przepis"):
            new_row = {"Nazwa": n, "Typ": t, "Skladniki": s}
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([new_row])], ignore_index=True)
            st.success(f"Dodano: {n}")

# --- WIDOK: ZAKUPY ---
elif st.session_state.page == "Zakupy":
    if st.button("⬅ Powrót do Menu"):
        set_page("Home")
        st.rerun()
        
    st.subheader("Twoja lista zakupów")
    
    # Zbierz wszystkie wybrane dania z planu
    all_selected = pd.concat([st.session_state.plan['Śniadanie'], st.session_state.plan['Lunch'], st.session_state.plan['Kolacja']])
    all_selected = all_selected[all_selected != ""] # usuń puste
    
    # Wyciągnij składniki
    recipes_in_plan = st.session_state.przepisy[st.session_state.przepisy['Nazwa'].isin(all_selected)]
    
    full_list = []
    for ingredient_string in recipes_in_plan['Skladniki']:
        items = [i.strip() for i in ingredient_string.split(',')]
        full_list.extend(items)
    
    unique_ingredients = sorted(list(set(full_list)))
    
    if unique_ingredients:
        for ing in unique_ingredients:
            st.checkbox(ing, key=ing)
    else:
        st.info("Brak produktów. Najpierw zaplanuj posiłki!")
