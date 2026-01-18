import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA I STYLIZACJA ---
st.set_page_config(page_title="Planer Kuchni", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; }
    .day-banner { 
        background-color: #2E7D32; color: white; padding: 25px; border-radius: 15px; 
        text-align: center; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(46, 125, 50, 0.2); 
    }
    .day-banner h1 { margin: 0; font-size: 2.5rem; font-weight: 600; }
    div.stButton > button { border-radius: 12px; font-weight: 600 !important; }
    div.stButton > button[kind="primary"] { background-color: #2E7D32 !important; color: white !important; height: 60px !important; width: 100% !important; }
    .missing-item { color: #d32f2f; font-size: 0.85rem; padding-left: 10px; border-left: 2px solid #d32f2f; margin: 5px 0; }
    .have-item { color: #2E7D32; font-size: 0.85rem; padding-left: 10px; border-left: 2px solid #2E7D32; margin: 5px 0; opacity: 0.8; }
    .kcal-tag { color: #2E7D32; font-weight: 600; font-size: 0.9rem; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNKCJE POMOCNICZE ---
def to_num(val):
    try: 
        if pd.isna(val) or val == "": return 0.0
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
            if c not in df.columns: df[c] = 0 if c in ["Kalorie", "Min_Ilosc", "Ilosc", "Porcje"] else ""
        return df[cols].dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame(columns=cols)

def save_now(df, ws_name):
    try:
        df_to_save = df.dropna(how='all').reset_index(drop=True)
        conn.update(worksheet=ws_name, data=df_to_save)
        st.cache_data.clear()
        st.toast(f"✅ Zsynchronizowano: {ws_name}")
    except Exception as e: st.error(f"Błąd zapisu: {e}")

# --- 4. INICJALIZACJA SESJI ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

# Rozszerzona struktura o "Porcje"
if 'przepisy' not in st.session_state: st.session_state.przepisy = safe_load("Przepisy", ["Nazwa", "Skladnik", "Ilosc", "Kalorie", "Porcje"])
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = safe_load("Spizarnia", ["Produkt", "Ilosc", "Czy_Stale", "Min_Ilosc"])
if 'plan_df' not in st.session_state: st.session_state.plan_df = safe_load("Plan", ["Klucz", "Wybor"])

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
miesiace_pl = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]

# --- 5. RENDEROWANIE ---

# --- HOME ---
if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"<div class='day-banner'><h1>{dni_pl[teraz.weekday()]}</h1><p>{teraz.day} {miesiace_pl[teraz.month-1]} {teraz.year}</p></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📅\nPLAN", use_container_width=True, type="primary"): st.session_state.page = "Plan"; st.rerun()
    if c2.button("🏠\nSPIŻARNIA", use_container_width=True): st.session_state.page = "Spizarnia"; st.rerun()
    if c3.button("📖\nPRZEPISY", use_container_width=True): st.session_state.page = "Dodaj"; st.rerun()
    if c4.button("🛒\nZAKUPY", use_container_width=True): st.session_state.page = "Zakupy"; st.rerun()

# --- PLANOWANIE ---
elif st.session_state.page == "Plan":
    st.subheader("📅 Planowanie tygodnia")
    c_back, c_nav, c_save = st.columns([1, 2, 1])
    if c_back.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    with c_nav:
        n1, n2, n3 = st.columns(3)
        if n1.button("◀ Tydzień"): st.session_state.week_offset -= 1; st.rerun()
        if n2.button("Obecny"): st.session_state.week_offset = 0; st.rerun()
        if n3.button("Tydzień ▶"): st.session_state.week_offset += 1; st.rerun()
    if c_save.button("💾 ZAPISZ", type="primary"): save_now(st.session_state.plan_df, "Plan")

    start = datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)
    t_id = start.strftime("%Y-%V")

    for i, d_n in enumerate(dni_pl):
        with st.expander(f"{d_n} ({(start + timedelta(days=i)).strftime('%d.%m')})"):
            day_kcal = 0
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{d_n}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if k in st.session_state.plan_df['Klucz'].values else "Brak"
                opcje = ["Brak"] + sorted([p for p in st.session_state.przepisy['Nazwa'].unique().tolist() if str(p).strip()])
                
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                
                if wyb != "Brak":
                    skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wyb]
                    porcje = skladniki['Porcje'].iloc[0] if not skladniki.empty else 1
                    st.caption(f"🍱 Liczba porcji w przepisie: {porcje}")
                    
                    for _, r in skladniki.iterrows():
                        nazwa_s = str(r['Skladnik']).lower()
                        wymagana = to_num(r['Ilosc'])
                        mam = st.session_state.spizarnia_df[st.session_state.spizarnia_df['Produkt'].str.lower() == nazwa_s]['Ilosc'].apply(to_num).sum()
                        
                        if mam < wymagana:
                            st.markdown(f"<div class='missing-item'>❌ {r['Skladnik']}: {wymagana} (brakuje: {round(wymagana-mam, 2)})</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='have-item'>✅ {r['Skladnik']}: {wymagana} (w spizarni: {mam})</div>", unsafe_allow_html=True)
                    
                    day_kcal += to_num(skladniki['Kalorie'].iloc[0])

                if wyb != istn:
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([st.session_state.plan_df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)
            
            if day_kcal > 0: st.markdown(f"<p class='kcal-tag'>🔥 Razem: {int(day_kcal)} kcal</p>", unsafe_allow_html=True)

# --- SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    st.subheader("🏠 Stan Spiżarni")
    c_back, c_save = st.columns(2)
    if c_back.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    if c_save.button("💾 ZAPISZ", type="primary"): save_now(st.session_state.spizarnia_df, "Spizarnia")
    
    with st.expander("➕ DODAJ PRODUKT"):
        with st.form("new_prod", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            n = c1.text_input("Nazwa")
            q = c2.number_input("Ilość", 0.0)
            s = c3.checkbox("Stały?")
            m = c4.number_input("Min.", 0.0)
            if st.form_submit_button("Dodaj"):
                if n:
                    st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}])], ignore_index=True)
                    st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        st.session_state.spizarnia_df.at[idx, 'Ilosc'] = c2.number_input("Q", to_num(row['Ilosc']), key=f"sq_{idx}", label_visibility="collapsed")
        is_st = str(row['Czy_Stale']).upper() == 'TAK'
        n_st = c3.checkbox("📌", value=is_st, key=f"ss_{idx}")
        st.session_state.spizarnia_df.at[idx, 'Czy_Stale'] = "TAK" if n_st else "NIE"
        st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = c4.number_input("M", to_num(row['Min_Ilosc']), key=f"sm_{idx}", label_visibility="collapsed") if n_st else 0.0
        if c5.button("🗑️", key=f"sdel_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True); st.rerun()

# --- PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.subheader("📖 Biblioteka Przepisów")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    # 1. DODAWANIE
    with st.expander("➕ UTWÓRZ NOWĄ POTRAWĘ"):
        np = st.text_input("Nazwa potrawy")
        pk = st.number_input("Kalorie (łącznie)", 0)
        pp = st.number_input("Liczba porcji", 1)
        if st.button("Zatwierdź nową potrawę"):
            if np:
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0, "Kalorie": pk, "Porcje": pp}])], ignore_index=True)
                st.rerun()

    # 2. EDYCJA (Schowana w expanderze zgodnie z prośbą)
    if not st.session_state.przepisy.empty:
        with st.expander("📝 EDYTUJ ISTNIEJĄCY PRZEPIS"):
            wyb = st.selectbox("Wybierz potrawę:", sorted(st.session_state.przepisy['Nazwa'].unique()))
            mask = st.session_state.przepisy['Nazwa'] == wyb
            
            c_kcal, c_porc = st.columns(2)
            st.session_state.przepisy.loc[mask, 'Kalorie'] = c_kcal.number_input("Kalorie całości:", value=int(to_num(st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0])))
            st.session_state.przepisy.loc[mask, 'Porcje'] = c_porc.number_input("Liczba porcji:", value=int(to_num(st.session_state.przepisy.loc[mask, 'Porcje'].iloc[0])))
            
            st.write("Składniki:")
            for idx, row in st.session_state.przepisy[mask].iterrows():
                c1, c2, c3 = st.columns([3, 1, 0.5])
                st.session_state.przepisy.at[idx, 'Skladnik'] = c1.text_input("Nazwa", row['Skladnik'], key=f"rn_{idx}", label_visibility="collapsed")
                st.session_state.przepisy.at[idx, 'Ilosc'] = c2.number_input("Ilość", to_num(row['Ilosc']), key=f"ri_{idx}", label_visibility="collapsed")
                if c3.button("🗑️", key=f"rdel_{idx}"):
                    st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True); st.rerun()
            
            if st.button("➕ Dodaj składnik"):
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0, "Kalorie": st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0], "Porcje": st.session_state.przepisy.loc[mask, 'Porcje'].iloc[0]}])], ignore_index=True); st.rerun()
            
            if st.button("💾 ZAPISZ ZMIANY W PRZEPISIE", type="primary"): save_now(st.session_state.przepisy, "Przepisy")

