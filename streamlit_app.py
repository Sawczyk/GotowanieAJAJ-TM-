import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Inteligentny Planer", layout="wide")

# --- POLSKIE DATY ---
DNI_TYGODNIA = {0: "Poniedziałek", 1: "Wtorek", 2: "Środa", 3: "Czwartek", 4: "Piątek", 5: "Sobota", 6: "Niedziela"}

# --- STYLE CSS ---
st.markdown("""
    <style>
    .stSelectbox { margin-bottom: -15px; }
    .status-box { padding: 10px; border-radius: 5px; margin-top: 5px; font-size: 0.85rem; }
    .mam { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .brak { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
    """, unsafe_allow_html=True)

# --- INICJALIZACJA DANYCH ---
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = pd.DataFrame([
        {"Nazwa": "Jajecznica", "Typ": "Śniadanie", "Skladniki": "jajka, masło, szczypiorek"},
        {"Nazwa": "Kurczak z ryżem", "Typ": "Lunch", "Skladniki": "kurczak, ryż, brokuł"},
        {"Nazwa": "Kanapki", "Typ": "Kolacja", "Skladniki": "chleb, masło, ser"}
    ])

if 'spizarnia' not in st.session_state:
    st.session_state.spizarnia = ["masło", "ryż", "sól"] # Przykładowe zapasy

if 'plan_data' not in st.session_state:
    st.session_state.plan_data = {} # Przechowujemy wybory użytkownika

# --- FUNKCJA SPRAWDZAJĄCA ---
def analiza_skladnikow(danie_nazwa):
    if not danie_nazwa or danie_nazwa == "Brak": return None
    
    przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == danie_nazwa].iloc[0]
    wymagane = [s.strip().lower() for s in przepis['Skladniki'].split(',')]
    
    mam = [s for s in wymagane if s in st.session_state.spizarnia]
    brak = [s for s in wymagane if s not in st.session_state.spizarnia]
    
    return {"mam": mam, "brak": brak}

# --- NAWIGACJA ---
st.title("🍴 Planer Posiłków")
tab1, tab2, tab3, tab4 = st.tabs(["📅 Planowanie", "🏠 Spiżarnia", "➕ Przepisy", "🛒 Zakupy"])

# --- TAB 1: PLANOWANIE ---
with tab1:
    st.header("Plan na tydzień")
    
    for i in range(7):
        data_obj = datetime.now() + timedelta(days=i)
        data_str = data_obj.strftime("%Y-%m-%d")
        dzien_nazwa = DNI_TYGODNIA[data_obj.weekday()]
        
        with st.expander(f"📅 {dzien_nazwa} ({data_str})", expanded=(i==0)):
            for posilek in ["Śniadanie", "Lunch", "Kolacja"]:
                st.write(f"**{posilek}:**")
                opcje = ["Brak"] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == posilek]['Nazwa'].tolist()
                
                # Klucz do zapamiętania wyboru
                key = f"{data_str}_{posilek}"
                wybor = st.selectbox(f"Wybierz {posilek}", opcje, key=key)
                st.session_state.plan_data[key] = wybor
                
                # ANALIZA W CZASIE RZECZYWISTYM
                wynik = analiza_skladnikow(wybor)
                if wynik:
                    col_mam, col_brak = st.columns(2)
                    with col_mam:
                        if wynik['mam']:
                            st.markdown(f"<div class='status-box mam'>✅ Mam: {', '.join(wynik['mam'])}</div>", unsafe_allow_html=True)
                    with col_brak:
                        if wynik['brak']:
                            st.markdown(f"<div class='status-box brak'>🛒 Kup: {', '.join(wynik['brak'])}</div>", unsafe_allow_html=True)
                st.write("---")

# --- TAB 2: SPIŻARNIA ---
with tab2:
    st.header("Moje zapasy")
    nowy = st.text_input("Dodaj produkt, który masz w domu:").lower().strip()
    if st.button("Dodaj do spiżarni"):
        if nowy and nowy not in st.session_state.spizarnia:
            st.session_state.spizarnia.append(nowy)
            st.rerun()
    
    st.write("Wpisz produkty po przecinku, aby dodać masowo:")
    
    st.divider()
    cols = st.columns(3)
    for idx, produkt in enumerate(sorted(st.session_state.spizarnia)):
        if cols[idx % 3].button(f"🗑️ {produkt}", key=f"inv_{produkt}"):
            st.session_state.spizarnia.remove(produkt)
            st.rerun()

# --- TAB 3: PRZEPISY ---
with tab3:
    st.header("Baza przepisów")
    with st.form("nowy_przepis"):
        n = st.text_input("Nazwa dania")
        t = st.selectbox("Typ", ["Śniadanie", "Lunch", "Kolacja"])
        s = st.text_area("Składniki (rozdzielone przecinkami)")
        if st.form_submit_button("Zapisz przepis"):
            nowy_wiersz = {"Nazwa": n, "Typ": t, "Skladniki": s.lower()}
            st.session_state.przepisy = pd.concat([st.session_state.przepisy
