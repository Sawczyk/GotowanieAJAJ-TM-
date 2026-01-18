import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA I STYLIZACJA (CLEAN & AESTHETIC) ---
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
    
    .missing-item { color: #d32f2f; font-size: 0.85rem; padding: 5px 10px; border-left: 3px solid #d32f2f; background: #fff5f5; margin: 5px 0; border-radius: 4px; }
    .have-item { color: #2E7D32; font-size: 0.85rem; padding: 5px 10px; border-left: 3px solid #2E7D32; background: #f1f8e9; margin: 5px 0; border-radius: 4px; }
    .kcal-tag { color: #2E7D32; font-weight: 600; font-size: 0.9rem; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNKCJE POMOCNICZE ---
def to_num(val):
    try: 
        if pd.isna(val) or str(val).strip() == "": return 0.0
        return float(str(val).replace(',', '.').strip())
    except: return 0.0

# --- 3. DANE I POŁĄCZENIE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_load(ws, cols):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=cols)
        
        # Standaryzacja nazw kolumn (usuwanie spacji)
        df.columns = [str(c).strip() for c in df.columns]
        
        # Zabezpieczenie przed brakiem kolumn w arkuszu (np. brak kolumny Porcje)
        for c in cols:
            if c not in df.columns:
                df[c] = 1 if c == "Porcje" else (0 if c in ["Kalorie", "Min_Ilosc", "Ilosc"] else "")
        
        return df[cols].dropna(how='all').reset_index(drop=True)
    except Exception as e:
        st.error(f"Błąd ładowania arkusza {ws}: {e}")
        return pd.DataFrame(columns=cols)

def save_now(df, ws_name):
    try:
        df_to_save = df.dropna(how='all').reset_index(drop=True)
        conn.update(worksheet=ws_name, data=df_to_save)
        st.cache_data.clear()
        st.toast(f"✅ Dane zapisane w arkuszu: {ws_name}")
    except Exception as e: 
        st.error(f"Błąd zapisu: {e}. Sprawdź uprawnienia arkusza!")

# --- 4. INICJALIZACJA SESJI ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

# Definicja struktury bazowej
STRUCT_PRZEPISY = ["Nazwa", "Skladnik", "Ilosc", "Kalorie", "Porcje"]
STRUCT_SPIZARNIA = ["Produkt", "Ilosc", "Czy_Stale", "Min_Ilosc"]
STRUCT_PLAN = ["Klucz", "Wybor"]

if 'przepisy' not in st.session_state: st.session_state.przepisy = safe_load("Przepisy", STRUCT_PRZEPISY)
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = safe_load("Spizarnia", STRUCT_SPIZARNIA)
if 'plan_df' not in st.session_state: st.session_state.plan_df = safe_load("Plan", STRUCT_PLAN)

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
miesiace_pl = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]

# --- 5. LOGIKA STRON ---

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
    
    if c_back.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    with c_nav:
        n1, n2, n3 = st.columns(3)
        if n1.button("◀ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
        if n2.button("Bieżący"): st.session_state.week_offset = 0; st.rerun()
        if n3.button("Następny ▶"): st.session_state.week_offset += 1; st.rerun()
    if c_save.button("💾 ZAPISZ PLAN", type="primary"): save_now(st.session_state.plan_df, "Plan")

    start_date = datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)
    week_id = start_date.strftime("%Y-%V")

    for i, dzien in enumerate(dni_pl):
        curr_date = (start_date + timedelta(days=i)).strftime('%d.%m')
        with st.expander(f"{dzien} ({curr_date})"):
            suma_kcal = 0
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{week_id}_{dzien}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if k in st.session_state.plan_df['Klucz'].values else "Brak"
                opcje = ["Brak"] + sorted([p for p in st.session_state.przepisy['Nazwa'].unique().tolist() if str(p).strip()])
                
                wybor = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                
                if wybor != "Brak":
                    przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wybor]
                    ile_porcji = przepis['Porcje'].iloc[0] if 'Porcje' in przepis.columns else 1
                    st.markdown(f"**🍱 Porcje w przepisie:** {ile_porcji}")
                    
                    for _, r in przepis.iterrows():
                        s_nazwa = str(r['Skladnik']).lower().strip()
                        potrzeba = to_num(r['Ilosc'])
                        # Sumowanie stanu ze spiżarni dla danego produktu
                        mam = st.session_state.spizarnia_df[st.session_state.spizarnia_df['Produkt'].str.lower().str.strip() == s_nazwa]['Ilosc'].apply(to_num).sum()
                        
                        if mam < potrzeba:
                            st.markdown(f"<div class='missing-item'>❌ {r['Skladnik']}: {potrzeba} (brakuje: {round(potrzeba-mam, 2)})</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='have-item'>✅ {r['Skladnik']}: {potrzeba} (w spiżarni: {mam})</div>", unsafe_allow_html=True)
                    
                    suma_kcal += to_num(przepis['Kalorie'].iloc[0])

                if wybor != istn:
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([st.session_state.plan_df, pd.DataFrame([{"Klucz": k, "Wybor": wybor}])], ignore_index=True)
            
            if suma_kcal > 0:
                st.markdown(f"<p class='kcal-tag'>🔥 Razem kalorie: {int(suma_kcal)} kcal</p>", unsafe_allow_html=True)

# --- SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    st.subheader("🏠 Zarządzanie Spiżarnią")
    c_back, c_save = st.columns(2)
    if c_back.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    if c_save.button("💾 ZAPISZ STAN", type="primary"): save_now(st.session_state.spizarnia_df, "Spizarnia")
    
    with st.expander("➕ DODAJ NOWY PRODUKT"):
        with st.form("add_p", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            nazwa = c1.text_input("Produkt")
            ilosc = c2.number_input("Ilość", 0.0)
            stale = c3.checkbox("Produkt stały?")
            minim = c4.number_input("Min. Ilość", 0.0)
            if st.form_submit_button("Dodaj do spisu"):
                if nazwa:
                    st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": nazwa, "Ilosc": ilosc, "Czy_Stale": "TAK" if stale else "NIE", "Min_Ilosc": minim}])], ignore_index=True)
                    st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        st.session_state.spizarnia_df.at[idx, 'Ilosc'] = c2.number_input("Ilość", to_num(row['Ilosc']), key=f"q_{idx}", label_visibility="collapsed")
        is_stale = str(row['Czy_Stale']).upper() == 'TAK'
        new_stale = c3.checkbox("Stały", value=is_stale, key=f"s_{idx}")
        st.session_state.spizarnia_df.at[idx, 'Czy_Stale'] = "TAK" if new_stale else "NIE"
        st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = c4.number_input("Min", to_num(row['Min_Ilosc']), key=f"m_{idx}", label_visibility="collapsed") if new_stale else 0.0
        if c5.button("🗑️", key=f"del_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
            st.rerun()

# --- PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.subheader("📖 Biblioteka Przepisów")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ DODAJ NOWĄ POTRAWĘ"):
        np = st.text_input("Nazwa potrawy")
        pk = st.number_input("Kaloryczność (całość)", value=0)
        pp = st.number_input("Liczba porcji", value=1, min_value=1)
        if st.button("Utwórz kartę przepisu"):
            if np:
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Woda", "Ilosc": 0, "Kalorie": pk, "Porcje": pp}])], ignore_index=True)
                st.rerun()

    if not st.session_state.przepisy.empty:
        with st.expander("📝 EDYTUJ ISTNIEJĄCE PRZEPISY"):
            wyb_edycja = st.selectbox("Wybierz potrawę:", sorted(st.session_state.przepisy['Nazwa'].unique()))
            mask = st.session_state.przepisy['Nazwa'] == wyb_edycja
            
            c_kcal, c_porc = st.columns(2)
            st.session_state.przepisy.loc[mask, 'Kalorie'] = c_kcal.number_input("Kalorie (suma):", value=int(to_num(st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0])))
            st.session_state.przepisy.loc[mask, 'Porcje'] = c_porc.number_input("Domyślne porcje:", value=int(to_num(st.session_state.przepisy.loc[mask, 'Porcje'].iloc[0])))
            
            st.write("---")
            for idx, row in st.session_state.przepisy[mask].iterrows():
                c1, c2, c3 = st.columns([3, 1, 0.5])
                st.session_state.przepisy.at[idx, 'Skladnik'] = c1.text_input("Składnik", row['Skladnik'], key=f"sk_{idx}", label_visibility="collapsed")
                st.session_state.przepisy.at[idx, 'Ilosc'] = c2.number_input("Ilość", to_num(row['Ilosc']), key=f"il_{idx}", label_visibility="collapsed")
                if c3.button("🗑️", key=f"r_del_{idx}"):
                    st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True); st.rerun()
            
            if st.button("➕ Dodaj kolejny składnik"):
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb_edycja, "Skladnik": "", "Ilosc": 0, "Kalorie": st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0], "Porcje": st.session_state.przepisy.loc[mask, 'Porcje'].iloc[0]}])], ignore_index=True); st.rerun()
            
            if st.button("💾 ZAPISZ PRZEPIS", type="primary"):
                save_now(st.session_state.przepisy, "Przepisy")

