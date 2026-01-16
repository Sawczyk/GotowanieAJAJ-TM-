import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 1. KONFIGURACJA I STYLE ---
st.set_page_config(page_title="Planer Kuchni", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
    /* Nowoczesna czcionka i tło */
    html, body, [data-testid="stAppViewContainer"] {
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Nagłówek dnia tygodnia */
    .date-header {
        background: #262730;
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #28a745;
        margin-bottom: 2rem;
        text-align: center;
    }

    /* Styl kafelków menu */
    .stButton > button {
        border-radius: 12px;
        height: 100px;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s ease;
    }

    /* Zielony przycisk zapisu (Primary) */
    div.stButton > button[kind="primary"] {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
        height: 50px !important;
    }
    
    /* Sekcje edycji */
    .edit-container {
        background-color: #1a1c24;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #3e404b;
    }
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
        st.toast(f"✅ Zapisano pomyślnie!")
        time.sleep(0.5)
        return True
    except Exception as e:
        st.error(f"❌ Błąd zapisu: {e}")
        return False

def wyciagnij_liczbe(t):
    if pd.isna(t) or t == "": return 0.0
    try: return float(str(t).replace(',', '.'))
    except: return 0.0

# --- 3. INICJALIZACJA STANU ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

if 'przepisy' not in st.session_state: st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = get_data("Spizarnia")
if 'plan_df' not in st.session_state: st.session_state.plan_df = get_data("Plan")

# --- 4. LOGIKA BIZNESOWA ---
dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

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
    
    # Dodaj produkty z planu, których nie ma w ogóle w spiżarni
    for n, potr in potrzeby.items():
        if n not in wynik and n not in [str(x).lower().strip() for x in st.session_state.spizarnia_df['Produkt']]:
            wynik[n] = {"brak": potr, "mam": 0, "potr": potr}
            
    return wynik

# --- 5. INTERFEJS UŻYTKOWNIKA ---

# Pasek boczny lub przycisk powrotu
if st.session_state.page != "Home":
    if st.button("⬅ POWRÓT DO MENU GŁÓWNEGO"):
        st.session_state.page = "Home"
        st.rerun()

# --- STRONA GŁÓWNA ---
if st.session_state.page == "Home":
    teraz = datetime.now()
    dzien_nazwa = dni_pl[teraz.weekday()]
    st.markdown(f"""
        <div class="date-header">
            <h1 style='margin:0; color:#28a745;'>{dzien_nazwa}</h1>
            <h3 style='margin:0; opacity:0.8;'>{teraz.strftime('%d.%m.%Y')}</h3>
        </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📅 PLAN TYGODNIA", use_container_width=True):
            st.session_state.page = "Plan"; st.rerun()
        if st.button("🏠 MOJA SPIŻARNIA", use_container_width=True):
            st.session_state.page = "Spizarnia"; st.rerun()
    with c2:
        if st.button("📖 BAZA PRZEPISÓW", use_container_width=True):
            st.session_state.page = "Dodaj"; st.rerun()
        if st.button("🛒 LISTA ZAKUPÓW", use_container_width=True):
            st.session_state.page = "Zakupy"; st.rerun()

# --- PLANOWANIE ---
elif st.session_state.page == "Plan":
    st.header("📅 Plan Posiłków")
    cp, ci, cn = st.columns([1, 2, 1])
    if cp.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    if cn.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()
    
    start = datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)
    st.info(f"Tydzień: {start.strftime('%d.%m')} - {(start + timedelta(days=6)).strftime('%d.%m')}")
    
    t_id = start.strftime("%Y-%V")
    for i, dzien in enumerate(dni_pl):
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

# --- SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    st.header("🏠 Spiżarnia")
    with st.expander("➕ DODAJ NOWY PRODUKT"):
        with st.form("fm_s"):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            n = c1.text_input("Nazwa produktu")
            q = c2.number_input("Ilość", min_value=0.0)
            s = c3.checkbox("Produkt stały?")
            m = c4.number_input("Minimum", min_value=0.0)
            if st.form_submit_button("Zapisz w spiżarni"):
                st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}])], ignore_index=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

    st.subheader("Aktualne stany")
    for idx, row in st.session_state.spizarnia_df.iterrows():
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 0.5])
            c1.markdown(f"**{row['Produkt']}**")
            nq = c2.number_input("Ilość", value=float(row['Ilosc']), key=f"q_{idx}", label_visibility="collapsed")
            st_val = True if str(row['Czy_Stale']).upper() == 'TAK' else False
            n_st = c3.checkbox("Stały", value=st_val, key=f"s_{idx}")
            nm = c4.number_input("Min", value=float(row['Min_Ilosc']), key=f"m_{idx}", label_visibility="collapsed") if n_st else 0.0
            
            if nq != float(row['Ilosc']) or n_st != st_val or (n_st and nm != float(row['Min_Ilosc'])):
                st.session_state.spizarnia_df.at[idx, 'Ilosc'] = nq
                st.session_state.spizarnia_df.at[idx, 'Czy_Stale'] = "TAK" if n_st else "NIE"
                st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = nm
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()
            if c5.button("🗑️", key=f"del_{idx}"):
                st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

# --- PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.header("📖 Baza Przepisów")
    with st.expander("➕ NOWA POTRAWA"):
        with st.form("fm_p"):
            np = st.text_input("Nazwa potrawy")
            if st.form_submit_button("Stwórz przepis"):
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0}])], ignore_index=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

    if not st.session_state.przepisy.empty:
        wyb = st.selectbox("Wybierz potrawę do edycji:", sorted(st.session_state.przepisy['Nazwa'].unique().tolist()))
        st.markdown("<div class='edit-container'>", unsafe_allow_html=True)
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

        col_a, col_b = st.columns(2)
        if col_a.button("➕ DODAJ WIERSZ SKŁADNIKA"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0}])], ignore_index=True)
            st.rerun()
        
        if col_b.button("💾 ZAPISZ CAŁY PRZEPIS", type="primary"):
            for r in upd:
                st.session_state.przepisy.at[r['idx'], 'Skladnik'] = r['s']
                st.session_state.przepisy.at[r['idx'], 'Ilosc'] = r['i']
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.header("🛒 Twoja Lista Zakupów")
    braki = analizuj_zapasy()
    if braki:
        st.write("Produkty do kupienia:")
        for p, d in braki.items():
            with st.container():
                st.warning(f"**{p.capitalize()}** — brak: **{d['brak']}** (masz: {d['mam']}, potrzebujesz: {d['potr']})")
    else:
        st.success("Wszystko masz! Nie musisz iść do sklepu. 🎉")
