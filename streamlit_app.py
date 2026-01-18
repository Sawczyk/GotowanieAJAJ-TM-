import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import google.generativeai as genai
from PIL import Image
import json

# --- 1. KONFIGURACJA API AI (Klucz zapisany w sesji/kodzie) ---
API_KEY = "AIzaSyAWT1RNxAFrH-HiX5_FQNAz3ToYyzY4Nho" 
genai.configure(api_key=API_KEY)

# --- 2. KONFIGURACJA I ESTETYCZNA STYLIZACJA ---
st.set_page_config(page_title="Planer Kuchni AI", page_icon="🍳", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; }
    
    .day-banner { 
        background-color: #2E7D32; color: white; padding: 25px; border-radius: 15px; 
        text-align: center; margin-bottom: 30px; box-shadow: 0 4px 15px rgba(46,125,50,0.2); 
    }
    .day-banner h1 { margin: 0; font-size: 2.5rem; font-weight: 600; }
    
    div.stButton > button { border-radius: 12px; font-weight: 600 !important; transition: 0.3s; }
    div.stButton > button[kind="primary"] { background-color: #2E7D32 !important; color: white !important; height: 60px !important; width: 100% !important; }
    
    .portion-box { background: #fdfdfd; padding: 15px; border-radius: 12px; margin-bottom: 15px; border: 1px solid #eee; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }
    .missing-item { color: #d32f2f; font-size: 0.85rem; padding: 6px 12px; border-left: 3px solid #d32f2f; background: #fff5f5; margin: 4px 0; border-radius: 4px; }
    .have-item { color: #2E7D32; font-size: 0.85rem; padding: 6px 12px; border-left: 3px solid #2E7D32; background: #f1f8e9; margin: 4px 0; border-radius: 4px; }
    .scan-preview { background: #f1f8e9; padding: 20px; border-radius: 12px; border: 2px dashed #2e7d32; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNKCJE POMOCNICZE ---
def to_num(val):
    try: 
        if pd.isna(val) or str(val).strip() == "": return 0.0
        return float(str(val).replace(',', '.').strip())
    except: return 0.0

conn = st.connection("gsheets", type=GSheetsConnection)

def safe_load(ws, cols):
    try:
        df = conn.read(worksheet=ws, ttl=0)
        if df is None: df = pd.DataFrame(columns=cols)
        df.columns = [str(c).strip() for c in df.columns]
        for c in cols:
            if c not in df.columns:
                df[c] = 1.0 if c in ["Porcje", "Ile_Porcji"] else (0.0 if c in ["Kalorie", "Min_Ilosc", "Ilosc"] else "")
        return df[cols].dropna(how='all').reset_index(drop=True)
    except: return pd.DataFrame(columns=cols)

def save_now(df, ws_name):
    try:
        df_to_save = df.dropna(how='all').reset_index(drop=True)
        conn.update(worksheet=ws_name, data=df_to_save)
        st.cache_data.clear()
        st.toast(f"✅ Zapisano: {ws_name}")
    except: st.error(f"Błąd zapisu {ws_name}")

def analyze_recipe_image(uploaded_file):
    model = genai.GenerativeModel('gemini-1.5-flash')
    img = Image.open(uploaded_file)
    prompt = """Przeanalizuj to zdjęcie i zwróć JSON: {"Nazwa": str, "Kalorie": float, "Porcje": float, "Skladniki": [{"Skladnik": str, "Ilosc": float}]}. Zwróć tylko czysty JSON."""
    response = model.generate_content([prompt, img])
    try:
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except: return None

# --- 4. SESJA I DANE ---
if 'page' not in st.session_state: st.session_state.page = "Home"
if 'week_offset' not in st.session_state: st.session_state.week_offset = 0

STRUCT_PRZEPISY = ["Nazwa", "Skladnik", "Ilosc", "Kalorie", "Porcje"]
STRUCT_SPIZARNIA = ["Produkt", "Ilosc", "Czy_Stale", "Min_Ilosc"]
STRUCT_PLAN = ["Klucz", "Wybor", "Ile_Porcji"]

if 'przepisy' not in st.session_state: st.session_state.przepisy = safe_load("Przepisy", STRUCT_PRZEPISY)
if 'spizarnia_df' not in st.session_state: st.session_state.spizarnia_df = safe_load("Spizarnia", STRUCT_SPIZARNIA)
if 'plan_df' not in st.session_state: st.session_state.plan_df = safe_load("Plan", STRUCT_PLAN)

dni_pl = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]

# --- 5. RENDEROWANIE ---

# --- PAGE: HOME ---
if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"<div class='day-banner'><h1>{dni_pl[teraz.weekday()]}</h1><p>{teraz.strftime('%d.%m.%Y')}</p></div>", unsafe_allow_html=True)
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
            suma_kcal = 0.0
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{week_id}_{dzien}_{typ}"
                row_p = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]
                w_istn = row_p['Wybor'].values[0] if not row_p.empty else "Brak"
                p_istn = to_num(row_p['Ile_Porcji'].values[0]) if not row_p.empty else 0.0
                
                opcje = ["Brak"] + sorted(st.session_state.przepisy['Nazwa'].unique().tolist())
                c_sel, c_por = st.columns([3, 1])
                wyb = c_sel.selectbox(f"{typ}:", opcje, index=opcje.index(w_istn) if w_istn in opcje else 0, key=f"sel_{k}")
                
                cur_p = 0.0
                if wyb != "Brak":
                    przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wyb]
                    p_baza = max(1.0, to_num(przepis['Porcje'].iloc[0]))
                    cur_p = c_por.number_input("Porcje", 0.5, 20.0, float(p_istn if p_istn > 0 else p_baza), 0.5, key=f"num_{k}")
                    
                    mnoznik = cur_p / p_baza
                    st.markdown("<div class='portion-box'>", unsafe_allow_html=True)
                    for _, r in przepis.iterrows():
                        ile_skal = round(to_num(r['Ilosc']) * mnoznik, 2)
                        mam = st.session_state.spizarnia_df[st.session_state.spizarnia_df['Produkt'].str.lower() == str(r['Skladnik']).lower()]['Ilosc'].apply(to_num).sum()
                        if mam < ile_skal:
                            st.markdown(f"<div class='missing-item'>❌ {r['Skladnik']}: {ile_skal} (brakuje: {round(ile_skal-mam, 2)})</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div class='have-item'>✅ {r['Skladnik']}: {ile_skal} (mam: {mam})</div>", unsafe_allow_html=True)
                    kcal_skal = (to_num(przepis['Kalorie'].iloc[0]) / p_baza) * cur_p
                    suma_kcal += kcal_skal
                    st.markdown("</div>", unsafe_allow_html=True)

                if (wyb != w_istn) or (cur_p != p_istn):
                    st.session_state.plan_df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    if wyb != "Brak":
                        st.session_state.plan_df = pd.concat([st.session_state.plan_df, pd.DataFrame([{"Klucz": k, "Wybor": wyb, "Ile_Porcji": cur_p}])], ignore_index=True)
            if suma_kcal > 0: st.markdown(f"**🔥 Razem: {int(suma_kcal)} kcal**")

# --- PAGE: SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    st.subheader("🏠 Spiżarnia")
    c1, c2 = st.columns(2)
    if c1.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    if c2.button("💾 ZAPISZ STAN", type="primary"): save_now(st.session_state.spizarnia_df, "Spizarnia")
    
    with st.expander("➕ DODAJ PRODUKT"):
        with st.form("add_p", clear_on_submit=True):
            cn, cq, cs, cm = st.columns([2, 1, 1, 1])
            n = cn.text_input("Nazwa")
            q = cq.number_input("Ilość", 0.0)
            s = cs.checkbox("Stały?")
            m = cm.number_input("Min.", 0.0)
            if st.form_submit_button("Dodaj"):
                if n:
                    st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": n, "Ilosc": q, "Czy_Stale": "TAK" if s else "NIE", "Min_Ilosc": m}])], ignore_index=True); st.rerun()

    for idx, row in st.session_state.spizarnia_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1, 1, 0.5])
        c1.write(f"**{row['Produkt']}**")
        st.session_state.spizarnia_df.at[idx, 'Ilosc'] = c2.number_input("Q", to_num(row['Ilosc']), key=f"q_{idx}", label_visibility="collapsed")
        is_s = str(row['Czy_Stale']).upper() == 'TAK'
        new_s = c3.checkbox("📌", value=is_s, key=f"st_{idx}")
        st.session_state.spizarnia_df.at[idx, 'Czy_Stale'] = "TAK" if new_s else "NIE"
        st.session_state.spizarnia_df.at[idx, 'Min_Ilosc'] = c4.number_input("M", to_num(row['Min_Ilosc']), key=f"min_{idx}", label_visibility="collapsed") if new_s else 0.0
        if c5.button("🗑️", key=f"del_{idx}"):
            st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True); st.rerun()