# --- ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Lista Zakupów")
    if st.button("⬅ Menu Główne"): st.session_state.page = "Home"; st.rerun()
    
    w_id = (datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)).strftime("%Y-%V")
    potrzeby = {}
    
    # 1. Zbiórka z planu
    plan = st.session_state.plan_df[st.session_state.plan_df['Klucz'].str.contains(w_id, na=False)]
    for potrawa in plan['Wybor']:
        if potrawa != "Brak":
            skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == potrawa]
            for _, r in skladniki.iterrows():
                s_name = str(r['Skladnik']).lower().strip()
                if s_name: potrzeby[s_name] = potrzeby.get(s_name, 0) + to_num(r['Ilosc'])
    
    # 2. Porównanie i braki stałe
    wynik_zakupy = []
    for _, r in st.session_state.spizarnia_df.iterrows():
        p_name = str(r['Produkt']).lower().strip()
        mam = to_num(r['Ilosc'])
        min_w = to_num(r['Min_Ilosc']) if str(r['Czy_Stale']).upper() == "TAK" else 0
        wymagane = max(potrzeby.get(p_name, 0), min_w)
        
        if wymagane > mam:
            wynik_zakupy.append({"Produkt": p_name.capitalize(), "Do kupienia": round(wymagane - mam, 2), "W domu": mam})
        if p_name in potrzeby: del potrzeby[p_name]
        
    for s_name, ile in potrzeby.items():
        if ile > 0: wynik_zakupy.append({"Produkt": s_name.capitalize(), "Do kupienia": round(ile, 2), "W domu": 0})

    if wynik_zakupy:
        st.table(pd.DataFrame(wynik_zakupy))
        # Eksport do TXT
        tekst = f"ZAKUPY {datetime.now().strftime('%d.%m')}\n" + "-"*20 + "\n"
        for b in wynik_zakupy: tekst += f"☐ {b['Produkt']}: {b['Do kupienia']}\n"
        st.download_button("📥 Pobierz listę na telefon", tekst, file_name="zakupy.txt", use_container_width=True)
    else:
        st.success("Wszystko masz! Możesz odpocząć. 🎉")
