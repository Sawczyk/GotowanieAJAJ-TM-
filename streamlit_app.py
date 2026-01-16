import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import re

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Inteligentny Planer Kuchni", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. SILNIK OBLICZENIOWY ---
def wyciagnij_liczbe(tekst):
    match = re.search(r"(\d+[\.,]?\d*)", str(tekst))
    if match:
        return float(match.group(1).replace(',', '.'))
    return 0

def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def save_data(df, worksheet_name):
    df = df.dropna(how='all')
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# --- 3. INICJALIZACJA SESJI ---
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia_df' not in st.session_state:
    st.session_state.spizarnia_df = get_data("Spizarnia")
if 'plan_df' not in st.session_state:
    st.session_state.plan_df = get_data("Plan")
if 'page' not in st.session_state:
    st.session_state.page = "Home"
if 'week_offset' not in st.session_state:
    st.session_state.week_offset = 0

def get_week_dates(offset):
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [(start_of_week + timedelta(days=i)) for i in range(7)]

def analizuj_zapasy_tygodniowe():
    potrzeby_suma = {}
    dni_tygodnia = get_week_dates(st.session_state.week_offset)
    # Tworzymy listę kluczy dla całego wybranego tygodnia
    tydzien_id = dni_tygodnia[0].strftime("%Y-%V")
    
    if st.session_state.plan_df.empty: return {}

    plan_tydzien = st.session_state.plan_df[st.session_state.plan_df['Klucz'].str.contains(tydzien_id)]

    for wybor in plan_tydzien['Wybor']:
        if wybor != "Brak":
            przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wybor]
            if not przepis.empty:
                skladniki = [s.strip() for s in str(przepis.iloc[0]['Skladniki']).split(',')]
                for s in skladniki:
                    nazwa = s.split('(')[0].strip().lower()
                    ilosc = wyciagnij_liczbe(s)
                    potrzeby_suma[nazwa] = potrzeby_suma.get(nazwa, 0) + ilosc

    magazyn = {}
    if not st.session_state.spizarnia_df.empty:
        for _, row in st.session_state.spizarnia_df.iterrows():
            magazyn[str(row['Produkt']).lower()] = wyciagnij_liczbe(row['Ilosc'])

    bilans = {}
    for nazwa, potrzebna_ilosc in potrzeby_suma.items():
        stan_w_domu = magazyn.get(nazwa, 0)
        brakuje = max(0, potrzebna_ilosc - stan_w_domu)
        bilans[nazwa] = {"potrzeba": potrzebna_ilosc, "mam": stan_w_domu, "brakuje": brakuje}
    return bilans

# --- 4. NAWIGACJA HOME ---
if st.session_state.page == "Home":
    st.title("🍴 Inteligentny System Kuchni")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📅 PLANOWANIE", use_container_width=True): st.session_state.page = "Plan"; st.rerun()
        if st.button("🏠 SPIŻARNIA", use_container_width=True): st.session_state.page = "Spizarnia"; st.rerun()
    with c2:
        if st.button("➕ DODAJ PRZEPIS", use_container_width=True): st.session_state.page = "Dodaj"; st.rerun()
        if st.button("🛒 ZAKUPY", use_container_width=True): st.session_state.page = "Zakupy"; st.rerun()
