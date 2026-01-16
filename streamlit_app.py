import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Planer Inteligentny PRO", layout="wide", initial_sidebar_state="collapsed")

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNKCJE DANYCH (ODCZYT/ZAPIS) ---
def get_data(worksheet_name):
    try:
        return conn.read(worksheet=worksheet_name, ttl=0) # ttl=0 wymusza świeże dane
    except:
        return pd.DataFrame()

def save_data(df, worksheet_name):
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# Załaduj dane na start
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia' not in st.session_state:
    df_spiz = get_data("Spizarnia")
    st.session_state.spizarnia = df_spiz['Produkt'].tolist() if not df_spiz.empty else []
if 'plan_df' not in st.session_state:
    st.session_state.plan_df = get_data("Plan")

if 'page' not in st.session_state:
    st.session_state.page = "Home"

# --- 3. LOGIKA POMOCNICZA ---
DNI = {0: "Poniedziałek", 1: "Wtorek", 2: "Środa", 3: "Czwartek", 4: "Piątek", 5: "Sobota", 6: "Niedziela"}

def sprawdz_skladniki(danie_nazwa):
    if not danie_nazwa or danie_nazwa == "Brak" or st.session_state.przepisy.empty: return None
    przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == danie_nazwa]
    if przepis.empty: return None
    wymagane = [s.strip().lower() for s in str(przepis.iloc[0]['Skladniki']).split(',')]
    mam = [s for s in wymagane if s in st.session_state.spizarnia]
    brak = [s for s in wymagane if s not in st.session_state.spizarnia]
    return {"mam": mam, "brak": brak}

# --- 4. NAWIGACJA (HOME) ---
if st.session_state.page == "Home":
    st.title("🍴 Mój Inteligentny Planer")
    st.write("Witaj! Wszystkie Twoje zmiany są automatycznie zapisywane w Google Sheets.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📅 MÓJ PLAN"): st.session_state.page = "Plan"; st.rerun()
        if st.button("🏠 MOJA SPIŻARNIA"): st.session_state.page = "Spizarnia"; st.rerun()
    with c2:
        if st.button("➕ DODAJ PRZEPIS"): st.session_state.page = "Dodaj"; st.rerun()
        if st.button("🛒 LISTA ZAKUPÓW"): st.session_state.page = "Zakupy"; st.rerun()

# --- 5. MODUŁ: PLANOWANIE ---
elif st.session_state.page == "Plan":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.header("Planowanie na najbliższe 7 dni")
    
    for i in range(7):
        data = datetime.now() + timedelta(days=i)
        data_str = data.strftime("%Y-%m-%d")
        naglowek = f"{DNI[data.weekday()]} ({data_str})"
        
        with st.expander(naglowek, expanded=(i==0)):
            for p_typ in ["Śniadanie", "Lunch", "Kolacja"]:
                klucz = f"{data_str}_{p_typ}"
                
                # Szukaj zapisanego wyboru w DataFrame Plan
                istniejacy_wybor = "Brak"
                if not st.session_state.plan_df.empty:
                    match = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == klucz]
                    if not match.empty:
                        istniejacy_wybor = match.iloc[0]['Wybor']

                opcje = ["Brak"] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == p_typ]['Nazwa'].tolist() if not st.session_state.przepisy.empty else ["Brak"]
                
                wybor = st.selectbox(f"{p_typ}:", opcje, index=opcje.index(istniejacy_wybor) if istniejacy_wybor in opcje else 0, key=klucz)
                
                # Zapisz jeśli zmieniono
                if wybor != istniejacy_wybor:
                    new_plan = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != klucz]
                    new_plan = pd.concat([new_plan, pd.DataFrame([{"Klucz": klucz, "Wybor": wybor}])], ignore_index=True)
                    st.session_state.plan_df = new_plan
                    save_data(new_plan, "Plan")
                    st.toast(f"Zapisano: {wybor}")

                res = sprawdz_skladniki(wybor)
                if res:
                    c1, c2 = st.columns(2)
                    if res['mam']: c1.info(f"✅ Mam: {', '.join(res['mam'])}")
                    if res['brak']: c2.warning(f"🛒 Brak: {', '.join(res['brak'])}")

# --- 6. MODUŁ: SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.header("Spiżarnia")
    nowy = st.text_input("Dodaj produkt:").lower().strip()
    if st.button("DODAJ"):
        if nowy and nowy not in st.session_state.spizarnia:
            st.session_state.spizarnia.append(nowy)
            save_data(pd.DataFrame({"Produkt": st.session_state.spizarnia}), "Spizarnia")
            st.rerun()
    
    st.write("Twoje produkty (kliknij by usunąć):")
    cols = st.columns(4)
    for idx, item in enumerate(sorted(st.session_state.spizarnia)):
        if cols[idx % 4].button(f"🗑️ {item}", key=f"inv_{item}"):
            st.session_state.spizarnia.remove(item)
            save_data(pd.DataFrame({"Produkt": st.session_state.spizarnia}), "Spizarnia")
            st.rerun()

# --- 7. MODUŁ: DODAJ PRZEPIS ---
elif st.session_state.page == "Dodaj":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    with st.form("new_r"):
        n = st.text_input("Nazwa potrawy")
        t = st.selectbox("Typ", ["Śniadanie", "Lunch", "Kolacja"])
        s = st.text_area("Sk
