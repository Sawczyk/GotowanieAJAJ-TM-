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

    /* Elegancki nagłówek dnia z pełną datą */
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
    .day-banner p { margin: 5px 0 0 0; font-size: 1.1rem; opacity: 0.9; text-transform: capitalize; }

    /* Styl przycisków menu */
    div.stButton > button {
        border-radius: 10px;
        padding: 20px 10px !important;
        font-weight: 600 !important;
        border: 1px solid #444;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        border-color: #2E7D32 !important;
        color: #2E7D32 !important;
    }

    /* Zielony przycisk akcji (Primary) */
    div.stButton > button[kind="primary"] {
        background-color: #2E7D32 !important;
        color: white !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA POŁĄCZENIA Z GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(ws):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        return df.dropna(how='all').reset_index(drop=True) if df is not None else pd.DataFrame()
    except:
        return pd.DataFrame()

def save_data(df, ws):
    try:
        conn.update(worksheet=ws, data=df.dropna(how='all'))
        st.cache_data.clear()
        st.toast(f"✅ Zapisano pomyślnie")
        return True
    except Exception as e:
        st.error(f"Błąd zapisu: {e}")
        return False

def wyciagnij_liczbe(t):
    if pd.isna(t) or t == "": return 0.0
    try: return float(str(t).replace(',', '.'))
    except: return 0.0

# --- 3. INICJALIZACJA STANU SESJI ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

# Ładujemy dane do sesji, aby zapobiec ich resetowaniu podczas wpisywania tekstu
if 'przepisy' not in st.session_state: st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = get_data("Spizarnia")
if 'plan_df' not in st.session_state: st.session_state.plan_df = get_data("Plan")

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
miesiace_pl = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]

# --- 4. LOGIKA ANALIZY ZAKUPÓW ---
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

    wynik = {}
    for _, r in st.session_state.spizarnia_df.iterrows():
        n = str(r['Produkt']).lower().strip()
        if not n: continue
        mam = wyciagnij_liczbe(r.get('Ilosc', 0))
        mini = wyciagnij_liczbe(r.get('Min_Ilosc', 0)) if str(r.get('Czy_Stale', '')).upper() == 'TAK' else 0
        wymagane = max(potrzeby.get(n, 0), mini)
        if wymagane > mam:
            wynik[n] = {"brak": wymagane - mam, "mam": mam, "potr": wymagane}
    
    for n, potr in potrzeby.items():
        if n not in wynik and n not in [str(x).lower().strip() for x in st.session_state.spizarnia_df['Produkt']]:
            wynik[n] = {"brak": potr, "mam": 0, "potr": potr}
    return wynik

# --- 5. RENDEROWANIE STRON ---

# --- HOME ---
if st.session_state.page == "Home":
    teraz = datetime.now()
    dzien_tyg = dni_pl[teraz.weekday()]
    data_pelna = f"{teraz.day} {miesiace_pl[teraz.month-1]} {teraz.year}"
    
    st.markdown(f"""
        <div class='day-banner'>
            <h1>{dzien_tyg}</h1>
            <p>{data_pelna}</p>
        </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("📅\nPLAN", use_container_width=True): st.session_state.page = "Plan"; st.rerun()
    with c2:
        if st.button("🏠\nSPIŻARNIA", use_container_width=True): st.session_state.page = "Spizarnia"; st.rerun()
    with c3:
        if st.button("📖\nPRZEPISY", use_container_width=True): st.session_state.page = "Dodaj"; st.rerun()
    with c4:
        if st.button("🛒\nZAKUPY", use_container_width=True): st.session_state.page = "Zakupy"; st.rerun()

# --- PLANOWANIE ---
elif st.session_state.page == "Plan":
    st.subheader("📅 Planowanie Posiłków")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    cp, ci, cn = st.columns([1, 2, 1])
    if cp.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    if cn.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()
    
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

# --- SPIŻARNIA ---
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

# --- PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.subheader("📖 Zarządzanie Przepisami")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ Nowa potrawa"):
        np = st.text_input("Nazwa potrawy")
        if st.button("Utwórz kartę"):
            nowy = pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0}])
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, nowy], ignore_index=True)
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

    if not st.session_state.przepisy.empty:
        wyb = st.selectbox("Edytuj przepis:", sorted(st.session_state.przepisy['Nazwa'].unique().tolist()))
        mask = st.session_state.przepisy['Nazwa'] == wyb
        items_to_edit = st.session_state.przepisy[mask].copy()
        
        rows_data = []
        for idx, row in items_to_edit.iterrows():
            c1, c2, c3 = st.columns([3, 1, 0.5])
            ns = c1.text_input("Składnik", row['Skladnik'], key=f"sn_{idx}")
            ni = c2.number_input("Ilość", value=float(row['Ilosc']), key=f"si_{idx}")
            rows_data.append({"idx": idx, "Skladnik": ns, "Ilosc": ni})
            if c3.button("🗑️", key=f"dr_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
        
        ca, cb = st.columns(2)
        if ca.button("➕ Dodaj wiersz"):
            nowy_wiersz = pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0}])
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, nowy_wiersz], ignore_index=True)
            st.rerun()
        if cb.button("💾 ZAPISZ PRZEPIS", type="primary"):
            for r in rows_data:
                st.session_state.przepisy.at[r['idx'], 'Skladnik'] = r['Skladnik']
                st.session_state.przepisy.at[r['idx'], 'Ilosc'] = r['Ilosc']
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

# --- ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Lista Zakupów")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    braki = analizuj_zapasy()
    if braki:
        for p, d in braki.items():
            st.warning(f"🔸 **{p.capitalize()}**: kup **{d['brak']}** (masz: {d['mam']}, potrzebne: {d['potr']})")
    else:
        st.success("Wszystko masz! 🎉")
