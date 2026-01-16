import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re

# --- 1. KONFIGURACJA UI ---
st.set_page_config(
    page_title="Planer Kuchni PRO", 
    page_icon="🌙", 
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Sora', sans-serif;
    }
    .menu-box {
        background-color: #1E1E1E;
        border: 1px solid #333333;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 10px;
    }
    .today-highlight {
        background: linear-gradient(90deg, #1B5E20, #2E7D32);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 30px;
        border: 1px solid #4CAF50;
    }
    .nav-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #262626;
        padding: 10px 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE I FUNKCJE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def wyciagnij_liczbe(tekst):
    if pd.isna(tekst) or tekst == "": return 0
    match = re.search(r"(\d+[\.,]?\d*)", str(tekst))
    return float(match.group(1).replace(',', '.')) if match else 0

def get_data(ws):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def save_data(df, ws):
    if 'Lp.' in df.columns: # Usuwamy Lp przed zapisem do bazy, by nie dublować
        df = df.drop(columns=['Lp.'])
    df = df.dropna(how='all')
    conn.update(worksheet=ws, data=df)
    st.cache_data.clear()

# --- 3. INICJALIZACJA ---
if 'przepisy' not in st.session_state: st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = get_data("Spizarnia")
if 'plan_df' not in st.session_state: st.session_state.plan_df = get_data("Plan")
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

def get_week_dates(offset):
    today = datetime.now()
    start = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [(start + timedelta(days=i)) for i in range(7)]

def analizuj_zapasy():
    potrzeby = {}
    dates = get_week_dates(st.session_state.week_offset)
    t_id = dates[0].strftime("%Y-%V")
    if st.session_state.plan_df.empty: return {}
    
    plan = st.session_state.plan_df[st.session_state.plan_df['Klucz'].astype(str).str.contains(t_id)]
    for w in plan['Wybor']:
        if w != "Brak":
            p = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == w]
            if not p.empty:
                skladniki = str(p.iloc[0]['Skladniki']).split(',')
                for s in skladniki:
                    nazwa = s.split('(')[0].strip().lower()
                    potrzeby[nazwa] = potrzeby.get(nazwa, 0) + wyciagnij_liczbe(s)
    
    mag = {str(r['Produkt']).lower(): wyciagnij_liczbe(r['Ilosc']) for _, r in st.session_state.spizarnia_df.iterrows()} if not st.session_state.spizarnia_df.empty else {}
    return {n: {"potr": p, "mam": mag.get(n, 0), "brak": max(0, p - mag.get(n, 0))} for n, p in potrzeby.items()}

