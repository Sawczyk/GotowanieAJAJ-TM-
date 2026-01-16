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
    .day-banner p { margin: 5px 0 0 0; font-size: 1.1rem; opacity: 0.9; }

    div.stButton > button {
        border-radius: 10px;
        padding: 20px 10px !important;
        font-weight: 600 !important;
        border: 1px solid #444;
        transition: all 0.2s;
    }
    div.stButton > button[kind="primary"] {
        background-color: #2E7D32 !important;
        color: white !important;
        border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA POŁĄCZENIA I BEZPIECZNEGO ŁADOWANIA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data_safe(ws, expected_cols):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=expected_cols)
        # Usuwamy puste wiersze i sprawdzamy czy kolumny istnieją
        df = df.dropna(how='all')
        for col in expected_cols:
            if col not in df.columns:
                df[col] = "" # Dodaj brakującą kolumnę
        return df.reset_index(drop=True)
    except:
        return pd.DataFrame(columns=expected_cols)

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

# --- 3. INICJALIZACJA ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

# Definiujemy poprawne kolumny dla każdej zakładki
if 'przepisy' not in st.session_state: 
    st.session_state.przepisy = get_data_safe("Przepisy", ["Nazwa", "Skladnik", "Ilosc"])
if 'spizarnia_df' not in st.session_state: 
    st.session_state.spizarnia_df = get_data_safe("Spizarnia", ["Produkt", "Ilosc", "Czy_Stale", "Min_Ilosc"])
if 'plan_df' not in st.session_state: 
    st.session_state.plan_df = get_data_safe("Plan", ["Klucz", "Wybor"])

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
miesiace_pl = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]

# --- 4. STRONY ---

if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"""
        <div class='day-banner'>
            <h1>{dni_pl[teraz.weekday()]}</h1>
            <p>{teraz.day} {miesiace_pl[teraz.month-1]} {teraz.year}</p>
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

elif st.session_state.page == "Plan":
    st.subheader("📅 Planowanie Posiłków")
    if st.button("⬅ Powrót"): st.session_state.page = "Home"; st.rerun()
    
    cp, ci, cn = st.columns([1, 2, 1])
    if cp.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    if cn.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()
    
    start = datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)
    t_id = start.strftime("%Y-%V")
    
    for i, d_n in enumerate(dni_pl):
        with st.expander(f"{d_n} ({(start + timedelta(days=i)).strftime('%d.%m')})"):
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{d_n}_{typ}"
                
                # Bezpieczne pobieranie wyboru
                plan = st.session_state.plan_df
                istn = plan[plan['Klucz'] == k]['Wybor'].values[0] if k in plan['Klucz'].values else "Brak"
                
                # Pobieranie opcji z przepisów (bezpieczne)
                opcje = ["Brak"] + sorted(st.session_state.przepisy['Nazwa'].dropna().unique().tolist())
                
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                if wyb != istn:
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([st.session_state.plan_df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)
                    save_data(st.session_state.plan_df, "Plan"); st.rerun()

elif st.session_state.page == "Spizarnia":
    st.subheader("🏠 Twoja Spiżarnia")
    if st.button("⬅ Powrót"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ Dodaj nowy produkt"):
        with st.form("new_item"):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            n, q, s, m = c1.text_input("Nazwa"), c2.number_input("Ilość", 0.0), c3.checkbox("Produkt stały"), c4.number_input("Min", 0.0)
            if st.form_submit_button("Dodaj"):
                st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}])], ignore_index=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        nq = c2.number_input("Q", float(row['Ilosc']), key=f"q_{idx}", label_visibility="collapsed")
        is_st = True if str(row['Czy_Stale']).upper() == 'TAK' else False
        n_st, nm = c3.checkbox("📌", value=is_st, key=f"s_{idx}"), c4.number_input("M", float(row['Min_Ilosc']), key=f"m_{idx}", label_visibility="collapsed") if is_st else 0.0
        
        if nq != float(row['Ilosc']) or n_st != is_st or (n_st and nm != float(row['Min_Ilosc'])):
            st.session_state.spizarnia_df.at[idx, 'Ilosc'], st.session_state.spizarnia_df.at[idx, 'Czy_Stale'], st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = nq, ("TAK" if n_st else "NIE"), nm
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()
        if c5.button("🗑️", key=f"del_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
            save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

elif st.session_state.page == "Dodaj":
    st.subheader("📖 Przepisy")
    if st.button("⬅ Powrót"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ Nowa potrawa"):
        np = st.text_input("Nazwa potrawy")
        if st.button("Utwórz kartę"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0}])], ignore_index=True)
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

    if not st.session_state.przepisy.empty:
        wyb = st.selectbox("Edytuj:", sorted(st.session_state.przepisy['Nazwa'].dropna().unique().tolist()))
        items = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wyb].copy()
        
        rows_data = []
        for idx, row in items.iterrows():
            c1, c2, c3 = st.columns([3, 1, 0.5])
            ns, ni = c1.text_input("S", row['Skladnik'], key=f"sn_{idx}"), c2.number_input("Q", value=float(row['Ilosc']), key=f"si_{idx}")
            rows_data.append({"idx": idx, "S": ns, "I": ni})
            if c3.button("🗑️", key=f"dr_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()
        
        c_add, c_save = st.columns(2)
        if c_add.button("➕ Dodaj wiersz"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0}])], ignore_index=True)
            st.rerun()
        if c_save.button("💾 ZAPISZ PRZEPIS", type="primary"):
            for r in rows_data:
                st.session_state.przepisy.at[r['idx'], 'Skladnik'], st.session_state.przepisy.at[r['idx'], 'Ilosc'] = r['S'], r['I']
            save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Zakupy")
    if st.button("⬅ Powrót"): st.session_state.page = "Home"; st.rerun()
    st.info("Lista zakupów pojawi się tutaj po wypełnieniu Planu i Spiżarni.")
