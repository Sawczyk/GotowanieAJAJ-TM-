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
    
    .missing-item { color: #d32f2f; font-size: 0.85rem; padding: 5px 10px; border-left: 3px solid #d32f2f; background: #fff5f5; margin: 5px 0; border-radius: 4px; }
    .have-item { color: #2E7D32; font-size: 0.85rem; padding: 5px 10px; border-left: 3px solid #2E7D32; background: #f1f8e9; margin: 5px 0; border-radius: 4px; }
    .kcal-tag { color: #2E7D32; font-weight: 600; font-size: 1rem; margin-top: 10px; border-top: 1px solid #eee; padding-top: 10px; }
    .portion-box { background: #f9f9f9; padding: 10px; border-radius: 8px; margin-bottom: 10px; border: 1px solid #eee; }
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
        df.columns = [str(c).strip() for c in df.columns]
        for c in cols:
            if c not in df.columns:
                df[c] = 1 if c == "Porcje" else (0 if c in ["Kalorie", "Min_Ilosc", "Ilosc"] else "")
        return df[cols].dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame(columns=cols)

def save_now(df, ws_name):
    try:
        df_to_save = df.dropna(how='all').reset_index(drop=True)
        conn.update(worksheet=ws_name, data=df_to_save)
        st.cache_data.clear()
        st.toast(f"✅ Zsynchronizowano: {ws_name}")
    except: st.error("Błąd zapisu!")

# --- 4. INICJALIZACJA SESJI ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

STRUCT_PRZEPISY = ["Nazwa", "Skladnik", "Ilosc", "Kalorie", "Porcje"]
STRUCT_SPIZARNIA = ["Produkt", "Ilosc", "Czy_Stale", "Min_Ilosc"]
STRUCT_PLAN = ["Klucz", "Wybor", "Ile_Porcji"] # Dodano Ile_Porcji do struktury planu

if 'przepisy' not in st.session_state: st.session_state.przepisy = safe_load("Przepisy", STRUCT_PRZEPISY)
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = safe_load("Spizarnia", STRUCT_SPIZARNIA)
if 'plan_df' not in st.session_state: st.session_state.plan_df = safe_load("Plan", STRUCT_PLAN)

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
miesiace_pl = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]

# --- 5. RENDEROWANIE ---

if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"<div class='day-banner'><h1>{dni_pl[teraz.weekday()]}</h1><p>{teraz.day} {miesiace_pl[teraz.month-1]} {teraz.year}</p></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📅\nPLAN", use_container_width=True, type="primary"): st.session_state.page = "Plan"; st.rerun()
    if c2.button("🏠\nSPIŻARNIA", use_container_width=True): st.session_state.page = "Spizarnia"; st.rerun()
    if c3.button("📖\nPRZEPISY", use_container_width=True): st.session_state.page = "Dodaj"; st.rerun()
    if c4.button("🛒\nZAKUPY", use_container_width=True): st.session_state.page = "Zakupy"; st.rerun()

elif st.session_state.page == "Plan":
    st.subheader("📅 Planowanie tygodnia")
    c_back, c_nav, c_save = st.columns([1, 2, 1])
    if c_back.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    with c_nav:
        n1, n2, n3 = st.columns(3)
        if n1.button("◀ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
        if n2.button("Obecny"): st.session_state.week_offset = 0; st.rerun()
        if n3.button("Następny ▶"): st.session_state.week_offset += 1; st.rerun()
    if c_save.button("💾 ZAPISZ PLAN", type="primary"): save_now(st.session_state.plan_df, "Plan")

    start_date = datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)
    week_id = start_date.strftime("%Y-%V")

    for i, dzien in enumerate(dni_pl):
        with st.expander(f"{dzien} ({(start_date + timedelta(days=i)).strftime('%d.%m')})"):
            suma_kcal_dnia = 0
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{week_id}_{dzien}_{typ}"
                
                # Pobieranie istniejących danych
                istn_row = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]
                istn_wybor = istn_row['Wybor'].values[0] if not istn_row.empty else "Brak"
                istn_ile_porcji = to_num(istn_row['Ile_Porcji'].values[0]) if not istn_row.empty and 'Ile_Porcji' in istn_row.columns else 0
                
                opcje = ["Brak"] + sorted([p for p in st.session_state.przepisy['Nazwa'].unique().tolist() if str(p).strip()])
                
                col_sel, col_por = st.columns([3, 1])
                wybor = col_sel.selectbox(f"{typ}:", opcje, index=opcje.index(istn_wybor) if istn_wybor in opcje else 0, key=f"sel_{k}")
                
                if wybor != "Brak":
                    przepis_dane = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wybor]
                    porcje_baza = max(1.0, to_num(przepis_dane['Porcje'].iloc[0]))
                    
                    # Domyślnie ustawiamy porcje z bazy, jeśli nie było nic zapisane
                    val_porcje = istn_ile_porcji if istn_ile_porcji > 0 else porcje_baza
                    ile_chce = col_por.number_input("Ile porcji?", min_value=0.5, value=float(val_porcje), step=0.5, key=f"por_{k}")
                    
                    # Mnożnik (Ile chce / Baza przepisu)
                    mnoznik = ile_chce / porcje_baza
                    
                    st.markdown("<div class='portion-box'>", unsafe_allow_html=True)
                    for _, r in przepis_dane.iterrows():
                        s_nazwa = str(r['Skladnik']).lower().strip()
                        potrzeba_oryg = to_num(r['Ilosc'])
                        potrzeba_skalowana = round(potrzeba_oryg * mnoznik, 2)
                        
                        mam = st.session_state.spizarnia_df[st.session_state.spizarnia_df['Produkt'].str.lower().str.strip() == s_nazwa]['Ilosc'].apply(to_num).sum()
                        
                        if mam < potrzeba_skalowana:
                            st.markdown(f"<div class='missing-item'>❌ {r['Skladnik']}: {potrzeba_skalowana} (brakuje: {round(potrzeba_skalowana-mam, 2)})</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='have-item'>✅ {r['Skladnik']}: {potrzeba_skalowana} (w spiżarni: {mam})</div>", unsafe_allow_html=True)
                    
                    kcal_skalowane = (to_num(przepis_dane['Kalorie'].iloc[0]) / porcje_baza) * ile_chce
                    suma_kcal_dnia += kcal_skalowane
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    ile_chce = 0

                # Aktualizacja sesji planu
                if (wybor != istn_wybor) or (ile_chce != istn_ile_porcji):
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    if wybor != "Brak":
                        new_data = pd.DataFrame([{"Klucz": k, "Wybor": wybor, "Ile_Porcji": ile_chce}])
                        st.session_state.plan_df = pd.concat([st.session_state.plan_df, new_data], ignore_index=True)

            if suma_kcal_dnia > 0:
                st.markdown(f"<p class='kcal-tag'>🔥 Razem kalorie dnia: {int(suma_kcal_dnia)} kcal</p>", unsafe_allow_html=True)

