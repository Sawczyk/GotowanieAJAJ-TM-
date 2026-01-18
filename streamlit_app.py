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
    .portion-box { background: #f9f9f9; padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 1px solid #eee; }
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
        # TTL=0 wymusza odświeżenie danych z chmury
        df = conn.read(worksheet=ws, ttl=0)
        
        if df is None:
            return pd.DataFrame(columns=cols)
        
        # Standaryzacja nazw kolumn
        df.columns = [str(c).strip() for c in df.columns]
        
        # REPARACJA KOLUMN: Jeśli kolumny nie ma w DF, dodaj ją z domyślną wartością
        for c in cols:
            if c not in df.columns:
                if c in ["Porcje", "Ile_Porcji"]:
                    df[c] = 1.0
                elif c in ["Kalorie", "Min_Ilosc", "Ilosc"]:
                    df[c] = 0.0
                else:
                    df[c] = ""
        
        # Zwracamy tylko wymagane kolumny, upewniając się, że istnieją
        return df[cols].dropna(how='all').reset_index(drop=True)
    except Exception as e:
        st.warning(f"Zauważono brak struktury w arkuszu {ws}. Tworzę strukturę zastępczą.")
        return pd.DataFrame(columns=cols)

def save_now(df, ws_name):
    try:
        df_to_save = df.dropna(how='all').reset_index(drop=True)
        conn.update(worksheet=ws_name, data=df_to_save)
        st.cache_data.clear()
        st.toast(f"✅ Zapisano pomyślnie: {ws_name}")
    except Exception as e:
        st.error(f"Błąd zapisu arkusza {ws_name}. Upewnij się, że masz uprawnienia do edycji!")

# --- 4. INICJALIZACJA SESJI ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

STRUCT_PRZEPISY = ["Nazwa", "Skladnik", "Ilosc", "Kalorie", "Porcje"]
STRUCT_SPIZARNIA = ["Produkt", "Ilosc", "Czy_Stale", "Min_Ilosc"]
STRUCT_PLAN = ["Klucz", "Wybor", "Ile_Porcji"]

# Ładowanie danych do sesji
if 'przepisy' not in st.session_state: st.session_state.przepisy = safe_load("Przepisy", STRUCT_PRZEPISY)
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = safe_load("Spizarnia", STRUCT_SPIZARNIA)
if 'plan_df' not in st.session_state: st.session_state.plan_df = safe_load("Plan", STRUCT_PLAN)

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
miesiace_pl = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]

# --- 5. RENDEROWANIE ---

# --- PAGE: HOME ---
if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"<div class='day-banner'><h1>{dni_pl[teraz.weekday()]}</h1><p>{teraz.day} {miesiace_pl[teraz.month-1]} {teraz.year}</p></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("📅\nPLAN", use_container_width=True, type="primary"): st.session_state.page = "Plan"; st.rerun()
    if c2.button("🏠\nSPIŻARNIA", use_container_width=True): st.session_state.page = "Spizarnia"; st.rerun()
    if c3.button("📖\nPRZEPISY", use_container_width=True): st.session_state.page = "Dodaj"; st.rerun()
    if c4.button("🛒\nZAKUPY", use_container_width=True): st.session_state.page = "Zakupy"; st.rerun()