# --- ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Lista Zakupów")
    if st.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    # Logika zakupów pozostaje bez zmian (zbiera braki z planu i min_ilosc)
    t_id = (datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)).strftime("%Y-%V")
    potrzeby = {}
    plan_obecny = st.session_state.plan_df[st.session_state.plan_df['Klucz'].str.contains(t_id, na=False)]
    for potrawa in plan_obecny['Wybor']:
        if potrawa != "Brak":
            skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == potrawa]
            for _, r in skladniki.iterrows():
                s_name = str(r['Skladnik']).lower().strip()
                if s_name: potrzeby[s_name] = potrzeby.get(s_name, 0) + to_num(r['Ilosc'])
    
    braki = []
    for _, r in st.session_state.spizarnia_df.iterrows():
        p_name = str(r['Produkt']).lower().strip()
        mam = to_num(r['Ilosc'])
        min_wym = to_num(r['Min_Ilosc']) if str(r['Czy_Stale']).upper() == "TAK" else 0
        wymagane = max(potrzeby.get(p_name, 0), min_wym)
        if wymagane > mam: braki.append({"Produkt": p_name.capitalize(), "Kupić": round(wymagane - mam, 2), "W spiżarni": mam})
        if p_name in potrzeby: del potrzeby[p_name]
    for s_name, ile in potrzeby.items():
        if ile > 0: braki.append({"Produkt": s_name.capitalize(), "Kupić": round(ile, 2), "W spiżarni": 0})

    if braki:
        st.table(pd.DataFrame(braki))
        txt = "LISTA ZAKUPÓW\n" + "\n".join([f"☐ {b['Produkt']}: {b['Kupić']}" for b in braki])
        st.download_button("📥 Pobierz TXT", txt, file_name="zakupy.txt", use_container_width=True)
    else: st.success("Wszystko masz! 🎉")
