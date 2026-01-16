import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 1. POWRÓT DO ULUBIONEGO UI Z POPRAWIONYM KLIKANIEM ---
st.set_page_config(page_title="Planer Kuchni PRO", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Sora', sans-serif; }
    
    /* Nagłówek dnia */
    .today-highlight { 
        background: linear-gradient(90deg, #1B5E20, #2E7D32); 
        padding: 20px; 
        border-radius: 15px; 
        text-align: center; 
        margin-bottom: 25px; 
        border: 1px solid #4CAF50; 
    }

    /* DUŻE PRZYCISKI KAFELKOWE */
    div.stButton > button {
        background-color: #1E1E1E !important;
        border: 1px solid #333333 !important;
        border-radius: 15px !important;
        height: 150px !important;  /* Wysokość kafelka */
        color: white !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        transition: all 0.2s ease;
    }

    div.stButton > button:hover {
        border-color: #2E7D32 !important;
        background-color: #262626 !important;
        transform: translateY(-2px);
    }

    /* Specjalny styl dla zielonego zapisu w przepisach */
    div.stButton > button[kind="primary"] {
        background-color: #2E7D32 !important;
        height: 50px !important;
        margin-top: 10px;
    }
    
    /* Sekcja edycji */
    .recipe-section { 
        background-color: #1E1E1E; 
        padding: 20px; 
        border-radius: 15px; 
        border: 1px solid #444; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNKCJE DANYCH ---
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
        st.toast(f"✅ Zapisano!")
        time.sleep(0.4)
        return True
    except: return False

def wyciagnij_liczbe(t):
    if pd.isna(t) or t == "": return 0.0
    try: return float(str(t).replace(',', '.'))
    except: return 0.0

# --- 3. INICJALIZACJA ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

st.session_state.przepisy = get_data("Przepisy")
st.session_state.spizarnia_df = get_data("Spizarnia")
st.session_state.plan_df = get_data("Plan")

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

# --- 4. ANALIZA ZAKUPÓW ---
def analizuj_zapasy():
    potrzeby = {}
    today = datetime.now()
    start = today - timedelta(days=today.weekday()) + timedelta(weeks=st.session_state.week_offset)
    t_id = start.strftime("%Y-%V")
    
    if not st.session_state.plan_df.empty:
        plan_tydzien = st.session_state.plan_df[st.session_state.plan_df['Klucz'].astype(str).str.contains(t_id)]
        for potrawa in plan_tydzien['Wybor']:
            if potrawa != "Brak":
                skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == potrawa]
                for _, row in skladniki.iterrows():
                    n = str(row.get('Skladnik', '')).lower().strip()
                    if n: potrzeby[n] = potrzeby.get(n, 0) + wyciagnij_liczbe(row.get('Ilosc', 0))

    magazyn_stan = {str(r['Produkt']).lower().strip(): wyciagnij_liczbe(r['Ilosc']) for _, r in st.session_state.spizarnia_df.iterrows() if not pd.isna(r['Produkt'])}
    magazyn_min = {str(r['Produkt']).lower().strip(): wyciagnij_liczbe(r.get('Min_Ilosc', 0)) for _, r in st.session_state.spizarnia_df.iterrows() if str(r.get('Czy_Stale', '')).upper() == 'TAK'}

    wszystkie = set(list(potrzeby.keys()) + list(magazyn_min.keys()))
    wynik = {}
    for n in wszystkie:
        wymagane = max(potrzeby.get(n, 0), magazyn_min.get(n, 0))
        obecne = magazyn_stan.get(n, 0)
        if wymagane > obecne:
            wynik[n] = {"brak": wymagane - obecne, "mam": obecne, "potr": wymagane}
    return wynik

# --- 5. STRONY ---

if st.session_state.page == "Home":
    st.markdown(f"<div class='today-highlight'><h1>{dni_pl[datetime.now().weekday()]}</h1></div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    # Ikona jest częścią etykiety przycisku, co sprawia że cały obszar jest klikalny
    if c1.button("📅\n\nPLAN", key="b1"): st.session_state.page = "Plan"; st.rerun()
    if c2.button("🏠\n\nSPIŻARNIA", key="b2"): st.session_state.page = "Spizarnia"; st.rerun()
    if c3.button("📖\n\nPRZEPISY", key="b3"): st.session_state.page = "Dodaj"; st.rerun()
    if c4.button("🛒\n\nZAKUPY", key="b4"): st.session_state.page = "Zakupy"; st.rerun()

elif st.session_state.page == "Plan":
    st.header("📅 Plan Posiłków")
    if st.button("⬅ POWRÓT", key="back"): st.session_state.page = "Home"; st.rerun()
    cp, ci, cn = st.columns([1, 2, 1])
    if cp.button("⬅", key="prev"): st.session_state.week_offset -= 1; st.rerun()
    if cn.button("➡", key="next"): st.session_state.week_offset += 1; st.rerun()
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
    st.header("🏠 Spiżarnia")
    if st.button("⬅ POWRÓT", key="back"): st.session_state.page = "Home"; st.rerun()
    with st.form("add_s"):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        n, q, s, m = c1.text_input("Produkt"), c2.number_input("Ilość", 0.0), c3.checkbox("Stały?"), c4.number_input("Min", 0.0)
        if st.form_submit_button("Dodaj produkt"):
            st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}])], ignore_index=True)
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()
    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        nq = c2.number_input("I", float(row['Ilosc']), key=f"q_{idx}", label_visibility="collapsed")
        is_st = True if str(row['Czy_Stale']).upper() == 'TAK' else False
        n_st = c3.checkbox("📌", value=is_st, key=f"s_{idx}")
        nm = c4.number_input("M", float(row['Min_Ilosc']), key=f"m_{idx}", label_visibility="collapsed") if n_st else 0.0
        if not n_st: c4.write("---")
        if nq != float(row['Ilosc']) or n_st != is_st or (n_st and nm != float(row['Min_Ilosc'])):
            st.session_state.spizarnia_df.at[idx, 'Ilosc'], st.session_state.spizarnia_df.at[idx, 'Czy_Stale'], st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = nq, ("TAK" if n_st else "NIE"), nm
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()
        if c5.button("🗑️", key=f"del_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

elif st.session_state.page == "Dodaj":
    st.header("📖 Przepisy")
    if st.button("⬅ POWRÓT", key="back"): st.session_state.page = "Home"; st.rerun()
    with st.expander("➕ Nowa potrawa"):
        np = st.text_input("Nazwa")
        if st.button("Stwórz przepis", key="create"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0}])], ignore_index=True)
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
    if not st.session_state.przepisy.empty:
        wyb = st.selectbox("Edytuj:", sorted(st.session_state.przepisy['Nazwa'].unique().tolist()))
        st.markdown("<div class='recipe-section'>", unsafe_allow_html=True)
        items = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wyb].copy()
        upd = []
        for idx, row in items.iterrows():
            c1, c2, c3 = st.columns([3, 1, 0.5])
            ns, ni = c1.text_input("S", row['Skladnik'], key=f"sn_{idx}", label_visibility="collapsed"), c2.number_input("Q", float(row['Ilosc']), key=f"si_{idx}", label_visibility="collapsed")
            upd.append({"idx": idx, "s": ns, "i": ni})
            if c3.button("🗑️", key=f"dr_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
        ca, cb = st.columns(2)
        if ca.button("➕ Dodaj wiersz", key="add_row"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0}])], ignore_index=True)
            st.rerun()
        if cb.button("💾 ZAPISZ PRZEPIS", type="primary", key="save_recipe"):
            for r in upd: st.session_state.przepisy.at[r['idx'], 'Skladnik'], st.session_state.przepisy.at[r['idx'], 'Ilosc'] = r['s'], r['i']
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.page == "Zakupy":
    st.header("🛒 Zakupy")
    if st.button("⬅ POWRÓT", key="back"): st.session_state.page = "Home"; st.rerun()
    braki = analizuj_zapasy()
    if braki:
        for p, d in braki.items(): st.warning(f"🔸 **{p.capitalize()}**: kup **{d['brak']}** (masz: {d['mam']}, potrzebne: {d['potr']})")
    else: st.success("Wszystko masz! 🎉")
