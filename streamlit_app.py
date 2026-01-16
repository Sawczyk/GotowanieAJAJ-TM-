import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 1. KONFIGURACJA UI ---
st.set_page_config(page_title="Planer Kuchni PRO", page_icon="🍳", layout="wide")

# CSS dla zielonego przycisku i estetyki
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Sora', sans-serif; }
    
    /* Menu Główne */
    .menu-box { background-color: #1E1E1E; border: 1px solid #333333; padding: 25px; border-radius: 15px; text-align: center; }
    .today-highlight { background: linear-gradient(90deg, #1B5E20, #2E7D32); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; border: 1px solid #4CAF50; }
    
    /* Sekcja Przepisów */
    .recipe-section { background-color: #1E1E1E; padding: 20px; border-radius: 15px; border: 1px solid #444; margin-top: 10px; }
    
    /* ZIELONY PRZYCISK PRIMARY */
    div.stButton > button[kind="primary"] {
        background-color: #2E7D32 !important;
        color: white !important;
        border-color: #4CAF50 !important;
        font-weight: bold !important;
        width: 100%;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #388E3C !important;
        border-color: #81C784 !important;
    }
    
    .stButton button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE I FUNKCJE DANYCH ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(ws):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        if df is None or df.empty:
            if ws == "Spizarnia": return pd.DataFrame(columns=["Produkt", "Ilosc", "Czy_Stale", "Min_Ilosc"])
            if ws == "Przepisy": return pd.DataFrame(columns=["Nazwa", "Skladnik", "Ilosc"])
            if ws == "Plan": return pd.DataFrame(columns=["Klucz", "Wybor"])
        return df.dropna(how='all').reset_index(drop=True)
    except:
        return pd.DataFrame()

def save_data(df, ws):
    try:
        df_to_save = df.dropna(how='all')
        conn.update(worksheet=ws, data=df_to_save)
        st.cache_data.clear()
        st.toast(f"✅ Zapisano zmiany w: {ws}")
        time.sleep(0.5)
        return True
    except Exception as e:
        st.error(f"⚠️ Błąd zapisu: {e}")
        return False

def wyciagnij_liczbe(tekst):
    if pd.isna(tekst) or tekst == "": return 0.0
    try:
        return float(str(tekst).replace(',', '.'))
    except:
        return 0.0

# --- 3. INICJALIZACJA ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

if 'przepisy' not in st.session_state: st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = get_data("Spizarnia")
if 'plan_df' not in st.session_state: st.session_state.plan_df = get_data("Plan")

# --- 4. LOGIKA ANALIZY ZAKUPÓW ---
def get_week_dates(offset):
    today = datetime.now()
    start = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [(start + timedelta(days=i)) for i in range(7)]

def analizuj_zapasy():
    potrzeby = {}
    dates = get_week_dates(st.session_state.week_offset)
    t_id = dates[0].strftime("%Y-%V")
    
    if not st.session_state.plan_df.empty:
        plan_tydzien = st.session_state.plan_df[st.session_state.plan_df['Klucz'].astype(str).str.contains(t_id)]
        for potrawa in plan_tydzien['Wybor']:
            if potrawa != "Brak":
                skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == potrawa]
                for _, row in skladniki.iterrows():
                    nazwa = str(row.get('Skladnik', '')).lower().strip()
                    if nazwa:
                        potrzeby[nazwa] = potrzeby.get(nazwa, 0) + wyciagnij_liczbe(row.get('Ilosc', 0))

    magazyn_stan = {str(r['Produkt']).lower().strip(): wyciagnij_liczbe(r['Ilosc']) for _, r in st.session_state.spizarnia_df.iterrows() if not pd.isna(r['Produkt'])}
    magazyn_minimum = {str(r['Produkt']).lower().strip(): wyciagnij_liczbe(r.get('Min_Ilosc', 0)) for _, r in st.session_state.spizarnia_df.iterrows() if str(r.get('Czy_Stale', '')).upper() == 'TAK'}

    wszystkie = set(list(potrzeby.keys()) + list(magazyn_minimum.keys()))
    wynik = {}
    for n in wszystkie:
        wymagane = max(potrzeby.get(n, 0), magazyn_minimum.get(n, 0))
        obecne = magazyn_stan.get(n, 0)
        wynik[n] = {"potr": wymagane, "mam": obecne, "brak": max(0, wymagane - obecne)}
    return wynik

# --- 5. STRONY ---
dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

if st.session_state.page == "Home":
    st.markdown(f"<div class='today-highlight'><h1>{dni_pl[datetime.now().weekday()]}</h1></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    pages = [("PLAN", "Plan", "📅"), ("SPIŻARNIA", "Spizarnia", "🏠"), ("PRZEPISY", "Dodaj", "📖"), ("ZAKUPY", "Zakupy", "🛒")]
    for i, (label, pg, icon) in enumerate(pages):
        with [c1, c2, c3, c4][i]:
            st.markdown(f"<div class='menu-box'><h1>{icon}</h1></div>", unsafe_allow_html=True)
            if st.button(label, key=f"btn_{pg}"): 
                st.session_state.page = pg; st.rerun()

elif st.session_state.page == "Plan":
    st.header("📅 Planowanie")
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
    st.header("🏠 Spiżarnia")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    with st.form("add_spiz", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        new_n = c1.text_input("Nazwa produktu")
        new_i = c2.number_input("Ilość", min_value=0.0)
        is_stale = c3.checkbox("Stały?")
        min_i = c4.number_input("Min", min_value=0.0)
        if st.form_submit_button("➕ DODAJ"):
            if new_n:
                row = {"Produkt": new_n, "Ilosc": new_i, "Czy_Stale": "TAK" if is_stale else "NIE", "Min_Ilosc": min_i if is_stale else 0}
                st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([row])], ignore_index=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        curr_i = c2.number_input("Q", value=float(row['Ilosc']), key=f"sq_{idx}", label_visibility="collapsed")
        st_val = True if str(row.get('Czy_Stale', '')).upper() == 'TAK' else False
        new_st = c3.checkbox("📌", value=st_val, key=f"st_ch_{idx}")
        min_v = c4.number_input("M", value=wyciagnij_liczbe(row.get('Min_Ilosc', 0)), key=f"st_m_{idx}", label_visibility="collapsed") if new_st else 0.0
        if not new_st: c4.write("---")
        
        if curr_i != float(row['Ilosc']) or new_st != st_val or (new_st and min_v != wyciagnij_liczbe(row.get('Min_Ilosc', 0))):
            st.session_state.spizarnia_df.at[idx, 'Ilosc'] = curr_i
            st.session_state.spizarnia_df.at[idx, 'Czy_Stale'] = "TAK" if new_st else "NIE"
            st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = min_v
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()
        if c5.button("🗑️", key=f"del_s_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

elif st.session_state.page == "Dodaj":
    st.header("📖 Przepisy")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ Nowa potrawa"):
        with st.form("nr", clear_on_submit=True):
            np = st.text_input("Nazwa potrawy")
            if st.form_submit_button("STWÓRZ"):
                if np:
                    st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Nowy składnik", "Ilosc": 0}])], ignore_index=True)
                    save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

    if not st.session_state.przepisy.empty:
        wyb = st.selectbox("Edytuj potrawę:", sorted(st.session_state.przepisy['Nazwa'].unique().tolist()))
        
        st.markdown("<div class='recipe-section'>", unsafe_allow_html=True)
        mask = st.session_state.przepisy['Nazwa'] == wyb
        items = st.session_state.przepisy[mask].copy()
        
        updated_rows = []
        to_delete = None
        
        for idx, row in items.iterrows():
            c1, c2, c3 = st.columns([3, 1, 0.5])
            new_s = c1.text_input("Składnik", row['Skladnik'], key=f"sn_{idx}", label_visibility="collapsed")
            new_i = c2.number_input("Ilość", float(row['Ilosc']), key=f"si_{idx}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"del_r_{idx}"):
                to_delete = idx
            updated_rows.append({"Nazwa": wyb, "Skladnik": new_s, "Ilosc": new_i, "old_idx": idx})

        # Przycisk dodawania wiersza (standardowy)
        if st.button("➕ DODAJ WIERSZ SKŁADNIKA", key="add_row"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0}])], ignore_index=True)
            st.rerun()

        st.markdown("---")
        # ZIELONY PRZYCISK ZAPISU (typ primary)
        if st.button("💾 ZAPISZ CAŁY PRZEPIS", type="primary", key="save_recipe"):
            for row in updated_rows:
                st.session_state.przepisy.at[row['old_idx'], 'Skladnik'] = row['Skladnik']
                st.session_state.przepisy.at[row['old_idx'], 'Ilosc'] = row['Ilosc']
            save_data(st.session_state.przepisy, "Przepisy")
            st.rerun()

        if to_delete is not None:
            st.session_state.przepisy = st.session_state.przepisy.drop(to_delete).reset_index(drop=True)
            save_data(st.session_state.przepisy, "Przepisy")
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Przycisk usuwania na samym dole, czerwony przez motyw (nie-primary)
        if st.button("❌ Usuń całą potrawę", key="del_entire"):
            st.session_state.przepisy = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] != wyb].reset_index(drop=True)
            save_data(st.session_state.przepisy, "Przepisy")
            st.rerun()

elif st.session_state.page == "Zakupy":
    st.header("🛒 Zakupy")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    analiza = analizuj_zapasy()
    braki = {k: v for k, v in analiza.items() if v['brak'] > 0}
    if braki:
        for p, d in braki.items():
            st.warning(f"🔸 **{p.capitalize()}**: kup **{d['brak']}** (masz: {d['mam']}, potrzebne: {d['potr']})")
    else:
        st.success("Wszystko masz! 🎉")