# --- 4. NAWIGACJA ---
if st.session_state.page == "Home":
    teraz = datetime.now()
    dzien_dzis = dni_pl[teraz.weekday()]
    st.markdown(f"""
        <div class='today-highlight'>
            <h1 style='margin:0; color:white; font-size: 2.5rem;'>{dzien_dzis}</h1>
            <p style='margin:0; color:white; opacity:0.9; font-size: 1.2rem;'>{teraz.strftime('%d.%m.%Y')}</p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("<div class='menu-box'>📅</div>", unsafe_allow_html=True)
        if st.button("PLANOWANIE", use_container_width=True): st.session_state.page = "Plan"; st.rerun()
    with c2:
        st.markdown("<div class='menu-box'>🏠</div>", unsafe_allow_html=True)
        if st.button("SPIŻARNIA", use_container_width=True): st.session_state.page = "Spizarnia"; st.rerun()
    with c3:
        st.markdown("<div class='menu-box'>📖</div>", unsafe_allow_html=True)
        if st.button("PRZEPISY", use_container_width=True): st.session_state.page = "Dodaj"; st.rerun()
    with c4:
        st.markdown("<div class='menu-box'>🛒</div>", unsafe_allow_html=True)
        if st.button("ZAKUPY", use_container_width=True): st.session_state.page = "Zakupy"; st.rerun()

elif st.session_state.page == "Plan":
    st.header("📅 Planowanie Tygodnia")
    if st.button("⬅ POWRÓT DO MENU"): st.session_state.page = "Home"; st.rerun()
    
    st.markdown("---")
    # Nowy pasek nawigacji tygodniem
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    if col_prev.button("⬅ Poprzedni Tydzień", use_container_width=True): st.session_state.week_offset -= 1; st.rerun()
    
    dates = get_week_dates(st.session_state.week_offset)
    t_id = dates[0].strftime("%Y-%V")
    col_info.markdown(f"<h3 style='text-align:center;'>{dates[0].strftime('%d.%m')} - {dates[-1].strftime('%d.%m')}</h3>", unsafe_allow_html=True)
    
    if col_next.button("Następny Tydzień ➡", use_container_width=True): st.session_state.week_offset += 1; st.rerun()
    st.markdown("---")
    
    with st.expander("📊 CZY STARCZY SKŁADNIKÓW?", expanded=True):
        b = analizuj_zapasy()
        if b:
            for p, d in b.items():
                col_a, col_b = st.columns([3,1])
                col_a.write(f"**{p.capitalize()}** (Potrzeba: {d['potr']}, Masz: {d['mam']})")
                if d['brak'] > 0: col_b.error(f"Brakuje: {d['brak']}")
                else: col_b.success("Mamy to!")
        else: st.info("Dodaj posiłki do planu.")

    for i, d_obj in enumerate(dates):
        with st.expander(f"{dni_pl[i]} ({d_obj.strftime('%d.%m')})"):
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{dni_pl[i]}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if not st.session_state.plan_df.empty and k in st.session_state.plan_df['Klucz'].values else "Brak"
                opcje = ["Brak"] + st.session_state.przepisy['Nazwa'].tolist() if not st.session_state.przepisy.empty else ["Brak"]
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                if wyb != istn:
                    df = st.session_state.plan_df
                    df = df[df['Klucz'] != k]
                    df = pd.concat([df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)
                    st.session_state.plan_df = df
                    save_data(df, "Plan"); st.rerun()

elif st.session_state.page == "Spizarnia":
    st.header("🏠 Twoja Spiżarnia")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    df_s = st.session_state.spizarnia_df.copy()
    if df_s.empty:
        df_s = pd.DataFrame(columns=['Produkt', 'Ilosc'])
    
    # Dodawanie automatycznej numeracji Lp.
    df_s.insert(0, 'Lp.', range(1, len(df_s) + 1))
    
    st.write("Wpisuj produkty i ich ilości (liczby):")
    eds = st.data_editor(df_s, num_rows="dynamic", use_container_width=True, hide_index=True)
    
    if st.button("💾 ZAPISZ STAN SPIŻARNI"):
        save_data(eds, "Spizarnia")
        st.session_state.spizarnia_df = eds.drop(columns=['Lp.']) if 'Lp.' in eds.columns else eds
        st.success("Zapisano!")
        st.rerun()

elif st.session_state.page == "Dodaj":
    st.header("📖 Baza Przepisów")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    with st.form("recipe_form"):
        n = st.text_input("Nazwa potrawy")
        t = st.selectbox("Typ posiłku", ["Śniadanie", "Obiad", "Kolacja"])
        s = st.text_area("Składniki (np. Jajka (3), Mleko (0.5))")
        if st.form_submit_button("DODAJ PRZEPIS"):
            if n and s:
                new_recipe = pd.DataFrame([{"Nazwa": n, "Typ": t, "Skladniki": s}])
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, new_recipe], ignore_index=True)
                save_data(st.session_state.przepisy, "Przepisy")
                st.success(f"Dodano: {n}")
                st.rerun()

elif st.session_state.page == "Zakupy":
    st.header("🛒 Lista Zakupów")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    b = analizuj_zapasy()
    braki = {k: v for k, v in b.items() if v['brak'] > 0}
    if braki:
        for p, d in braki.items():
            st.warning(f"🔸 **{p.capitalize()}**: dokup {d['brak']}")
    else:
        st.success("Spiżarnia pełna! 🎉")
