import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re

# --- 1. KONFIGURACJA I TOTALNA STYLIZACJA UI ---
st.set_page_config(
    page_title="Planer Kuchni Pro", 
    page_icon="🍳", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Bardziej restrykcyjny CSS, aby wymusić widoczność tekstu
st.markdown("""
    <style>
    /* Wymuszenie kolorów bazowych */
    :root {
        --primary-color: #2E7D32;
    }
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #ffffff !important;
        color: #1a1a1a !important;
    }

    /* Wszystkie teksty, nagłówki i labele na czarno */
    h1, h2, h3, p, span, label, .stMarkdown, [data-testid="stText"] {
        color: #1a1a1a !important;
    }

    /* Naprawa białych tekstów w widgetach */
    .stSelectbox label, .stTextInput label, .stTextArea label {
        color: #1a1a1a !important;
        font-weight: 600 !important;
    }
    
    /* Karty Menu Głównego */
    .menu-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-size: 2.5rem;
        border: 1px solid #e9ecef;
        margin-bottom: 0.5rem;
    }

    /* Stylizacja przycisków */
    .stButton>button {
        border-radius: 8px !important;
        background-color: #ffffff !important;
        color: #1a1a1a !important;
        border: 1px solid #d1d1d1 !important;
        font-weight: 600 !important;
        width: 100%;
    }
    
    .stButton>button:hover {
        border-color: #2E7D32 !important;
        color: #2E7D32 !important;
        background-color: #f1f8e9 !important;
    }

    /* Styl kart planowania */
    div[data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 10px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE I FUNKCJE (bez zmian) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def wyciagnij_liczbe(tekst):
    if pd.isna(tekst): return 0
    match = re.search(r"(\d+[\.,]?\d*)", str(tekst))
    if match:
        return float(match.group(1).replace(',', '.'))
    return 0

def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df.dropna(how='all')
    except: return pd.DataFrame()

# --- 3. INICJALIZACJA SESJI ---
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
    plan_tydzien = st.session_state.plan_df[st.session_state.plan_df['Klucz'].str.contains(tydzien_id)]
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

# --- 4. NAWIGACJA HOME ---
if st.session_state.page == "Home":
    st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>🍳 Mój Planer Kuchni</h1>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("<div class='menu-card'>📅</div>", unsafe_allow_html=True)
        if st.button("PLANOWANIE"): st.session_state.page = "Plan"; st.rerun()
    with c2:
        st.markdown("<div class='menu-card'>🏠</div>", unsafe_allow_html=True)
        if st.button("SPIŻARNIA"): st.session_state.page = "Spizarnia"; st.rerun()
    with c3:
        st.markdown("<div class='menu-card'>📖</div>", unsafe_allow_html=True)
        if st.button("PRZEPISY"): st.session_state.page = "Dodaj"; st.rerun()
    with c4:
        st.markdown("<div class='menu-card'>🛒</div>", unsafe_allow_html=True)
        if st.button("ZAKUPY"): st.session_state.page = "Zakupy"; st.rerun()

# --- 5. MODUŁ: PLANOWANIE ---
elif st.session_state.page == "Plan":
    st.markdown("<h2 style='text-align: center;'>📅 Plan Tygodniowy</h2>", unsafe_allow_html=True)
    if st.button("⬅ POWRÓT DO MENU"): st.session_state.page = "Home"; st.rerun()
    
    cp, cc, cn = st.columns([1, 2, 1])
    if cp.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    if cn.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()
    
    dni = get_week_dates(st.session_state.week_offset)
    tydzien_id = dni[0].strftime("%Y-%V")
    
    st.info(f"Tydzień {tydzien_id} ({dni[0].strftime('%d.%m')} - {dni[-1].strftime('%d.%m')})")

    with st.expander("📊 ANALIZA SKŁADNIKÓW (CZY MI STARCZY?)", expanded=True):
        bilans = analizuj_zapasy_tygodniowe()
        if bilans:
            for p, d in bilans.items():
                if d['brakuje'] > 0:
                    st.markdown(f"<span style='color: #d32f2f;'>❌ **{p.capitalize()}**: Potrzebujesz {d['potrzeba']}, masz {d['mam']}. **Brak: {d['brakuje']}**</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='color: #2e7d32;'>✅ **{p.capitalize()}**: Masz wystarczająco ({d['mam']}/{d['potrzeba']})</span>", unsafe_allow_html=True)
        else: st.write("Wybierz posiłki poniżej.")

    dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    for i, d_obj in enumerate(dni):
        with st.expander(f"📍 {dni_pl[i]} ({d_obj.strftime('%d.%m')})"):
            for p_typ in ["Śniadanie", "Lunch", "Kolacja"]:
                klucz = f"{tydzien_id}_{dni_pl[i]}_{p_typ}"
                istn = "Brak"
                if not st.session_state.plan_df.empty and 'Klucz' in st.session_state.plan_df.columns:
                    m = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == klucz]
                    if not m.empty: istn = m.iloc[0]['Wybor']
                
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

# --- 6. MODUŁ: SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    st.markdown("<h2>🏠 Stan Magazynowy</h2>", unsafe_allow_html=True)
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.write("Wpisz produkty i ich liczbowe ilości:")
    df_s = st.session_state.spizarnia_df
    if df_s.empty: df_s = pd.DataFrame(columns=['Produkt', 'Ilosc'])
    edytowany = st.data_editor(df_s, num_rows="dynamic", use_container_width=True)
    if st.button("💾 ZAPISZ ZMIANY"):
        st.session_state.spizarnia_df = edytowany
        save_data(edytowany, "Spizarnia")
        st.success("Zapisano stan spiżarni!")

# --- 7. MODUŁ: PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.markdown("<h2>📖 Baza Przepisów</h2>", unsafe_allow_html=True)
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    with st.form("f_recipe"):
        n = st.text_input("Nazwa potrawy")
        t = st.selectbox("Typ", ["Śniadanie", "Lunch", "Kolacja"])
        s = st.text_area("Składniki, np: Jajka (3), Mleko (0.5), Bułka (1)")
        if st.form_submit_button("DODAJ PRZEPIS"):
            if n and s:
                nowy = pd.DataFrame([{"Nazwa": n, "Typ": t, "Skladniki": s}])
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, nowy], ignore_index=True)
                save_data(st.session_state.przepisy, "Przepisy")
                st.rerun()

# --- 8. MODUŁ: ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.markdown("<h2>🛒 Lista Zakupów</h2>", unsafe_allow_html=True)
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    bilans = analizuj_zapasy_tygodniowe()
    braki = {k: v for k, v in bilans.items() if v['brakuje'] > 0}
    if braki:
        st.write("Do kupienia na ten tydzień:")
        txt_list = []
        for p, d in braki.items():
            st.checkbox(f"🔴 {p.capitalize()}: {d['brakuje']} szt/jedn", key=f"shop_{p}")
            txt_list.append(f"{p}: {d['brakuje']}")
        st.download_button("Pobierz listę .txt", "\n".join(txt_list), "lista_zakupow.txt")
    else:
        st.success("Masz wszystko na zaplanowany tydzień! 🎉")
