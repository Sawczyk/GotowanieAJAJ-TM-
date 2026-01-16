import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re

# --- 1. KONFIGURACJA UI ---
st.set_page_config(page_title="Planer Kuchni PRO", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Sora', sans-serif; }
    .menu-box { background-color: #1E1E1E; border: 1px solid #333333; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 10px; }
    .today-highlight { background: linear-gradient(90deg, #1B5E20, #2E7D32); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 30px; border: 1px solid #4CAF50; }
    .recipe-section { background-color: #1E1E1E; padding: 20px; border-radius: 15px; border: 1px solid #444; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE I FUNKCJE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def wyciagnij_liczbe(tekst):
    if pd.isna(tekst) or tekst == "": return 0
    try: return float(str(tekst).replace(',', '.'))
    except: return 0

def get_data(ws):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        return df.dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame()

def save_data(df, ws):
    conn.update(worksheet=ws, data=df)
    st.cache_data.clear()

# --- 3. INICJALIZACJA STANU ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0
if 'przepisy' not in st.session_state: st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = get_data("Spizarnia")
if 'plan_df' not in st.session_state: st.session_state.plan_df = get_data("Plan")

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
            # Szukamy wszystkich wierszy składników dla danej potrawy
            skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == w]
            for _, row in skladniki.iterrows():
                nazwa = str(row['Skladnik']).lower().strip()
                potrzeby[nazwa] = potrzeby.get(nazwa, 0) + wyciagnij_liczbe(row['Ilosc'])
    
    mag = {str(r['Produkt']).lower(): wyciagnij_liczbe(r['Ilosc']) for _, r in st.session_state.spizarnia_df.iterrows() if not pd.isna(r['Produkt'])}
    return {n: {"potr": p, "mam": mag.get(n, 0), "brak": max(0, p - mag.get(n, 0))} for n, p in potrzeby.items()}

# --- 4. LOGIKA STRON ---
if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"<div class='today-highlight'><h1 style='margin:0; color:white;'>{dni_pl[teraz.weekday()]}</h1><p style='margin:0; color:white;'>{teraz.strftime('%d.%m.%Y')}</p></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    pages = [("PLANOWANIE", "Plan", "📅"), ("SPIŻARNIA", "Spizarnia", "🏠"), ("PRZEPISY", "Dodaj", "📖"), ("ZAKUPY", "Zakupy", "🛒")]
    for i, (label, pg, icon) in enumerate(pages):
        with [c1, c2, c3, c4][i]:
            st.markdown(f"<div class='menu-box'>{icon}</div>", unsafe_allow_html=True)
            if st.button(label, key=f"btn_{pg}", use_container_width=True): 
                st.session_state.page = pg
                st.rerun()

elif st.session_state.page == "Plan":
    st.header("📅 Planowanie")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    # ... (Reszta kodu Planowania pozostaje bez zmian, bo używa 'Nazwa' potrawy)
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    if col_prev.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    dates = get_week_dates(st.session_state.week_offset)
    col_info.markdown(f"<h3 style='text-align:center;'>{dates[0].strftime('%d.%m')} - {dates[-1].strftime('%d.%m')}</h3>", unsafe_allow_html=True)
    if col_next.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()
    
    with st.expander("📊 ANALIZA SKŁADNIKÓW", expanded=True):
        b = analizuj_zapasy()
        for p, d in b.items():
            st.write(f"**{p.capitalize()}**: {d['mam']}/{d['potr']} " + (f"🔴 Brakuje: {d['brak']}" if d['brak'] > 0 else "🟢 OK"))

    t_id = dates[0].strftime("%Y-%V")
    for i, d_obj in enumerate(dates):
        with st.expander(f"{dni_pl[i]} ({d_obj.strftime('%d.%m')})"):
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{dni_pl[i]}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if not st.session_state.plan_df.empty and k in st.session_state.plan_df['Klucz'].values else "Brak"
                # Unikalne nazwy potraw do wyboru
                opcje = ["Brak"] + sorted(st.session_state.przepisy['Nazwa'].unique().tolist()) if not st.session_state.przepisy.empty else ["Brak"]
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                if wyb != istn:
                    df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)
                    save_data(st.session_state.plan_df, "Plan"); st.rerun()

elif st.session_state.page == "Spizarnia":
    st.header("🏠 Spiżarnia")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    with st.form("add_stock"):
        c1, c2, c3 = st.columns([3, 1, 1])
        new_p = c1.text_input("Produkt")
        new_i = c2.number_input("Ilość", min_value=0.0, step=0.1)
        if c3.form_submit_button("➕ DODAJ"):
            if new_p:
                st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": new_p, "Ilosc": new_i}])], ignore_index=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

    st.markdown("---")
    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4 = st.columns([0.5, 3, 1.5, 0.5])
        c1.write(f"{idx+1}.")
        c2.write(f"**{row['Produkt']}**")
        edited_qty = c3.number_input("Ilość", value=float(row['Ilosc']), step=0.1, key=f"q_{idx}", label_visibility="collapsed")
        if edited_qty != float(row['Ilosc']):
            st.session_state.spizarnia_df.at[idx, 'Ilosc'] = edited_qty
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()
        if c4.button("🗑️", key=f"del_s_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

elif st.session_state.page == "Dodaj":
    st.header("📖 Baza Przepisów")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    # 1. DODAWANIE NOWEJ POTRAWY
    with st.expander("➕ Dodaj nową potrawę", expanded=True):
        with st.form("new_recipe_form"):
            nazwa_p = st.text_input("Nazwa potrawy (np. Jajecznica)")
            st.info("Po dodaniu potrawy będziesz mógł dopisać do niej składniki poniżej.")
            if st.form_submit_button("UTWÓRZ POTRAWĘ"):
                if nazwa_p:
                    # Dodajemy pusty wiersz jako placeholder dla potrawy
                    new_row = pd.DataFrame([{"Nazwa": nazwa_p, "Skladnik": "Wpisz składnik", "Ilosc": 0}])
                    st.session_state.przepisy = pd.concat([st.session_state.przepisy, new_row], ignore_index=True)
                    save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

    # 2. EDYCJA SKŁADNIKÓW ISTNIEJĄCEJ POTRAWY
    st.markdown("---")
    if not st.session_state.przepisy.empty:
        potrawy = sorted(st.session_state.przepisy['Nazwa'].unique().tolist())
        wybrana = st.selectbox("Wybierz potrawę do edycji:", potrawy)
        
        st.markdown(f"<div class='recipe-section'>", unsafe_allow_html=True)
        st.subheader(f"Składniki dla: {wybrana}")
        
        # Filtrujemy składniki dla tej potrawy
        mask = st.session_state.przepisy['Nazwa'] == wybrana
        skladniki_potrawy = st.session_state.przepisy[mask]
        
        for idx, row in skladniki_potrawy.iterrows():
            c1, c2, c3, c4 = st.columns([3, 1, 0.5, 0.5])
            
            # Edycja nazwy składnika i ilości w oddzielnych polach
            n_sklad = c1.text_input("Składnik", value=row['Skladnik'], key=f"sn_{idx}", label_visibility="collapsed")
            i_sklad = c2.number_input("Ilość", value=float(row['Ilosc']), step=0.1, key=f"si_{idx}", label_visibility="collapsed")
            
            if c3.button("💾", key=f"sv_{idx}"):
                st.session_state.przepisy.at[idx, 'Skladnik'] = n_sklad
                st.session_state.przepisy.at[idx, 'Ilosc'] = i_sklad
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
                
            if c4.button("🗑️", key=f"dl_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
        
        if st.button("➕ DODAJ KOLEJNY SKŁADNIK"):
            new_line = pd.DataFrame([{"Nazwa": wybrana, "Skladnik": "", "Ilosc": 0}])
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, new_line], ignore_index=True)
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

elif st.session_state.page == "Zakupy":
    st.header("🛒 Zakupy")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    b = analizuj_zapasy()
    if b:
        for p, d in b.items():
            if d['brak'] > 0: st.warning(f"🔸 **{p.capitalize()}**: {d['brak']}")
    else: st.success("Wszystko masz! 🎉")