# --- PAGE: PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.subheader("📖 Biblioteka Przepisów")
    if st.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    
    with st.expander("📸 SKANUJ PRZEPIS (OCR AI)", expanded=False):
        f = st.file_uploader("Zdjęcie przepisu", type=['jpg', 'png', 'jpeg'])
        if f and st.button("Analizuj ✨"):
            with st.spinner("AI czyta..."):
                res = analyze_recipe_image(f)
                if res: st.session_state.temp_recipe = res
        
        if 'temp_recipe' in st.session_state:
            tr = st.session_state.temp_recipe
            st.markdown("<div class='scan-preview'>", unsafe_allow_html=True)
            st.write(f"### {tr['Nazwa']} (🔥 {tr['Kalorie']} kcal | 🍽 {tr['Porcje']} porcji)")
            st.table(pd.DataFrame(tr['Skladniki']))
            if st.button("✅ ZATWIERDŹ I DODAJ"):
                for s in tr['Skladniki']:
                    st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": tr['Nazwa'], "Skladnik": s['Skladnik'], "Ilosc": to_num(s['Ilosc']), "Kalorie": to_num(tr['Kalorie']), "Porcje": to_num(tr['Porcje'])}])], ignore_index=True)
                save_now(st.session_state.przepisy, "Przepisy")
                del st.session_state.temp_recipe; st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("➕ RĘCZNE DODAWANIE"):
        np = st.text_input("Nazwa potrawy")
        pk = st.number_input("Kalorie całości", value=0.0)
        pp = st.number_input("Porcje bazowe", value=1.0)
        if st.button("Stwórz"):
            if np:
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": np, "Skladnik": "Składnik", "Ilosc": 0.0, "Kalorie": pk, "Porcje": pp}])], ignore_index=True); st.rerun()

    if not st.session_state.przepisy.empty:
        with st.expander("📝 EDYCJA"):
            wyb = st.selectbox("Wybierz potrawę:", sorted(st.session_state.przepisy['Nazwa'].unique()))
            mask = st.session_state.przepisy['Nazwa'] == wyb
            st.session_state.przepisy.loc[mask, 'Kalorie'] = st.number_input("Kalorie:", value=float(to_num(st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0])))
            st.session_state.przepisy.loc[mask, 'Porcje'] = st.number_input("Porcje:", value=float(to_num(st.session_state.przepisy.loc[mask, 'Porcje'].iloc[0])))
            for idx, row in st.session_state.przepisy[mask].iterrows():
                c1, c2, c3 = st.columns([3, 1, 0.5])
                st.session_state.przepisy.at[idx, 'Skladnik'] = c1.text_input("S", row['Skladnik'], key=f"ps_{idx}")
                st.session_state.przepisy.at[idx, 'Ilosc'] = c2.number_input("I", value=float(to_num(row['Ilosc'])), key=f"pi_{idx}")
                if c3.button("🗑️", key=f"pd_{idx}"): st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True); st.rerun()
            if st.button("➕ Składnik"):
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": wyb, "Skladnik": "", "Ilosc": 0.0, "Kalorie": st.session_state.przepisy.loc[mask, 'Kalorie'].iloc[0], "Porcje": st.session_state.przepisy.loc[mask, 'Porcje'].iloc[0]}])], ignore_index=True); st.rerun()
            if st.button("💾 ZAPISZ"): save_now(st.session_state.przepisy, "Przepisy")

