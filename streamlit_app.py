import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA I STYLIZACJA ---
st.set_page_config(page_title="Planer Kuchni", page_icon="🍳", layout="wide")

# Estetyka: Inter, kolorystyka #2E7D32, zaokrąglone rogi i cienie
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    
    /* Globalne czcionki */
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; }
    
    /* Baner dnia */
    .day-banner { 
        background-color: #2E7D32; 
        color: white; 
        padding: 25px; 
        border-radius: 15px; 
        text-align: center; 
        margin-bottom: 30px; 
        box-shadow: 0 4px 15px rgba(46, 125, 50, 0.2); 
    }
    .day-banner h1 { margin: 0; font-size: 2.5rem; font-weight: 600; }
    .day-banner p { margin: 5px 0 0 0; font-size: 1.2rem; opacity: 0.9; }
    
    /* Przyciski */
    div.stButton > button { 
        border-radius: 12px; 
        font-weight: 600 !important; 
        transition: all 0.3s ease;
    }
    div.stButton > button[kind="primary"] { 
        background-color: #2E7D32 !important; 
        color: white !important; 
        height: 60px !important; 
        width: 100% !important;
    }
    
    /* Tagi i metryki */
    .missing-tag { color: #d32f2f; font-weight: 600; font-size: 0.85rem; display: block; margin-bottom: 10px; }
    .kcal-tag { color: #2E7D32; font-weight: 600; font-size: 0.9rem; }
    
    /* Styl tabeli */
    .stTable { border-radius: 10px; overflow: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNKCJE POMOCNICZE ---
def to_num(val):
    try: 
        if pd.isna(val): return 0.0
        return float(str(val).replace(',', '.').strip())
    except: return 0.0

# --- 3. DANE I POŁĄCZENIE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_load(ws, cols):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=cols)
        df.columns = [str(c).strip() for c in df.columns]
        for c in cols:
            if c not in df.columns: df[c] = 0 if c == "Kalorie" or c == "Min_Ilosc" or c == "Ilosc" else ""
        return df[cols].dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame(columns=cols)

def save_now(df, ws_name):
    try:
        # Czyszczenie przed zapisem
        df_to_save = df.dropna(how='all').reset_index(drop=True)
        conn.update(worksheet=ws_name, data=df_to_save)
        
        # Synchronizacja session_state
        if ws_name == "Przepisy": st.session_state.przepisy = df_to_save
        if ws_name == "Spizarnia": st.session_state.spizarnia_df = df_to_save
        if ws_name == "Plan": st.session_state.plan_df = df_to_save
        
        st.cache_data.clear()
        st.toast(f"✅ Zapisano pomyślnie: {ws_name}")
    except Exception as e: 
        st.error(f"Błąd zapisu: {e}")

# --- 4. INICJALIZACJA SESJI ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

# Ładowanie danych tylko jeśli nie ma ich w sesji
if 'przepisy' not in st.session_state: st.session_state.przepisy = safe_load("Przepisy", ["Nazwa", "Skladnik", "Ilosc", "Kalorie"])
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = safe_load("Spizarnia", ["Produkt", "Ilosc", "Czy_Stale", "Min_Ilosc"])
if 'plan_df' not in st.session_state: st.session_state.plan_df = safe_load("Plan", ["Klucz", "Wybor"])

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
miesiace_pl = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]

# --- 5. LOGIKA RENDEROWANIA ---

# --- PAGE: HOME ---
if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"""
        <div class='day-banner'>
            <h1>{dni_pl[teraz.weekday()]}</h1>
            <p>{teraz.day} {miesiace_pl[teraz.month-1]} {teraz.year}</p>
        </div>
        """, unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📅\nPLAN", use_container_width=True, type="primary"): st.session_state.page = "Plan"; st.rerun()
    if c2.button("🏠\nSPIŻARNIA", use_container_width=True): st.session_state.page = "Spizarnia"; st.rerun()
    if c3.button("📖\nPRZEPISY", use_container_width=True): st.session_state.page = "Dodaj"; st.rerun()
    if c4.button("🛒\nZAKUPY", use_container_width=True): st.session_state.page = "Zakupy"; st.rerun()

# --- PAGE: PLANOWANIE ---
elif st.session_state.page == "Plan":
    st.subheader("📅 Planowanie tygodnia")
    
    c_back, c_prev, c_curr, c_next, c_save = st.columns([1, 0.5, 1, 0.5, 1])
    if c_back.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    if c_prev.button("◀"): st.session_state.week_offset -= 1; st.rerun()
    if c_curr.button("Dzisiaj"): st.session_state.week_offset = 0; st.rerun()
    if c_next.button("▶"): st.session_state.week_offset += 1; st.rerun()
    if c_save.button("💾 ZAPISZ PLAN", type="primary"): save_now(st.session_state.plan_df, "Plan")
    
    start = datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)
    t_id = start.strftime("%Y-%V")
    
    for i, d_n in enumerate(dni_pl):
        with st.expander(f"{d_n} ({(start + timedelta(days=i)).strftime('%d.%m')})"):
            total_day_kcal = 0
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{d_n}_{typ}"
                # Pobierz wybór z DF lub sesji selectboxa
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if k in st.session_state.plan_df['Klucz'].values else "Brak"
                
                opcje = ["Brak"] + sorted([p for p in st.session_state.przepisy['Nazwa'].unique().tolist() if str(p).strip()])
                
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                
                if wyb != "Brak":
                    # Sprawdzanie braków
                    sklad_p = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wyb]
                    braki = []
                    for _, r in sklad_p.iterrows():
                        mam = st.session_state.spizarnia_df[st.session_state.spizarnia_df['Produkt'].str.lower() == str(r['Skladnik']).lower()]['Ilosc'].apply(to_num).sum()
                        if mam < to_num(r['Ilosc']): braki.append(str(r['Skladnik']).lower())
                    
                    if braki: st.markdown(f"<span class='missing-tag'>⚠️ Brak: {', '.join(braki)}</span>", unsafe_allow_html=True)
                    
                    # Kalorie
                    kcal = to_num(sklad_p['Kalorie'].iloc[0]) if not sklad_p.empty else 0
                    total_day_kcal += kcal
                
                # Aktualizacja planu w pamięci
                if wyb != istn:
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([st.session_state.plan_df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)
            
            if total_day_kcal > 0:
                st.markdown(f"<p class='kcal-tag'>🔥 Suma dnia: {int(total_day_kcal)} kcal</p>", unsafe_allow_html=True)

# --- PAGE: SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    st.subheader("🏠 Stan Spiżarni")
    c_back, c_save = st.columns(2)
    if c_back.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    if c_save.button("💾 ZAPISZ SPIŻARNIĘ", type="primary"): save_now(st.session_state.spizarnia_df, "Spizarnia")
    
    with st.expander("➕ Dodaj nowy produkt"):
        with st.form("new_s", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            n = c1.text_input("Nazwa")
            q = c2.number_input("Ilość", 0.0)
            s = c3.checkbox("Stały?")
            m = c4.number_input("Min. Ilość", 0.0)
            if st.form_submit_button("Dodaj do listy"):
                if n:
                    new_item = {"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}
                    st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([new_item])], ignore_index=True)
                    st.rerun()

    # Edycja listy
    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        st.session_state.spizarnia_df.at[idx, 'Ilosc'] = c2.number_input("Q", to_num(row['Ilosc']), key=f"sq_{idx}", label_visibility="collapsed")
        is_st = str(row['Czy_Stale']).upper() == 'TAK'
        n_st = c3.checkbox("📌", value=is_st, key=f"ss_{idx}")
        st.session_state.spizarnia_df.at[idx, 'Czy_Stale'] = "TAK" if n_st else "NIE"
        st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = c4.number_input("M", to_num(row['Min_Ilosc']), key=f"sm_{idx}", label_visibility="collapsed") if n_st else 0.0
        if c5.button("🗑️", key=f"sdel_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
            st.rerun()

# --- PAGE: PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.subheader("📖 Zarządzanie Przepisami")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ DODAJ NOWĄ POTRAWĘ"):
        np = st.text_input("Nazwa potrawy")
        kcal = st.number_input("Kcal/porcja", value=0)
        if st.button("Utwórz przepis"):
            if np:
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Woda", "Ilosc": 0, "Kalorie": kcal}])], ignore_index=True)
                st.rerun()

    if not st.session_state.przepisy.empty:
        wyb = st.selectbox("Wybierz do edycji:", sorted(st.session_state.przepisy['Nazwa'].unique()))
        mask = st.session_state.przepisy['Nazwa'] == wyb
        
        # Edycja nazwy i kcal globalnie dla potrawy
        new_kcal = st.number_input("Kaloryczność:", value=int(to_num(st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0])))
        st.session_state.przepisy.loc[mask, 'Kalorie'] = new_kcal
        
        st.write("Składniki:")
        for idx, row in st.session_state.przepisy[mask].iterrows():
            c1, c2, c3 = st.columns([3, 1, 0.5])
            st.session_state.przepisy.at[idx, 'Skladnik'] = c1.text_input("Składnik", row['Skladnik'], key=f"rn_{idx}", label_visibility="collapsed")
            st.session_state.przepisy.at[idx, 'Ilosc'] = c2.number_input("Ilość", to_num(row['Ilosc']), key=f"ri_{idx}", label_visibility="collapsed")
            if c3.button("🗑️", key=f"rdel_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                st.rerun()
        
        c_add, c_save = st.columns(2)
        if c_add.button("➕ Dodaj składnik"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0, "Kalorie": new_kcal}])], ignore_index=True)
            st.rerun()
        if c_save.button("💾 ZAPISZ PRZEPIS", type="primary"): save_now(st.session_state.przepisy, "Przepisy")