elif st.session_state.page == "Spizarnia":
    st.subheader("🏠 Stan Spiżarni")
    c_back, c_save = st.columns(2)
    if c_back.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    if c_save.button("💾 ZAPISZ", type="primary"): save_now(st.session_state.spizarnia_df, "Spizarnia")
    
    with st.expander("➕ DODAJ PRODUKT"):
        with st.form("add_p", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            nazwa = c1.text_input("Produkt")
            ilosc = c2.number_input("Ilość", 0.0)
            stale = c3.checkbox("Produkt stały?")
            minim = c4.number_input("Min. Ilość", 0.0)
            if st.form_submit_button("Dodaj"):
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
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True); st.rerun()

elif st.session_state.page == "Dodaj":
    st.subheader("📖 Biblioteka Przepisów")
    if st.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ UTWÓRZ NOWĄ POTRAWĘ"):
        np = st.text_input("Nazwa potrawy")
        pk = st.number_input("Kaloryczność (dla liczby porcji poniżej)", value=0)
        pp = st.number_input("Dla ilu porcji jest ten przepis?", value=1, min_value=1)
        if st.button("Utwórz kartę"):
            if np:
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0, "Kalorie": pk, "Porcje": pp}])], ignore_index=True)
                st.rerun()

    if not st.session_state.przepisy.empty:
        with st.expander("📝 EDYTUJ ISTNIEJĄCE PRZEPISY"):
            wyb_edycja = st.selectbox("Wybierz potrawę:", sorted(st.session_state.przepisy['Nazwa'].unique()))
            mask = st.session_state.przepisy['Nazwa'] == wyb_edycja
            
            c_kcal, c_porc = st.columns(2)
            st.session_state.przepisy.loc[mask, 'Kalorie'] = c_kcal.number_input("Kalorie całości:", value=int(to_num(st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0])))
            st.session_state.przepisy.loc[mask, 'Porcje'] = c_porc.number_input("Bazowa liczba porcji:", value=int(to_num(st.session_state.przepisy.loc[mask, 'Porcje'].iloc[0])))
            
            for idx, row in st.session_state.przepisy[mask].iterrows():
                c1, c2, c3 = st.columns([3, 1, 0.5])
                st.session_state.przepisy.at[idx, 'Skladnik'] = c1.text_input("Składnik", row['Skladnik'], key=f"sk_{idx}", label_visibility="collapsed")
                st.session_state.przepisy.at[idx, 'Ilosc'] = c2.number_input("Ilość", to_num(row['Ilosc']), key=f"il_{idx}", label_visibility="collapsed")
                if c3.button("🗑️", key=f"r_del_{idx}"):
                    st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True); st.rerun()
            
            if st.button("➕ Dodaj składnik"):
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb_edycja, "Skladnik": "", "Ilosc": 0, "Kalorie": st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0], "Porcje": st.session_state.przepisy.loc[mask, 'Porcje'].iloc[0]}])], ignore_index=True); st.rerun()
            if st.button("💾 ZAPISZ PRZEPIS", type="primary"): save_now(st.session_state.przepisy, "Przepisy")

elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Lista Zakupów")
    if st.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    
    w_id = (datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)).strftime("%Y-%V")
    potrzeby = {}
    
    plan = st.session_state.plan_df[st.session_state.plan_df['Klucz'].str.contains(w_id, na=False)]
    for _, row_p in plan.iterrows():
        potrawa = row_p['Wybor']
        ile_chce = to_num(row_p['Ile_Porcji'])
        if potrawa != "Brak":
            przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == potrawa]
            porcje_baza = max(1.0, to_num(przepis['Porcje'].iloc[0]))
            mnoznik = ile_chce / porcje_baza
            for _, r in przepis.iterrows():
                s_name = str(r['Skladnik']).lower().strip()
                if s_name: potrzeby[s_name] = potrzeby.get(s_name, 0) + (to_num(r['Ilosc']) * mnoznik)
    
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
        tekst = f"ZAKUPY\n" + "\n".join([f"☐ {b['Produkt']}: {b['Do kupienia']}" for b in wynik_zakupy])
        st.download_button("📥 Pobierz TXT", tekst, file_name="zakupy.txt", use_container_width=True)
    else: st.success("Masz wszystko! 🎉")