# --- PAGE: PLANOWANIE ---
elif st.session_state.page == "Plan":
    st.subheader("📅 Planowanie tygodnia")
    c_back, c_nav, c_save = st.columns([1, 2, 1])
    
    if c_back.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    with c_nav:
        n1, n2, n3 = st.columns(3)
        if n1.button("◀"): st.session_state.week_offset -= 1; st.rerun()
        if n2.button("Dziś"): st.session_state.week_offset = 0; st.rerun()
        if n3.button("▶"): st.session_state.week_offset += 1; st.rerun()
    if c_save.button("💾 ZAPISZ PLAN", type="primary"): save_now(st.session_state.plan_df, "Plan")

    start_date = datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)
    week_id = start_date.strftime("%Y-%V")

    for i, dzien in enumerate(dni_pl):
        with st.expander(f"{dzien} ({(start_date + timedelta(days=i)).strftime('%d.%m')})"):
            suma_kcal_dnia = 0
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{week_id}_{dzien}_{typ}"
                
                # Bezpieczne pobranie wartości z plan_df
                mask = st.session_state.plan_df['Klucz'] == k
                istn = st.session_state.plan_df[mask]
                
                w_istn = istn['Wybor'].values[0] if not istn.empty else "Brak"
                p_istn = to_num(istn['Ile_Porcji'].values[0]) if not istn.empty else 0
                
                opcje = ["Brak"] + sorted([p for p in st.session_state.przepisy['Nazwa'].unique().tolist() if str(p).strip()])
                
                c_sel, c_por = st.columns([3, 1])
                wyb = c_sel.selectbox(f"{typ}:", opcje, index=opcje.index(w_istn) if w_istn in opcje else 0, key=f"sel_{k}")
                
                current_p = 0
                if wyb != "Brak":
                    przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wyb]
                    # Ile porcji przewiduje baza przepisu (domyślnie 1)
                    p_baza = max(1.0, to_num(przepis['Porcje'].iloc[0]) if not przepis.empty else 1.0)
                    
                    # Jeśli nie mamy nic w planie, podpowiadamy bazę z przepisu
                    p_val = p_istn if p_istn > 0 else p_baza
                    current_p = c_por.number_input("Porcje", 0.5, 20.0, float(p_val), 0.5, key=f"p_{k}")
                    
                    mnoznik = current_p / p_baza
                    
                    st.markdown("<div class='portion-box'>", unsafe_allow_html=True)
                    for _, r in przepis.iterrows():
                        s_nazwa = str(r['Skladnik']).lower().strip()
                        potrzeba = round(to_num(r['Ilosc']) * mnoznik, 2)
                        mam = st.session_state.spizarnia_df[st.session_state.spizarnia_df['Produkt'].str.lower().str.strip() == s_nazwa]['Ilosc'].apply(to_num).sum()
                        
                        if mam < potrzeba:
                            st.markdown(f"<div class='missing-item'>❌ {r['Skladnik']}: {potrzeba} (brakuje: {round(potrzeba-mam, 2)})</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='have-item'>✅ {r['Skladnik']}: {potrzeba} (mam: {mam})</div>", unsafe_allow_html=True)
                    
                    kcal_skalowane = (to_num(przepis['Kalorie'].iloc[0]) / p_baza) * current_p
                    suma_kcal_dnia += kcal_skalowane
                    st.markdown("</div>", unsafe_allow_html=True)

                # Logika aktualizacji planu
                if (wyb != w_istn) or (current_p != p_istn):
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    if wyb != "Brak":
                        new_row = pd.DataFrame([{"Klucz": k, "Wybor": wyb, "Ile_Porcji": current_p}])
                        st.session_state.plan_df = pd.concat([st.session_state.plan_df, new_row], ignore_index=True)

            if suma_kcal_dnia > 0:
                st.markdown(f"<p class='kcal-tag'>🔥 Razem: {int(suma_kcal_dnia)} kcal</p>", unsafe_allow_html=True)

