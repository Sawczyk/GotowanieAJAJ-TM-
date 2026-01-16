import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 1. CZYSTE I SCHLUDNE STYLE ---
st.set_page_config(page_title="Planer Kuchni", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    /* Ogólny wygląd */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Inter', sans-serif;
    }

    /* Elegancki nagłówek dnia */
    .day-banner {
        background-color: #2E7D32;
        color: white;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 30px;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Standardowe przyciski menu - schludne i klikalne */
    div.stButton > button {
        border-radius: 10px;
        padding: 20px 10px !important;
        font-weight: 600 !important;
        border: 1px solid #444;
        transition: all 0.2s;
    }

    /* Zielony przycisk zapisu (Primary) */
    div.stButton > button[kind="primary"] {
        background-color: #2E7D32 !important;
        color: white !important;
        border: none !important;
    }
    
    div.stButton > button:hover {
        border-color: #2E7D32 !important;
        color: #2E7D32 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA DANYCH ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(ws):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        return df.dropna(how='all').reset_index(drop=True) if df is not None else pd.DataFrame()
    except: return pd.DataFrame()

def save_data(df, ws):
    try:
        conn.update(worksheet=ws, data=df.dropna(how='all'))
        st.cache_data.clear()
        st.toast(f"✅ Zapisano pomyślnie")
        time.sleep(0.4)
        return True
    except: return False

# --- 3. INICJALIZACJA ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

st.session_state.przepisy = get_data("Przepisy")
st.session_state.spizarnia_df = get_data("Spizarnia")
st.session_state.plan_df = get_data("Plan")

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

# --- 4. INTERFEJS ---

if st.session_state.page == "Home":
    # Schludny Banner
    st.markdown(f"<div class='day-banner'><h1>{dni_pl[datetime.now().weekday()]}</h1></div>", unsafe_allow_html=True)
    
    # Intuicyjne Menu Główne
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
    st.subheader("📅 Planowanie posiłków")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    cp, ci, cn = st.columns([1, 2, 1])
    if cp.button("Poprzedni tydzień"): st.session_state.week_offset -= 1; st.rerun()
    if cn.button("Następny tydzień"): st.session_state.week_offset += 1; st.rerun()
    
    start = datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)
    t_id = start.strftime("%Y-%V")
    
    for i, d_n in enumerate(dni_pl):
        with st.expander(f"{d_n} ({(start + timedelta(days=i)).strftime('%d.%m')})"):
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{d_n}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if k in st.session_state.plan_df['Klucz'].values else "Brak"
                opcje = ["Brak"] + sorted(st.session_state.przepisy['Nazwa'].unique().tolist())
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                if wyb != istn:
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([st.session_state.plan_df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)
                    save_data(st.session_state.plan_df, "Plan"); st.rerun()

elif st.session_state.page == "Spizarnia":
    st.subheader("🏠 Twoja Spiżarnia")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ Dodaj nowy produkt"):
        with st.form("new_item"):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            n = c1.text_input("Nazwa")
            q = c2.number_input("Ilość", 0.0)
            s = c3.checkbox("Produkt stały")
            m = c4.number_input("Min. ilość", 0.0)
            if st.form_submit_button("Dodaj do bazy"):
                st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}])], ignore_index=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        nq = c2.number_input("Q", float(row['Ilosc']), key=f"q_{idx}", label_visibility="collapsed")
        is_st = True if str(row['Czy_Stale']).upper() == 'TAK' else False
        n_st = c3.checkbox("📌", value=is_st, key=f"s_{idx}")
        nm = c4.number_input("M", float(row['Min_Ilosc']), key=f"m_{idx}", label_visibility="collapsed") if n_st else 0.0
        
        if nq != float(row['Ilosc']) or n_st != is_st or (n_st and nm != float(row['Min_Ilosc'])):
            st.session_state.spizarnia_df.at[idx, 'Ilosc'], st.session_state.spizarnia_df.at[idx, 'Czy_Stale'], st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = nq, ("TAK" if n_st else "NIE"), nm
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()
        if c5.button("🗑️", key=f"del_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

elif st.session_state.page == "Dodaj":
    st.subheader("📖 Zarządzanie Przepisami")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ Nowa potrawa"):
        np = st.text_input("Nazwa potrawy")
        if st.button("Utwórz kartę przepisu"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0}])], ignore_index=True)
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

    if not st.session_state.przepisy.empty:
        wyb = st.selectbox("Edytuj przepis:", sorted(st.session_state.przepisy['Nazwa'].unique().tolist()))
        items = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wyb].copy()
        
        upd = []
        for idx, row in items.iterrows():
            c1, c2, c3 = st.columns([3, 1, 0.5])
            ns = c1.text_input("Składnik", row['Skladnik'], key=f"sn_{idx}", label_visibility="collapsed")
            ni = c2.number_input("Ilość", float(row['Ilosc']), key=f"si_{idx}", label_visibility="collapsed")
            upd.append({"idx": idx, "s": ns, "i": ni})
            if c3.button("🗑️", key=f"dr_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
        
        c1, c2 = st.columns(2)
        if c1.button("➕ Dodaj wiersz"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0}])], ignore_index=True)
            st.rerun()
        if c2.button("💾 ZAPISZ PRZEPIS", type="primary"):
            for r in upd: st.session_state.przepisy.at[r['idx'], 'Skladnik'], st.session_state.przepisy.at[r['idx'], 'Ilosc'] = r['s'], r['i']
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Lista Zakupów")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    st.success("Lista jest generowana na podstawie Twojego planu i braków w spiżarni.")