# --- 5. MODUŁ: PLANOWANIE ---
elif st.session_state.page == "Plan":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    # Nawigacja tygodniami
    cp, cc, cn = st.columns([1, 2, 1])
    if cp.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    if cn.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()
    
    dni = get_week_dates(st.session_state.week_offset)
    tydzien_id = dni[0].strftime("%Y-%V")
    st.subheader(f"Tydzień {tydzien_id} ({dni[0].strftime('%d.%m')} - {dni[-1].strftime('%d.%m')})")

    # Sekcja inteligentnego liczenia jajek/składników
    with st.expander("📊 ANALIZA ZAPASÓW NA TEN TYDZIEN", expanded=True):
        bilans = analizuj_zapasy_tygodniowe()
        if bilans:
            for prod, d in bilans.items():
                if d['brakuje'] > 0:
                    st.error(f"❌ **{prod.capitalize()}**: Potrzebujesz {d['potrzeba']}, masz {d['mam']}. **DOKUP: {d['brakuje']}**")
                else:
                    st.success(f"✅ **{prod.capitalize()}**: Masz {d['mam']} (potrzeba {d['potrzeba']})")
        else:
            st.info("Brak zaplanowanych posiłków w tym tygodniu.")

    # Wybór dań
    DNI_N = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    for i, d_obj in enumerate(dni):
        with st.expander(f"{DNI_N[i]} ({d_obj.strftime('%d.%m')})"):
            for p_typ in ["Śniadanie", "Lunch", "Kolacja"]:
                klucz = f"{tydzien_id}_{DNI_N[i]}_{p_typ}"
                istn = "Brak"
                if not st.session_state.plan_df.empty and 'Klucz' in st.session_state.plan_df.columns:
                    m = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == klucz]
                    if not m.empty: istn = m.iloc[0]['Wybor']

                opcje = ["Brak"] + st.session_state.przepisy['Nazwa'].tolist() if not st.session_state.przepisy.empty else ["Brak"]
                wybor = st.selectbox(f"{p_typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=klucz)
                
                if wybor != istn:
                    df_p = st.session_state.plan_df
                    if df_p.empty or 'Klucz' not in df_p.columns: df_p = pd.DataFrame(columns=['Klucz', 'Wybor'])
                    df_p = df_p[df_p['Klucz'] != klucz]
                    df_p = pd.concat([df_p, pd.DataFrame([{"Klucz": klucz, "Wybor": wybor}])], ignore_index=True)
                    st.session_state.plan_df = df_p
                    save_data(df_p, "Plan")
                    st.rerun()

# --- 6. MODUŁ: SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.header("🏠 Stan Magazynowy")
    st.info("W kolumnie 'Ilosc' wpisuj same liczby (np. 10), aby aplikacja mogła liczyć braki.")
    
    df_s = st.session_state.spizarnia_df
    if df_s.empty: df_s = pd.DataFrame(columns=['Produkt', 'Ilosc'])
    
    edytowany = st.data_editor(df_s, num_rows="dynamic", use_container_width=True, key="edit_spiz")
    if st.button("ZAPISZ ZMIANY W SPIŻARNI"):
        st.session_state.spizarnia_df = edytowany
        save_data(edytowany, "Spizarnia")
        st.success("Zapisano!")

# --- 7. MODUŁ: DODAJ PRZEPIS ---
elif st.session_state.page == "Dodaj":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.header("➕ Nowy Przepis")
    with st.form("f_przepis"):
        n = st.text_input("Nazwa dania")
        t = st.selectbox("Typ", ["Śniadanie", "Lunch", "Kolacja"])
        s = st.text_area("Składniki w formacie: Nazwa (Liczba), np: Jajka (3), Mleko (0.5)")
        if st.form_submit_button("ZAPISZ PRZEPIS"):
            if n and s:
                nowy = pd.DataFrame([{"Nazwa": n, "Typ": t, "Skladniki": s}])
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, nowy], ignore_index=True)
                save_data(st.session_state.przepisy, "Przepisy")
                st.success("Dodano!")

# --- 8. MODUŁ: ZAKUPY ---
elif st.session_state.page == "Zakupy":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.header("🛒 Lista Zakupów")
    
    bilans = analizuj_zapasy_tygodniowe()
    braki = {k: v for k, v in bilans.items() if v['brakuje'] > 0}
    
    if braki:
        st.write("Produkty do dokupienia na ten tydzień:")
        dane_tabeli = []
        for p, d in braki.items():
            st.checkbox(f"{p.capitalize()} - dokup: {d['brakuje']}", key=f"z_{p}")
            dane_tabeli.append(f"{p}: {d['brakuje']}")
        
        st.download_button("Pobierz listę", "\n".join(dane_tabeli), "zakupy.txt")
    else:
        st.success("Masz wszystko, czego potrzebujesz na ten tydzień!")
