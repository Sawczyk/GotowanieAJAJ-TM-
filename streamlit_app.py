import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re

# --- 1. KONFIGURACJA I TOTALNA BLOKADA KOLORÓW ---
st.set_page_config(
    page_title="Planer Kuchni Pro", 
    page_icon="🍳", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Ten CSS wymusza jasny wygląd niezależnie od ustawień systemowych
st.markdown("""
    <style>
    /* 1. Globalne tło i kolory tekstu */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }

    /* 2. NAPRAWA PÓL WYBORU I TEKSTOWYCH (Input, Selectbox, Textarea) */
    /* Wymuszamy białe tło i czarny tekst wewnątrz pól */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] > div,
    input, textarea, .stSelectbox, .stTextInput, .stTextArea {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #cccccc !important;
    }
    
    /* Naprawa kolorów rozwijanej listy (dropdown) */
    div[data-baseweb="popover"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* 3. Naprawa nagłówków i etykiet */
    label, p, h1, h2, h3, span {
        color: #000000 !important;
        font-weight: 500 !important;
    }

    /* 4. Menu Główne - Karty */
    .menu-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        font-size: 30px;
        border: 1px solid #ddd;
    }

    /* 5. Przyciski - jasne i czytelne */
    .stButton>button {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #000000 !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        height: 3em !important;
    }
    
    .stButton>button:hover {
        background-color: #000000 !important;
        color: #ffffff !important;
    }

    /* 6. Naprawa Expanderów */
    div[data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #eee !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SILNIK DANYCH ---
conn = st.connection("gsheets", type=GSheetsConnection)

def wyciagnij_liczbe(tekst):
    if pd.isna(tekst): return 0
    match = re.search(r"(\d+[\.,]?\d*)", str(tekst))
    if match:
        return float(match.group(1).replace(',', '.'))
    return 0

def get_data(ws):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def save_data(df, ws):
    df = df.dropna(how='all')
    conn.update(worksheet=ws, data=df)
    st.cache_data.clear()

# --- 3. LOGIKA SESJI I TYGODNI ---
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia_df' not in st.session_state:
    st.session_state.spizarnia_df = get_data("Spizarnia")
if 'plan_df' not in st.session_state:
    st.session_state.plan_df = get_data("Plan")
if 'page' not in st.session_state:
    st.session_state.page = "Home"
if 'week_offset' not in st.session_state:
    st.session_state.week_offset = 0

def get_week_dates(offset):
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [(start_of_week + timedelta(days=i)) for i in range(7)]

def analizuj_zapasy_tygodniowe():
    potrzeby_suma = {}
    dni = get_week_dates(st.session_state.week_offset)
    tydzien_id = dni[0].strftime("%Y-%V")
    if st.session_state.plan_df.empty: return {}
    
    plan_tydzien = st.session_state.plan_df[st.session_state.plan_df['Klucz'].astype(str).str.contains(tydzien_id)]
    
    for wybor in plan_tydzien['Wybor']:
        if wybor != "Brak":
            przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wybor]
            if not przepis.empty:
                skladniki = [s.strip() for s in str(przepis.iloc[0]['Skladniki']).split(',')]
                for s in skladniki:
                    nazwa = s.split('(')[0].strip().lower()
                    ilosc = wyciagnij_liczbe(s)
                    potrzeby_suma[nazwa] = potrzeby_suma.get(nazwa, 0) + ilosc
    
    magazyn = {}
    if not st.session_state.spizarnia_df.empty:
        for _, row in st.session_state.spizarnia_df.iterrows():
            magazyn[str(row['Produkt']).lower()] = wyciagnij_liczbe(row['Ilosc'])
            
    bilans = {}
    for nazwa, potr in potrzeby_suma.items():
        mam = magazyn.get(nazwa, 0)
        bilans[nazwa] = {"potrzeba": potr, "mam": mam, "brakuje": max(0, potr - mam)}
    return bilans

# --- 4. EKRAN GŁÓWNY ---
if st.session_state.page == "Home":
    st.markdown("<h1 style='text-align: center;'>🥘 Mój Planer Kuchni</h1>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("<div class='menu-card'>📅</div>", unsafe_allow_html=True)
        if st.button("PLANOWANIE", use_container_width=True): st.session_state.page = "Plan"; st.rerun()
    with c2:
        st.markdown("<div class='menu-card'>🏠</div>", unsafe_allow_html=True)
        if st.button("SPIŻARNIA", use_container_width=True): st.session_state.page = "Spizarnia"; st.rerun()
    with c3:
        st.markdown("<div class='menu-card'>📖</div>", unsafe_allow_html=True)
        if st.button("PRZEPISY", use_container_width=True): st.session_state.page = "Dodaj"; st.rerun()
    with c4:
        st.markdown("<div class='menu-card'>🛒</div>", unsafe_allow_html=True)
        if st.button("ZAKUPY", use_container_width=True): st.session_state.page = "Zakupy"; st.rerun()

# --- 5. PLANOWANIE ---
elif st.session_state.page == "Plan":
    st.markdown("<h2>📅 Mój Plan Tygodniowy</h2>", unsafe_allow_html=True)
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    cp, cc, cn = st.columns([1, 2, 1])
    if cp.button("⬅ Poprzedni Tydzień"): st.session_state.week_offset -= 1; st.rerun()
    if cn.button("Następny Tydzień ➡"): st.session_state.week_offset += 1; st.rerun()
    
    dni = get_week_dates(st.session_state.week_offset)
    tydzien_id = dni[0].strftime("%Y-%V")
    st.info(f"Podgląd tygodnia: {dni[0].strftime('%d.%m')} - {dni[-1].strftime('%d.%m')}")

    with st.expander("📊 CZY MASZ WSZYSTKIE SKŁADNIKI?", expanded=True):
        bilans = analizuj_zapasy_tygodniowe()
        if bilans:
            for p, d in bilans.items():
                if d['brakuje'] > 0:
                    st.markdown(f"<p style='color: #d32f2f;'>🔴 <b>{p.capitalize()}</b>: brakuje {d['brakuje']} (potrzeba {d['potrzeba']}, masz {d['mam']})</p>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<p style='color: #2e7d32;'>🟢 <b>{p.capitalize()}</b>: masz wystarczająco ({d['mam']})</p>", unsafe_allow_html=True)
        else: st.write("Wybierz posiłki w planie poniżej.")

    dni_nazwy = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    for i, d_obj in enumerate(dni):
        with st.expander(f"🗓️ {dni_nazwy[i]} ({d_obj.strftime('%d.%m')})"):
            for p_typ in ["Śniadanie", "Lunch", "Kolacja"]:
                klucz = f"{tydzien_id}_{dni_nazwy[i]}_{p_typ}"
                istn = "Brak"
                if not st.session_state.plan_df.empty and 'Klucz' in st.session_state.plan_df.columns:
                    match = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == klucz]
                    if not match.empty: istn = match.iloc[0]['Wybor']
                
                opcje = ["Brak"] + st.session_state.przepisy['Nazwa'].tolist() if not st.session_state.przepisy.empty else ["Brak"]
                wybor = st.selectbox(f"{p_typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=klucz)
                
                if wybor != istn:
                    df_p = st.session_state.plan_df
                    if df_p.empty or 'Klucz' not in df_p.columns: df_p = pd.DataFrame(columns=['Klucz', 'Wybor'])
                    df_p = df_p[df_p['Klucz'] != klucz]
                    df_p = pd.concat([df_p, pd.DataFrame([{"Klucz": klucz, "Wybor": wybor}])], ignore_index=True)
                    st.session_state.plan_df = df_p
                    save_data(df_p, "Plan")
                    st.rerun()

# --- 6. SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    st.markdown("<h2>🏠 Stan Magazynowy</h2>", unsafe_allow_html=True)
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.write("Wpisuj produkty i liczby (aplikacja sumuje je w planowaniu):")
    
    df_s = st.session_state.spizarnia_df
    if df_s.empty: df_s = pd.DataFrame(columns=['Produkt', 'Ilosc'])
    edytowany = st.data_editor(df_s, num_rows="dynamic", use_container_width=True)
    
    if st.button("💾 ZAPISZ ZMIANY W SPIŻARNI"):
        st.session_state.spizarnia_df = edytowany
        save_data(edytowany, "Spizarnia")
        st.success("Spiżarnia zaktualizowana!")

# --- 7. PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.markdown("<h2>📖 Twoja Baza Przepisów</h2>", unsafe_allow_html=True)
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    with st.form("f_recipe_pro"):
        n = st.text_input("Nazwa potrawy")
        t = st.selectbox("Posiłek", ["Śniadanie", "Lunch", "Kolacja"])
        s = st.text_area("Składniki i ilości w nawiasach, np: Jajka (3), Mleko (0.5), Ryż (100)")
        if st.form_submit_button("DODAJ DO BAZY"):
            if n and s:
                nowy = pd.DataFrame([{"Nazwa": n, "Typ": t, "Skladniki": s}])
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, nowy], ignore_index=True)
                save_data(st.session_state.przepisy, "Przepisy")
                st.success(f"Dodano przepis: {n}")
                st.rerun()

# --- 8. ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.markdown("<h2>🛒 Twoja Lista Zakupów</h2>", unsafe_allow_html=True)
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    bilans = analizuj_zapasy_tygodniowe()
    braki = {k: v for k, v in bilans.items() if v['brakuje'] > 0}
    
    if braki:
        st.write("Produkty, których brakuje do zrealizowania Twojego planu:")
        txt_out = []
        for prod, dane in braki.items():
            st.markdown(f"⬜ **{prod.capitalize()}** – dokup: **{dane['brakuje']}**")
            txt_out.append(f"{prod}: {dane['brakuje']}")
        
        st.download_button("Pobierz listę .txt", "\n".join(txt_out), "zakupy.txt")
    else:
        st.success("Masz wszystkie potrzebne produkty w spiżarni! 🎉")
