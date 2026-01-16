import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re
import time

# --- 1. KONFIGURACJA UI ---
st.set_page_config(page_title="Planer Kuchni PRO", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Sora', sans-serif; }
    .menu-box { background-color: #1E1E1E; border: 1px solid #333333; padding: 20px; border-radius: 15px; text-align: center; }
    .today-highlight { background: linear-gradient(90deg, #1B5E20, #2E7D32); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; border: 1px solid #4CAF50; }
    .recipe-section { background-color: #1E1E1E; padding: 20px; border-radius: 15px; border: 1px solid #444; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE I FUNKCJE POMOCNICZE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def wyciagnij_liczbe(tekst):
    if pd.isna(tekst) or tekst == "": return 0.0
    try:
        return float(str(tekst).replace(',', '.'))
    except:
        return 0.0

def get_data(ws):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        return df.dropna(how='all').reset_index(drop=True)
    except:
        return pd.DataFrame()

def save_data(df, ws):
    try:
        df_to_save = df.dropna(how='all')
        conn.update(worksheet=ws, data=df_to_save)
        st.cache_data.clear()
        st.toast(f"💾 Zapisano w {ws}")
        time.sleep(0.4)
        return True
    except Exception as e:
        st.error(f"⚠️ Błąd zapisu: {e}")
        return False

# --- 3. INICJALIZACJA I ANALIZA ZAPASÓW ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

# Ładowanie danych
st.session_state.przepisy = get_data("Przepisy")
st.session_state.spizarnia_df = get_data("Spizarnia")
st.session_state.plan_df = get_data("Plan")
st.session_state.stale_df = get_data("Stale")

def get_week_dates(offset):
    today = datetime.now()
    start = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [(start + timedelta(days=i)) for i in range(7)]

def analizuj_zapasy():
    potrzeby = {}
    
    # 1. Z planu posiłków
    dates = get_week_dates(st.session_state.week_offset)
    t_id = dates[0].strftime("%Y-%V")
    if not st.session_state.plan_df.empty:
        plan_tydzien = st.session_state.plan_df[st.session_state.plan_df['Klucz'].astype(str).str.contains(t_id)]
        for wybrana_potrawa in plan_tydzien['Wybor']:
            if wybrana_potrawa != "Brak":
                skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wybrana_potrawa]
                for _, row in skladniki.iterrows():
                    nazwa = str(row.get('Skladnik', '')).lower().strip()
                    if nazwa:
                        potrzeby[nazwa] = potrzeby.get(nazwa, 0) + wyciagnij_liczbe(row.get('Ilosc', 0))

    # 2. Ze stałych produktów (Minimum)
    if not st.session_state.stale_df.empty:
        for _, row in st.session_state.stale_df.iterrows():
            nazwa = str(row.get('Produkt', '')).lower().strip()
            if nazwa:
                mini = wyciagnij_liczbe(row.get('Minimum', 0))
                potrzeby[nazwa] = max(potrzeby.get(nazwa, 0), mini)

    # 3. Porównanie ze spiżarnią
    magazyn = {str(r['Produkt']).lower(): wyciagnij_liczbe(r['Ilosc']) 
               for _, r in st.session_state.spizarnia_df.iterrows() if not pd.isna(r['Produkt'])}
    
    wynik = {}
    for n, p in potrzeby.items():
        wynik[n] = {"potr": p, "mam": magazyn.get(n, 0), "brak": max(0, p - magazyn.get(n, 0))}
    return wynik

# --- 4. LOGIKA STRON ---
dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"<div class='today-highlight'><h1>{dni_pl[teraz.weekday()]}</h1><p>{teraz.strftime('%d.%m.%Y')}</p></div>", unsafe_allow_html=True)
    
    c1, c2, c3, c4, c5 = st.columns(5)
    p_config = [("PLAN", "Plan", "📅"), ("SPIŻARNIA", "Spizarnia", "🏠"), ("PRZEPISY", "Dodaj", "📖"), ("ZAKUPY", "Zakupy", "🛒"), ("STAŁE", "Stale", "📌")]
    
    for i, (label, pg, icon) in enumerate(p_config):
        with [c1, c2, c3, c4, c5][i]:
            st.markdown(f"<div class='menu-box'><h1>{icon}</h1></div>", unsafe_allow_html=True)
            if st.button(label, key=f"btn_{pg}", use_container_width=True): 
                st.session_state.page = pg; st.rerun()

elif st.session_state.page == "Plan":
    st.header("📅 Planowanie Tygodnia")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    cp, ci, cn = st.columns([1, 2, 1])
    if cp.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    dates = get_week_dates(st.session_state.week_offset)
    ci.markdown(f"<h3 style='text-align:center;'>{dates[0].strftime('%d.%m')} - {dates[-1].strftime('%d.%m')}</h3>", unsafe_allow_html=True)
    if cn.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()

    t_id = dates[0].strftime("%Y-%V")
    for i, d_obj in enumerate(dates):
        with st.expander(f"{dni_pl[i]} ({d_obj.strftime('%d.%m')})"):
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{dni_pl[i]}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if not st.session_state.plan_df.empty and k in st.session_state.plan_df['Klucz'].values else "Brak"
                opcje = ["Brak"] + sorted(st.session_state.przepisy['Nazwa'].unique().tolist()) if not st.session_state.przepisy.empty else ["Brak"]
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                if wyb != istn:
                    df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)
                    save_data(st.session_state.plan_df, "Plan"); st.rerun()

elif st.session_state.page == "Spizarnia":
    st.header("🏠 Twoja Spiżarnia")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    with st.form("add_s"):
        c1, c2, c3 = st.columns([3, 1, 1])
        np = c1.text_input("Produkt")
        ni = c2.number_input("Ilość", min_value=0.0, step=0.1)
        if c3.form_submit_button("➕ DODAJ"):
            if np:
                st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": np, "Ilosc": ni}])], ignore_index=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3 = st.columns([3, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        val = c2.number_input("Ilość", value=float(row['Ilosc']), key=f"sq_{idx}", label_visibility="collapsed")
        if val != float(row['Ilosc']):
            st.session_state.spizarnia_df.at[idx, 'Ilosc'] = val
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()
        if c3.button("🗑️", key=f"sd_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

elif st.session_state.page == "Dodaj":
    st.header("📖 Baza Przepisów")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ Utwórz nową potrawę"):
        with st.form("nr"):
            n_potr = st.text_input("Nazwa potrawy")
            if st.form_submit_button("STWÓRZ"):
                if n_potr:
                    new = pd.DataFrame([{"Nazwa": n_potr, "Skladnik": "Składnik 1", "Ilosc": 0}])
                    st.session_state.przepisy = pd.concat([st.session_state.przepisy, new], ignore_index=True)
                    save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

    if not st.session_state.przepisy.empty:
        wyb = st.selectbox("Wybierz potrawę do edycji:", sorted(st.session_state.przepisy['Nazwa'].unique().tolist()))
        st.markdown("<div class='recipe-section'>", unsafe_allow_html=True)
        skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wyb]
        for idx, row in skladniki.iterrows():
            c1, c2, c3, c4 = st.columns([3, 1, 0.5, 0.5])
            ns = c1.text_input("Składnik", row['Skladnik'], key=f"sn_{idx}", label_visibility="collapsed")
            ni = c2.number_input("Ilość", float(row['Ilosc']), key=f"si_{idx}", label_visibility="collapsed")
            if c3.button("💾", key=f"sv_{idx}"):
                st.session_state.przepisy.at[idx, 'Skladnik'] = ns
                st.session_state.przepisy.at[idx, 'Ilosc'] = ni
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
            if c4.button("🗑️", key=f"rd_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
        if st.button("➕ Dodaj kolejny składnik"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0}])], ignore_index=True)
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.page == "Stale":
    st.header("📌 Stałe Produkty (Minimum)")
    st.info("Produkty tutaj wpisane będą zawsze pilnowane. Jeśli w spiżarni będzie ich mniej niż 'Min', trafią na listę zakupów.")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    with st.form("add_st"):
        c1, c2, c3 = st.columns([3, 1, 1])
        pn = c1.text_input("Produkt")
        pm = c2.number_input("Min. ilość", min_value=0.0)
        if c3.form_submit_button("➕"):
            if pn:
                st.session_state.stale_df = pd.concat([st.session_state.stale_df, pd.DataFrame([{"Produkt": pn, "Minimum": pm}])], ignore_index=True)
                save_data(st.session_state.stale_df, "Stale"); st.rerun()
    for idx, row in st.session_state.stale_df.iterrows():
        c1, c2, c3 = st.columns([3, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        ed_m = c2.number_input("Min", value=float(row['Minimum']), key=f"stm_{idx}", label_visibility="collapsed")
        if ed_m != float(row['Minimum']):
            st.session_state.stale_df.at[idx, 'Minimum'] = ed_m
            save_data(st.session_state.stale_df, "Stale"); st.rerun()
        if c3.button("🗑️", key=f"std_{idx}"):
            st.session_state.stale_df = st.session_state.stale_df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.stale_df, "Stale"); st.rerun()

elif st.session_state.page == "Zakupy":
    st.header("🛒 Lista Zakupów")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    analiza = analizuj_zapasy()
    braki = {k: v for k, v in analiza.items() if v['brak'] > 0}
    if braki:
        st.write("Musisz kupić poniższe produkty, aby zrealizować plan i utrzymać stan stały:")
        for p, d in braki.items():
            st.warning(f"🔸 **{p.capitalize()}**: potrzebujesz jeszcze **{d['brak']}** (masz: {d['mam']}, wymagane: {d['potr']})")
    else:
        st.success("Wszystko masz! Twoja spiżarnia i plan są zgodne. 🎉")