# --- PAGE: SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    st.subheader("🏠 Spiżarnia")
    c1, c2 = st.columns(2)
    if c1.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    if c2.button("💾 ZAPISZ STAN", type="primary"): save_now(st.session_state.spizarnia_df, "Spizarnia")
    
    with st.expander("➕ NOWY PRODUKT"):
        with st.form("f_add", clear_on_submit=True):
            c_n, c_q, c_s, c_m = st.columns([2, 1, 1, 1])
            n = c_n.text_input("Nazwa")
            q = c_q.number_input("Ilość", 0.0)
            s = c_s.checkbox("Stały?")
            m = c_m.number_input("Min.", 0.0)
            if st.form_submit_button("Dodaj"):
                if n:
                    st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}])], ignore_index=True)
                    st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        st.session_state.spizarnia_df.at[idx, 'Ilosc'] = c2.number_input("Q", to_num(row['Ilosc']), key=f"q_{idx}", label_visibility="collapsed")
        is_s = str(row['Czy_Stale']).upper() == 'TAK'
        new_s = c3.checkbox("📌", value=is_s, key=f"s_{idx}")
        st.session_state.spizarnia_df.at[idx, 'Czy_Stale'] = "TAK" if new_s else "NIE"
        st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = c4.number_input("M", to_num(row['Min_Ilosc']), key=f"m_{idx}", label_visibility="collapsed") if new_s else 0.0
        if c5.button("🗑️", key=f"d_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True); st.rerun()

# --- PAGE: PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.subheader("📖 Przepisy")
    if st.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("➕ NOWY PRZEPIS"):
        n_p = st.text_input("Nazwa potrawy")
        n_k = st.number_input("Kaloryczność (suma)", 0)
        n_po = st.number_input("Dla ilu porcji", 1, min_value=1)
        if st.button("Utwórz"):
            if n_p:
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": n_p, "Skladnik": "Składnik", "Ilosc": 0, "Kalorie": n_k, "Porcje": n_po}])], ignore_index=True)
                st.rerun()

    if not st.session_state.przepisy.empty:
        with st.expander("📝 EDYCJA PRZEPISÓW"):
            wyb_p = st.selectbox("Wybierz:", sorted(st.session_state.przepisy['Nazwa'].unique()))
            mask = st.session_state.przepisy['Nazwa'] == wyb_p
            
            ck, cp = st.columns(2)
            st.session_state.przepisy.loc[mask, 'Kalorie'] = ck.number_input("Kalorie:", value=int(to_num(st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0])))
            st.session_state.przepisy.loc[mask, 'Porcje'] = cp.number_input("Porcje bazowe:", value=int(to_num(st.session_state.przepisy.loc[mask, 'Porcje'].iloc[0])))
            
            for idx, row in st.session_state.przepisy[mask].iterrows():
                c1, c2, c3 = st.columns([3, 1, 0.5])
                st.session_state.przepisy.at[idx, 'Skladnik'] = c1.text_input("S", row['Skladnik'], key=f"ps_{idx}", label_visibility="collapsed")
                st.session_state.przepisy.at[idx, 'Ilosc'] = c2.number_input("I", to_num(row['Ilosc']), key=f"pi_{idx}", label_visibility="collapsed")
                if c3.button("🗑️", key=f"pd_{idx}"):
                    st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True); st.rerun()
            
            if st.button("➕ Dodaj składnik"):
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb_p, "Skladnik": "", "Ilosc": 0, "Kalorie": st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0], "Porcje": st.session_state.przepisy.loc[mask, 'Porcje'].iloc[0]}])], ignore_index=True); st.rerun()
            if st.button("💾 ZAPISZ PRZEPIS", type="primary"): save_now(st.session_state.przepisy, "Przepisy")

# --- PAGE: ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Zakupy")
    if st.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    
    wid = (datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)).strftime("%Y-%V")
    needs = {}
    
    # Zbieranie potrzeb z planu
    plan = st.session_state.plan_df[st.session_state.plan_df['Klucz'].str.contains(wid, na=False)]
    for _, row_p in plan.iterrows():
        potrawa = row_p['Wybor']
        ile_chce = to_num(row_p['Ile_Porcji'])
        if potrawa != "Brak":
            skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == potrawa]
            p_baza = max(1.0, to_num(skladniki['Porcje'].iloc[0]) if not skladniki.empty else 1.0)
            mnoznik = ile_chce / p_baza
            for _, r in skladniki.iterrows():
                s_name = str(r['Skladnik']).lower().strip()
                if s_name: needs[s_name] = needs.get(s_name, 0) + (to_num(r['Ilosc']) * mnoznik)
    
    lista = []
    # Sprawdzanie spiżarni i produktów stałych
    for _, r in st.session_state.spizarnia_df.iterrows():
        p_name = str(r['Produkt']).lower().strip()
        mam = to_num(r['Ilosc'])
        min_w = to_num(r['Min_Ilosc']) if str(r['Czy_Stale']).upper() == "TAK" else 0
        wymagane = max(needs.get(p_name, 0), min_w)
        if wymagane > mam:
            lista.append({"Produkt": p_name.capitalize(), "Kupić": round(wymagane - mam, 2), "W domu": mam})
        if p_name in needs: del needs[p_name]
    
    # Rzeczy z planu, których nie ma w ogóle w spiżarni
    for s_name, ile in needs.items():
        if ile > 0: lista.append({"Produkt": s_name.capitalize(), "Kupić": round(ile, 2), "W domu": 0})

    if lista:
        st.table(pd.DataFrame(lista))
        tekst = "LISTA ZAKUPÓW\n" + "\n".join([f"☐ {b['Produkt']}: {b['Kupić']}" for b in lista])
        st.download_button("📥 Pobierz listę", tekst, file_name="zakupy.txt", use_container_width=True)
    else: st.success("Wszystko masz! 🎉")