# --- PAGE: ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Twoja Lista Zakupów")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    t_id = (datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)).strftime("%Y-%V")
    potrzeby = {}
    
    # 1. Zliczanie z planu
    plan_obecny = st.session_state.plan_df[st.session_state.plan_df['Klucz'].str.contains(t_id, na=False)]
    for potrawa in plan_obecny['Wybor']:
        if potrawa != "Brak":
            skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == potrawa]
            for _, r in skladniki.iterrows():
                s_name = str(r['Skladnik']).lower().strip()
                if s_name and s_name not in ["składnik", "nan", ""]:
                    potrzeby[s_name] = potrzeby.get(s_name, 0) + to_num(r['Ilosc'])
    
    # 2. Porównanie ze spiżarnią (w tym produkty stałe)
    braki = []
    spizarnia_produkty = [p.lower().strip() for p in st.session_state.spizarnia_df['Produkt'].tolist()]
    
    # Sprawdź produkty ze spiżarni
    for _, r in st.session_state.spizarnia_df.iterrows():
        p_name = str(r['Produkt']).lower().strip()
        mam = to_num(r['Ilosc'])
        min_wym = to_num(r['Min_Ilosc']) if str(r['Czy_Stale']).upper() == "TAK" else 0
        wymagane = max(potrzeby.get(p_name, 0), min_wym)
        
        if wymagane > mam:
            braki.append({"Produkt": p_name.capitalize(), "Kupić": wymagane - mam, "W spiżarni": mam})
        
        if p_name in potrzeby: del potrzeby[p_name]
    
    # Dodaj rzeczy z planu, których w ogóle nie ma w spiżarni
    for s_name, ile in potrzeby.items():
        if ile > 0:
            braki.append({"Produkt": s_name.capitalize(), "Kupić": ile, "W spiżarni": 0})

    if braki:
        df_braki = pd.DataFrame(braki)
        st.table(df_braki)
        
        # Generator tekstu do eksportu
        export_text = f"🛒 LISTA ZAKUPÓW ({datetime.now().strftime('%d.%m.%Y')})\n" + "="*30 + "\n"
        for _, b in df_braki.iterrows():
            export_text += f"☐ {b['Produkt']}: {b['Kupić']} (obecnie: {b['W spiżarni']})\n"
        
        st.download_button(
            label="📥 Pobierz listę zakupów (.txt)",
            data=export_text,
            file_name=f"lista_zakupow_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    else:
        st.success("Wszystko masz! Twoja spiżarnia i plan są zsynchronizowane. 🎉")
