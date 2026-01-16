import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 1. KONFIGURACJA I TWOJE ULUBIONE STYLE ---
st.set_page_config(page_title="Planer Kuchni", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; }

    .day-banner {
        background-color: #2E7D32;
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .day-banner h1 { margin: 0; font-size: 2.2rem; }
    .day-banner p { margin: 5px 0 0 0; font-size: 1.1rem; opacity: 0.9; }

    div.stButton > button {
        border-radius: 10px;
        padding: 15px 10px !important;
        font-weight: 600 !important;
        border: 1px solid #444;
    }
    div.stButton > button[kind="primary"] {
        background-color: #2E7D32 !important;
        color: white !important;
        border: none !important;
        height: 55px !important;
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BEZPIECZNE POŁĄCZENIE Z DANYMI ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_load(worksheet_name, columns):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=columns)
        df = df.dropna(how='all').reset_index(drop=True)
        df.columns = [str(c).strip() for c in df.columns]
        for col in columns:
            if col not in df.columns: df[col] = ""
        return df[columns]
    except:
        return pd.DataFrame(columns=columns)

def save_now(df, worksheet_name):
    try:
        conn.update(worksheet=ws_map[worksheet_name], data=df.dropna(how='all'))
        st.cache_data.clear()
        st.toast(f"✅ Zapisano w {worksheet_name}!")
        return True
    except:
        st.error("Błąd zapisu!")
        return False

ws_map = {"Przepisy": "Przepisy", "Spizarnia": "Spizarnia", "Plan": "Plan"}

# --- 3. INICJALIZACJA ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

if 'przepisy' not in st.session_state: st.session_state.przepisy = safe_load("Przepisy", ["Nazwa", "Skladnik", "Ilosc"])
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = safe_load("Spizarnia", ["Produkt", "Ilosc", "Czy_Stale", "Min_Ilosc"])
if 'plan_df' not in st.session_state: st.session_state.plan_df = safe_load("Plan", ["Klucz", "Wybor"])

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
miesiace_pl = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]

# --- 4. STRONY ---

if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"<div class='day-banner'><h1>{dni_pl[teraz.weekday()]}</h1><p>{teraz.day} {miesiace_pl[teraz.month-1]} {teraz.year}</p></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: 
        if st.button("📅\nPLAN", use_container_width=True): st.session_state.page = "Plan"; st.rerun()
    with c2: 
        if st.button("🏠\nSPIŻARNIA", use_container_width=True): st.session_state.page = "Spizarnia"; st.rerun()
    with c3: 
        if st.button("📖\nPRZEPISY", use_container_width=True): st.session_state.page = "Dodaj"; st.rerun()
    with c4: 
        if st.button("🛒\nZAKUPY", use_container_width=True): st.session_state.page = "Zakupy"; st.rerun()

elif st.session_state.page == "Plan":
    st.subheader("📅 Plan Posiłków")
    c_back, c_save = st.columns([1, 1])
    if c_back.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    if c_save.button("💾 ZAPISZ CAŁY PLAN", type="primary"):
        save_now(st.session_state.plan_df, "Plan")

    c_p, c_c, c_n = st.columns([1, 2, 1])
    if c_p.button("⬅ Poprzedni tydzień"): st.session_state.week_offset -= 1; st.rerun()
    if c_n.button("Następny tydzień ➡"): st.session_state.week_offset += 1; st.rerun()
    
    start = datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)
    t_id = start.strftime("%Y-%V")
    
    for i, d_n in enumerate(dni_pl):
        with st.expander(f"{d_n} ({(start + timedelta(days=i)).strftime('%d.%m')})"):
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{d_n}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if k in st.session_state.plan_df['Klucz'].values else "Brak"
                opcje = ["Brak"] + sorted(st.session_state.przepisy['Nazwa'].astype(str).unique().tolist())
                if "" in opcje: opcje.remove("")
                
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                if wyb != istn:
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([st.session_state.plan_df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)

elif st.session_state.page == "Spizarnia":
    st.subheader("🏠 Spiżarnia")
    c_back, c_save = st.columns([1, 1])
    if c_back.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    if c_save.button("💾 ZAPISZ STAN SPIŻARNI", type="primary"):
        save_now(st.session_state.spizarnia_df, "Spizarnia")
    
    with st.expander("➕ Dodaj nowy produkt"):
        with st.form("new_s", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            n, q, s, m = c1.text_input("Nazwa"), c2.number_input("Ilość", 0.0), c3.checkbox("Stały?"), c4.number_input("Min", 0.0)
            if st.form_submit_button("Dodaj do listy"):
                st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}])], ignore_index=True)
                st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        nq = c2.number_input("I", float(row['Ilosc']), key=f"sq_{idx}", label_visibility="collapsed")
        is_st = True if str(row['Czy_Stale']).upper() == 'TAK' else False
        n_st = c3.checkbox("📌", value=is_st, key=f"ss_{idx}")
        nm = c4.number_input("M", float(row['Min_Ilosc']), key=f"sm_{idx}", label_visibility="collapsed") if n_st else 0.0
        
        # Aktualizacja tylko w sesji
        st.session_state.spizarnia_df.at[idx, 'Ilosc'] = nq
        st.session_state.spizarnia_df.at[idx, 'Czy_Stale'] = "TAK" if n_st else "NIE"
        st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = nm
        
        if c5.button("🗑️", key=f"sdel_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
            st.rerun()

elif st.session_state.page == "Dodaj":
    st.subheader("📖 Przepisy")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ Nowa potrawa"):
        np = st.text_input("Nazwa potrawy")
        if st.button("Utwórz"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0}])], ignore_index=True)
            st.rerun()

    if not st.session_state.przepisy.empty:
        potrawy = sorted([p for p in st.session_state.przepisy['Nazwa'].astype(str).unique().tolist() if p.strip()])
        if potrawy:
            wyb = st.selectbox("Wybierz do edycji:", potrawy)
            mask = st.session_state.przepisy['Nazwa'] == wyb
            items = st.session_state.przepisy[mask].copy()
            
            temp_rows = []
            for idx, row in items.iterrows():
                c1, c2, c3 = st.columns([3, 1, 0.5])
                ns = c1.text_input("S", row['Skladnik'], key=f"rn_{idx}")
                ni = c2.number_input("Q", float(row['Ilosc']), key=f"ri_{idx}")
                temp_rows.append({"idx": idx, "S": ns, "I": ni})
                if c3.button("🗑️", key=f"rdel_{idx}"):
                    st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                    st.rerun()
            
            c_a, c_s = st.columns(2)
            if c_a.button("➕ Dodaj składnik"):
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0}])], ignore_index=True)
                st.rerun()
            if c_s.button("💾 ZAPISZ PRZEPIS", type="primary"):
                for r in temp_rows:
                    st.session_state.przepisy.at[r['idx'], 'Skladnik'] = r['S']
                    st.session_state.przepisy.at[r['idx'], 'Ilosc'] = r['I']
                save_now(st.session_state.przepisy, "Przepisy")

elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Lista Zakupów")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    st.info("Mechanizm listy zakupów jest gotowy do wdrożenia.")
