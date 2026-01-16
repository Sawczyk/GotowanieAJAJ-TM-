import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 1. TWOJE ULUBIONE STYLE ---
st.set_page_config(page_title="Planer Kuchni PRO", page_icon="🍳", layout="wide")

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
        margin-bottom: 25px;
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
    .missing-tag { color: #d32f2f; font-weight: 600; font-size: 0.85rem; margin-top: -5px; display: block; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA POŁĄCZENIA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_load(ws, cols):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        if df is None or df.empty: 
            return pd.DataFrame(columns=cols)
        
        df.columns = [str(c).strip() for c in df.columns]
        
        for c in cols:
            if c not in df.columns:
                df[c] = 0 if c == "Kalorie" else ""
        
        if 'Kalorie' in df.columns:
            df['Kalorie'] = pd.to_numeric(df['Kalorie'], errors='coerce').fillna(0).astype(int)
        
        return df[cols].dropna(how='all').reset_index(drop=True)
    except:
        return pd.DataFrame(columns=cols)

def save_now(df, ws_name):
    try:
        conn.update(worksheet=ws_name, data=df.dropna(how='all'))
        st.cache_data.clear()
        st.toast(f"✅ Zapisano pomyślnie: {ws_name}")
    except: 
        st.error("Błąd zapisu!")

def to_num(val):
    try: return float(str(val).replace(',', '.'))
    except: return 0.0

# --- 3. INICJALIZACJA DANYCH I FIX SESJI ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

# Naprawa struktury w razie starych danych w przeglądarce
if 'przepisy' in st.session_state:
    if "Kalorie" not in st.session_state.przepisy.columns:
        del st.session_state.przepisy

if 'przepisy' not in st.session_state: 
    st.session_state.przepisy = safe_load("Przepisy", ["Nazwa", "Skladnik", "Ilosc", "Kalorie"])
if 'spizarnia_df' not in st.session_state: 
    st.session_state.spizarnia_df = safe_load("Spizarnia", ["Produkt", "Ilosc", "Czy_Stale", "Min_Ilosc"])
if 'plan_df' not in st.session_state: 
    st.session_state.plan_df = safe_load("Plan", ["Klucz", "Wybor"])

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
miesiace_pl = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]

# --- 4. ANALIZA BRAKÓW ---
def sprawdz_braki_dla_potrawy(nazwa_potrawy):
    if nazwa_potrawy == "Brak" or nazwa_potrawy == "": return None
    skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == nazwa_potrawy]
    braki = []
    for _, r in skladniki.iterrows():
        s_name = str(r['Skladnik']).lower().strip()
        if s_name in ["składnik", "", "nan"]: continue
        potrzeba = to_num(r['Ilosc'])
        mam = to_num(st.session_state.spizarnia_df[st.session_state.spizarnia_df['Produkt'].str.lower() == s_name]['Ilosc'].sum())
        if mam < potrzeba:
            braki.append(s_name)
    return braki

