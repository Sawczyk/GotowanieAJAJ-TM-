import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA I STYLE ---
st.set_page_config(page_title="Planer Posiłków", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stButton > button { width: 100%; height: 60px; font-weight: bold; border-radius: 10px; }
    .status-box { padding: 10px; border-radius: 8px; margin: 5px 0; font-size: 0.9rem; border-left: 5px solid; }
    .mam { background-color: #e8f5e9; border-color: #2e7d32; color: #1e4620; }
    .brak { background-color: #ffebee; border-color: #c62828; color: #5f1a1a; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INICJALIZACJA DANYCH (Spiżarnia, Przepisy, Plan) ---
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = pd.DataFrame([
        {"Nazwa": "Jajecznica", "Typ": "Śniadanie", "Skladniki": "jajka, masło"},
        {"Nazwa": "Kurczak z ryżem", "Typ": "Lunch", "Skladniki": "kurczak, ryż, brokuł"}
    ])

if 'spizarnia' not in st.session_state:
    st.session_state.spizarnia = ["masło", "sól"]

if 'plan_wybory' not in st.session_state:
    st.session_state.plan_wybory = {}

if 'page' not in st.session_state:
    st.session_state.page = "Home"

# --- 3. LOGIKA POMOCNICZA ---
DNI = {0: "Poniedziałek", 1: "Wtorek", 2: "Środa", 3: "Czwartek", 4: "Piątek", 5: "Sobota", 6: "Niedziela"}

def sprawdz_skladniki(danie_nazwa):
    if not danie_nazwa or danie_nazwa == "Brak": return None
    przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == danie_nazwa]
    if przepis.empty: return None
    wymagane = [s.strip().lower() for s in przepis.iloc[0]['Skladniki'].split(',')]
    mam = [s for s in wymagane if s in st.session_state.spizarnia]
    brak = [s for s in wymagane if s not in st.session_state.spizarnia]
    return {"mam": mam, "brak": brak}

# --- 4. NAWIGACJA (DASHBOARD) ---
if st.session_state.page == "Home":
    st.title("🍴 Twój Planer Posiłków")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📅 MÓJ PLAN"): st.session_state.page = "Plan"; st.rerun()
        if st.button("🏠 MOJA SPIŻARNIA"): st.session_state.page = "Spizarnia"; st.rerun()
    with col2:
        if st.button("➕ DODAJ PRZEPIS"): st.session_state.page = "Dodaj"; st.rerun()
        if st.button("🛒 LISTA ZAKUPÓW"): st.session_state.page = "Zakupy"; st.rerun()

# --- 5. MODUŁ: PLANOWANIE ---
elif st.session_state.page == "Plan":
    if st.button("⬅ POWRÓT DO MENU"): st.session_state.page = "Home"; st.rerun()
    st.header("Planowanie na 7 dni")
    
    for i in range(7):
        data = datetime.now() + timedelta(days=i)
        data_str = data.strftime("%Y-%m-%d")
        label = f"{DNI[data.weekday()]} ({data_str})"
        
        with st.expander(label, expanded=(i==0)):
            for p_typ in ["Śniadanie", "Lunch", "Kolacja"]:
                klucz = f"{data_str}_{p_typ}"
                opcje = ["Brak"] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == p_typ]['Nazwa'].tolist()
                
                domyslny_idx = 0
                if klucz in st.session_state.plan_wybory:
                    if st.session_state.plan_wybory[klucz] in opcje:
                        domyslny_idx = opcje.index(st.session_state.plan_wybory[klucz])

                wybor = st.selectbox(f"{p_typ}:", opcje, index=domyslny_idx, key=klucz)
                st.session_state.plan_wybory[klucz] = wybor
                
                res = sprawdz_skladniki(wybor)
                if res:
                    if res['mam']: st.markdown(f"<div class='status-box mam'>✅ Mam: {', '.join(res['mam'])}</div>", unsafe_allow_html=True)
                    if res['brak']: st.markdown(f"<div class='status-box brak'>🛒 Kup: {', '.join(res['brak'])}</div>", unsafe_allow_html=True)

# --- 6. MODUŁ: SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    if st.button("⬅ POWRÓT DO MENU"): st.session_state.page = "Home"; st.rerun()
    st.header("Zarządzaj swoją spiżarnią")
    nowy = st.text_input("Dodaj produkt, który masz (np. jajka, mleko):").lower().strip()
    if st.button("DODAJ DO ZAPASÓW"):
        if nowy and nowy not in st.session_state.spizarnia:
            st.session_state.spizarnia.append(nowy)
            st.rerun()
    
    st.write("---")
    st.subheader("Produkty w domu (kliknij, aby usunąć):")
    cols = st.columns(4)
    for idx, item in enumerate(sorted(st.session_state.spizarnia)):
        if cols[idx % 4].button(f"🗑️ {item}", key=f"inv_{item}"):
            st.session_state.spizarnia.remove(item)
            st.rerun()

# --- 7. MODUŁ: DODAJ PRZEPIS ---
elif st.session_state.page == "Dodaj":
    if st.button("⬅ POWRÓT DO MENU"): st.session_state.page = "Home"; st.rerun()
    st.header("Dodaj nowy przepis do bazy")
    with st.form("new_recipe_form"):
        nazwa = st.text_input("Nazwa potrawy")
        typ = st.selectbox("Typ posiłku", ["Śniadanie", "Lunch", "Kolacja"])
        skladniki = st.text_area("Składniki (rozdzielone przecinkami, np: mąka, jajka, mleko)")
        if st.form_submit_button("ZAPISZ PRZEPIS"):
            if nazwa and skladniki:
                nowy_row = {"Nazwa": nazwa, "Typ": typ, "Skladniki": skladniki.lower()}
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([nowy_row])], ignore_index=True)
                st.success(f"Dodano przepis: {nazwa}")
            else:
                st.error("Wypełnij wszystkie pola!")

# --- 8. MODUŁ: LISTA ZAKUPÓW ---
elif st.session_state.page == "Zakupy":
    if st.button("⬅ POWRÓT DO MENU"): st.session_state.page = "Home"; st.rerun()
    st.header("Twoja inteligentna lista zakupów")
    potrzebne = []
    for danie in st.session_state.plan_wybory.values():
        res = sprawdz_skladniki(danie)
        if res: potrzebne.extend(res['brak'])
    
    lista = sorted(list(set(potrzebne)))
    if lista:
        st.write("Tych rzeczy brakuje Ci do zrealizowania planu:")
        for l in lista: st.checkbox(l, key=f"shopping_{l}")
    else:
        st.success("Masz wszystko w spiżarni! Nie musisz iść na zakupy.")