# --- PAGE: ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.subheader("🛒 Lista Zakupów")
    if st.button("⬅ Menu"): st.session_state.page = "Home"; st.rerun()
    wid = (datetime.now() - timedelta(days=datetime.now().weekday()) + timedelta(weeks=st.session_state.week_offset)).strftime("%Y-%V")
    needs = {}
    plan = st.session_state.plan_df[st.session_state.plan_df['Klucz'].str.contains(wid, na=False)]
    for _, rp in plan.iterrows():
        p_name = rp['Wybor']
        if p_name != "Brak":
            skladniki = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == p_name]
            p_baza = max(1.0, to_num(skladniki['Porcje'].iloc[0]) if not skladniki.empty else 1.0)
            mnoznik = to_num(rp['Ile_Porcji']) / p_baza
            for _, r in skladniki.iterrows():
                s = str(r['Skladnik']).lower().strip()
                if s: needs[s] = needs.get(s, 0) + (to_num(r['Ilosc']) * mnoznik)
    
    lista = []
    for _, r in st.session_state.spizarnia_df.iterrows():
        name = str(r['Produkt']).lower().strip()
        mam = to_num(r['Ilosc'])
        wym = max(needs.get(name, 0), to_num(r['Min_Ilosc']) if str(r['Czy_Stale']).upper()=="TAK" else 0)
        if wym > mam: lista.append({"Produkt": name.capitalize(), "Kupić": round(wym - mam, 2)})
        if name in needs: del needs[name]
    for n, q in needs.items():
        if q > 0: lista.append({"Produkt": n.capitalize(), "Kupić": round(q, 2)})
    
    if lista:
        st.table(pd.DataFrame(lista))
        st.download_button("📥 Pobierz TXT", "ZAKUPY\n"+"\n".join([f"☐ {b['Produkt']}: {b['Kupić']}" for b in lista]), "zakupy.txt", use_container_width=True)
    else: st.success("Wszystko masz! 🎉")
