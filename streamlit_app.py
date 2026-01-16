import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Planer Inteligentny", layout="wide")

# Polski format dni tygodnia
DNI_TYGODNIA = {0: "Poniedziałek", 1: "Wtorek", 2: "Środa", 3: "Czwartek", 4: "Piątek", 5: "Sobota", 6: "Niedziela"}

# --- STYLE CSS DLA WYGODY ---
st.markdown("""
    <style>
    .stSelectbox { margin-bottom: -10px; }
    .status-box { padding: 8px; border-radius: 8px; margin-top: 5px; font-size: 0.9rem; }
    .mam { background-color: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }
    .brak { background-color: #ffebee; color: #c62828; border: 1px solid #ffcdd2; }
    </style>
    """, unsafe_allow_html=True)

# --- INICJALIZACJA DANYCH (SESJA TYMCZASOWA) ---
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = pd.DataFrame([
        {"Nazwa": "Jajecznica", "Typ": "Śniadanie", "Skladniki": "jajka, masło"},
        {"Nazwa": "Kurczak z ryżem", "Typ": "Lunch", "Skladniki": "kurczak, ryż, brokuł"}
    ])

if 'spizarnia' not in st.session_state:
    st.session_state.spizarnia = ["masło", "sól", "pieprz"]

if 'plan_data' not in st.session_state:
    st.session_state.plan_data = {}

# --- FUNKCJA ANALIZY ---
def analiza_skladnikow(danie_nazwa):
    if not danie_nazwa or danie_nazwa == "Brak":
        return None
    
    przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == danie_nazwa]
    if przepis.empty:
        return None
        
    skladniki_str = przepis.iloc[0]['Skladniki']
    wymagane = [s.strip().lower() for s in skladniki_str.split(',')]
    
    mam = [s for s in wymagane if s in st.session_state.spizarnia]
    brak = [s for s in wymagane if s not in st.session_state.spizarnia]
    
    return {"mam": mam, "brak": brak}

# --- GŁÓWNY INTERFEJS ---
st.title("🍴 Mój Planer")

tab1, tab2, tab3, tab4 = st.tabs(["📅 Planowanie", "🏠 Moja Spiżarnia", "➕ Dodaj Przepis", "🛒 Lista Zakupów"])

# --- TAB 1: PLANOWANIE ---
with tab1:
    st.header("Plan na tydzień")
    for i in range(7):
        data_obj = datetime.now() + timedelta(days=i)
        data_str = data_obj.strftime("%Y-%m-%d")
        naglowek = f"{DNI_TYGODNIA[data_obj.weekday()]} ({data_str})"
        
        with st.expander(naglowek, expanded=(i==0)):
            for posilek in ["Śniadanie", "Lunch", "Kolacja"]:
                st.write(f"**{posilek}**")
                opcje = ["Brak"] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == posilek]['Nazwa'].tolist()
                
                klucz = f"{data_str}_{posilek}"
                wybor = st.selectbox(f"Co jemy na {posilek}?", opcje, key=klucz)
                st.session_state.plan_data[klucz] = wybor