# --- 5. RENDEROWANIE STRON ---

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
    st.subheader("📅 Planowanie Posiłków")
    c_back, c_save = st.columns(2)
    if c_back.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    if c_save.button("💾 ZAPISZ CAŁY PLAN", type="primary"): save_now(st.session_state.plan_df, "Plan")
    st.divider()
    
    c_p, c_c, c_n = st.columns([1, 2, 1])
    if c_p.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    if c_n.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()
    
    start = datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)
    t_id = start.strftime("%Y-%V")
    
    for i, d_n in enumerate(dni_pl):
        with st.expander(f"{d_n} ({(start + timedelta(days=i)).strftime('%d.%m')})"):
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{d_n}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if k in st.session_state.plan_df['Klucz'].values else "Brak"
                opcje = ["Brak"] + sorted([p for p in st.session_state.przepisy['Nazwa'].unique().tolist() if str(p).strip()])
                
                p_data = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == istn]
                kcal = int(p_data['Kalorie'].iloc[0]) if not p_data.empty and istn != "Brak" else 0
                
                wyb = st.selectbox(f"{typ} ({kcal} kcal):", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                
                braki = sprawdz_braki_dla_potrawy(wyb)
                if braki:
                    st.markdown(f"<span class='missing-tag'>⚠️ Brak: {', '.join(braki)}</span>", unsafe_allow_html=True)
                
                if wyb != istn:
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([st.session_state.plan_df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)

elif st.session_state.page == "Spizarnia":
    st.subheader("🏠 Spiżarnia")
    c_back, c_save = st.columns(2)
    if c_back.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    if c_save.button("💾 ZAPISZ STAN SPIŻARNI", type="primary"): save_now(st.session_state.spizarnia_df, "Spizarnia")
    st.divider()
    
    with st.expander("➕ Dodaj produkt"):
        with st.form("new_s", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            n, q, s, m = c1.text_input("Nazwa"), c2.number_input("Ilość", 0.0), c3.checkbox("Stały?"), c4.number_input("Min", 0.0)
            if st.form_submit_button("Dodaj"):
                st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}])], ignore_index=True)
                st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        st.session_state.spizarnia_df.at[idx, 'Ilosc'] = c2.number_input("Q", float(row['Ilosc']), key=f"sq_{idx}", label_visibility="collapsed")
        is_st = str(row['Czy_Stale']).upper() == 'TAK'
        n_st = c3.checkbox("📌", value=is_st, key=f"ss_{idx}")
        st.session_state.spizarnia_df.at[idx, 'Czy_Stale'] = "TAK" if n_st else "NIE"
        st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = c4.number_input("M", float(row['Min_Ilosc']), key=f"sm_{idx}", label_visibility="collapsed") if n_st else 0.0
        if c5.button("🗑️", key=f"sdel_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True); st.rerun()

elif st.session_state.page == "Dodaj":
    st.subheader("📖 Baza Przepisów")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    st.divider()
    
    with st.expander("➕ Dodaj potrawę (Ręcznie lub Zdjęcie)"):
        c1, c2 = st.columns(2)
        np = c1.text_input("Nazwa potrawy")
        foto = c2.file_uploader("Skanuj ze zdjęcia (OCR)", type=['jpg', 'png', 'jpeg'])
        if st.button("Utwórz nową kartę"):
            sug_kcal = 450 if "obiad" in np.lower() else 250
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0, "Kalorie": sug_kcal}])], ignore_index=True)
            st.rerun()

    if not st.session_state.przepisy.empty:
        wyb = st.selectbox("Edytuj przepis:", sorted(st.session_state.przepisy['Nazwa'].unique()))
        mask = st.session_state.przepisy['Nazwa'] == wyb
        cur_kcal = int(st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0])
        new_kcal = st.number_input("Kaloryczność porcji:", value=cur_kcal)
        st.session_state.przepisy.loc[mask, 'Kalorie'] = new_kcal
        
        st.write("Składniki:")
        df_edit = st.session_state.przepisy[mask]
        for idx, row in df_edit.iterrows():
            c1, c2, c3 = st.columns([3, 1, 0.5])
            st.session_state.przepisy.at[idx, 'Skladnik'] = c1.text_input("S", row['Skladnik'], key=f"rn_{idx}", label_visibility="collapsed")
            st.session_state.przepisy.at[idx, 'Ilosc'] = c2.number_input("Q", float(row['Ilosc']), key=f"ri_{idx}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"rdel_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True); st.rerun()
        
        ca, cs = st.columns(2)
        if ca.button("➕ Dodaj składnik"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0, "Kalorie": new_kcal}])], ignore_index=True); st.rerun()
        if cs.button("💾 ZAPISZ PRZEPIS", type="primary"): save_now(st.session_state.przepisy, "Przepisy")

elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Lista Zakupów")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    st.divider()
    
    teraz = datetime.now()
    start = teraz - timedelta(days=teraz.weekday()) + timedelta(weeks=st.session_state.week_offset)
    t_id = start.strftime("%Y-%V")
    
    potrzeby = {}
    plan_obecny = st.session_state.plan_df[st.session_state.plan_df['Klucz'].str.contains(t_id, na=False)]
    for potrawa in plan_obecny['Wybor']:
        if potrawa != "Brak":
            skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == potrawa]
            for _, r in skladniki.iterrows():
                s_name = str(r['Skladnik']).lower().strip()
                if s_name and s_name not in ["składnik", "nan"]:
                    potrzeby[s_name] = potrzeby.get(s_name, 0) + to_num(r['Ilosc'])

    braki = []
    for _, r in st.session_state.spizarnia_df.iterrows():
        p_name = str(r['Produkt']).lower().strip()
        mam = to_num(r['Ilosc'])
        min_wym = to_num(r['Min_Ilosc']) if str(r['Czy_Stale']).upper() == "TAK" else 0
        wymagane = max(potrzeby.get(p_name, 0), min_wym)
        if wymagane > mam:
            braki.append({"Produkt": p_name.capitalize(), "Kupić": wymagane - mam, "W spiżarni": mam})
        if p_name in potrzeby: del potrzeby[p_name]

    for s_name, ile in potrzeby.items():
        braki.append({"Produkt": s_name.capitalize(), "Kupić": ile, "W spiżarni": 0})

    if braki: st.table(pd.DataFrame(braki))
    else: st.success("Masz wszystko, czego potrzebujesz! 🎉")
