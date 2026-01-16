import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Mój Planer Posiłków", layout="wide")

st.title("🍴 Planer Posiłków MVP")

# PROSTA NAWIGACJA
menu = ["Mój Plan", "Dodaj Przepis", "Lista Zakupów"]
choice = st.sidebar.selectbox("Menu", menu)

# --- FUNKCJA SYMULUJĄCA BAZĘ DANYCH (ZAMIAST GOOGLE SHEETS DLA TESTU) ---
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = pd.DataFrame([
        {"Nazwa": "Jajecznica", "Typ": "Śniadanie", "Skladniki": "jajka, masło, szczypiorek"},
        {"Nazwa": "Kurczak z ryżem", "Typ": "Lunch", "Skladniki": "pierś z kurczaka, ryż, brokuł"},
        {"Nazwa": "Sałatka Cezar", "Typ": "Kolacja", "Skladniki": "sałata, kurczak, parmezan, sos"}
    ])

if 'plan' not in st.session_state:
    dni = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    st.session_state.plan = pd.DataFrame({"Data": dni, "Śniadanie": "", "Lunch": "", "Kolacja": ""})

# --- WIDOKI ---
if choice == "Mój Plan":
    st.subheader("Plan na najbliższe 7 dni")
    # Edytowalna tabela planu
    edited_plan = st.data_editor(st.session_state.plan, use_container_width=True)
    if st.button("Zapisz plan"):
        st.session_state.plan = edited_plan
        st.success("Plan zapisany!")

elif choice == "Dodaj Przepis":
    st.subheader("Dodaj nowe danie")
    with st.form("recipe_form"):
        nowa_nazwa = st.text_input("Nazwa dania")
        nowy_typ = st.selectbox("Typ", ["Śniadanie", "Lunch", "Kolacja"])
        nowe_skladniki = st.text_area("Składniki (po przecinku)")
        if st.form_submit_button("Dodaj do bazy"):
            nowy_przepis = {"Nazwa": nowa_nazwa, "Typ": nowy_typ, "Skladniki": nowe_skladniki}
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([nowy_przepis])], ignore_index=True)
            st.success("Dodano przepis!")

elif choice == "Lista Zakupów":
    st.subheader("Twoja lista zakupów")
    # Logika uproszczona: wyciąga składniki z zaplanowanych dań
    all_planned = pd.concat([st.session_state.plan['Śniadanie'], st.session_state.plan['Lunch'], st.session_state.plan['Kolacja']])
    relevant_recipes = st.session_state.przepisy[st.session_state.przepisy['Nazwa'].isin(all_planned)]
    
    shopping_list = []
    for s in relevant_recipes['Skladniki']:
        shopping_list.extend([item.strip() for item in s.split(',')])
    
    if shopping_list:
        unique_list = sorted(list(set(shopping_list)))
        for item in unique_list:
            st.checkbox(item)
    else:
        st.info("Zaplanuj posiłki, aby zobaczyć listę zakupów.")
