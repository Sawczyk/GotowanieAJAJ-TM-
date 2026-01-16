import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Planer Kuchni", layout="wide")

# Tylko niezbędny styl dla zielonego przycisku zapisu
st.markdown("""
    <style>
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
        width: 100%;
    }
    .stButton button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. POŁĄCZENIE I FUNKCJE ---
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
        conn.update(worksheet=ws, data=df.dropna(how='all'))
        st.cache_data.clear()
        st.toast(f"Zapisano: {ws}")
        time.sleep(0.5)
        return True
    except Exception as e:
        st.error(f"Błąd: {e}")
        return False

def wyciagnij_liczbe(tekst):
    if pd.isna(tekst) or tekst == "": return 0.0
    try: return float(str(tekst).replace(',', '.'))
    except: return 0.0

# --- 3. INICJALIZACJA ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

if 'przepisy' not in st.session_state: st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = get_data("Spizarnia")
if 'plan_df' not in st.session_state: st.session_state.plan_df = get_data("Plan")

# --- 4. LOGIKA ZAKUPÓW ---
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
                    nazwa = str(row.get('Skladnik', '')).lower().strip()
                    if nazwa: potrzeby[nazwa] = potrzeby.get(nazwa, 0) + wyciagnij_liczbe(row.get('Ilosc', 0))

    wynik = {}
    magazyn = {str(r['Produkt']).lower().strip(): r for _, r in st.session_state.spizarnia_df.iterrows() if not pd.isna(r['Produkt'])}
    
    wszystkie_nazwy = set(list(potrzeby.keys()) + list(magazyn.keys()))
    for n in wszystkie_nazwy:
        m_row = magazyn.get(n, {})
        mam = wyciagnij_liczbe(m_row.get('Ilosc', 0))
        minimum = wyciagnij_liczbe(m_row.get('Min_Ilosc', 0)) if str(m_row.get('Czy_Stale', '')).upper() == 'TAK' else 0
        wymagane = max(potrzeby.get(n, 0), minimum)
        if wymagane > mam:
            wynik[n] = {"brak": wymagane - mam, "mam": mam, "potr": wymagane}
    return wynik

# --- 5. NAWIGACJA ---
st.title("🍳 Planer Kuchenny")
if st.session_state.page != "Home":
    if st.button("⬅ Powrót do Menu"):
        st.session_state.page = "Home"
        st.rerun()

# --- 6. STRONY ---
if st.session_state.page == "Home":
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📅 PLAN", use_container_width=True): st.session_state.page = "Plan"; st.rerun()
    if c2.button("🏠 SPIŻARNIA", use_container_width=True): st.session_state.page = "Spizarnia"; st.rerun()
    if c3.button("📖 PRZEPISY", use_container_width=True): st.session_state.page = "Dodaj"; st.rerun()
    if c4.button("🛒 ZAKUPY", use_container_width=True): st.session_state.page = "Zakupy"; st.rerun()

elif st.session_state.page == "Plan":
    st.subheader("Planowanie tygodnia")
    cp, ci, cn = st.columns([1, 2, 1])
    if cp.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    if cn.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()
    
    today = datetime.now()
    start = today - timedelta(days=today.weekday()) + timedelta(weeks=st.session_state.week_offset)
    t_id = start.strftime("%Y-%V")
    
    dni = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    for i, dzien in enumerate(dni):
        with st.expander(f"{dzien} ({(start + timedelta(days=i)).strftime('%d.%m')})"):
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{dzien}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if k in st.session_state.plan_df['Klucz'].values else "Brak"
                opcje = ["Brak"] + sorted(st.session_state.przepisy['Nazwa'].unique().tolist())
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                if wyb != istn:
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([st.session_state.plan_df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)
                    save_data(st.session_state.plan_df, "Plan"); st.rerun()

elif st.session_state.page == "Spizarnia":
    st.subheader("Twoja Spiżarnia")
    with st.form("dodaj_s"):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        n = c1.text_input("Nazwa")
        q = c2.number_input("Ilość", min_value=0.0)
        s = c3.checkbox("Stały?")
        m = c4.number_input("Min", min_value=0.0)
        if st.form_submit_button("Dodaj produkt"):
            st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}])], ignore_index=True)
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 0.5])
        c1.text(row['Produkt'])
        nq = c2.number_input("Q", value=float(row['Ilosc']), key=f"q_{idx}", label_visibility="collapsed")
        st_val = True if str(row['Czy_Stale']).upper() == 'TAK' else False
        n_st = c3.checkbox("Stały", value=st_val, key=f"s_{idx}")
        nm = c4.number_input("Min", value=float(row['Min_Ilosc']), key=f"m_{idx}", label_visibility="collapsed") if n_st else 0.0
        if not n_st: c4.write("---")
        
        if nq != float(row['Ilosc']) or n_st != st_val or (n_st and nm != float(row['Min_Ilosc'])):
            st.session_state.spizarnia_df.at[idx, 'Ilosc'] = nq
            st.session_state.spizarnia_df.at[idx, 'Czy_Stale'] = "TAK" if n_st else "NIE"
            st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = nm
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()
        if c5.button("🗑️", key=f"del_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

elif st.session_state.page == "Dodaj":
    st.subheader("Baza Przepisów")
    with st.expander("Nowa potrawa"):
        np = st.text_input("Nazwa potrawy")
        if st.button("Stwórz"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0}])], ignore_index=True)
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

    if not st.session_state.przepisy.empty:
        wyb = st.selectbox("Wybierz do edycji:", sorted(st.session_state.przepisy['Nazwa'].unique().tolist()))
        mask = st.session_state.przepisy['Nazwa'] == wyb
        items = st.session_state.przepisy[mask].copy()
        
        upd = []
        for idx, row in items.iterrows():
            c1, c2, c3 = st.columns([3, 1, 0.5])
            ns = c1.text_input("Składnik", row['Skladnik'], key=f"sn_{idx}", label_visibility="collapsed")
            ni = c2.number_input("Ilość", float(row['Ilosc']), key=f"si_{idx}", label_visibility="collapsed")
            upd.append({"idx": idx, "s": ns, "i": ni})
            if c3.button("🗑️", key=f"dr_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

        if st.button("➕ Dodaj wiersz"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0}])], ignore_index=True)
            st.rerun()

        if st.button("💾 ZAPISZ PRZEPIS", type="primary"):
            for r in upd:
                st.session_state.przepisy.at[r['idx'], 'Skladnik'] = r['s']
                st.session_state.przepisy.at[r['idx'], 'Ilosc'] = r['i']
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

elif st.session_state.page == "Zakupy":
    st.subheader("Lista zakupów")
    braki = analizuj_zapasy()
    if braki:
        for p, d in braki.items():
            st.warning(f"🔸 **{p.capitalize()}**: kup **{d['brak']}** (masz: {d['mam']}, potrzebne: {d['potr']})")
    else:
        st.success("Masz wszystko! 🎉")
