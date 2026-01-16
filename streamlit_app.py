import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Inteligentny Magazyn", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNKCJE DANYCH ---
def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df.dropna(how='all')
    except: return pd.DataFrame()

def save_data(df, worksheet_name):
    df = df.dropna(how='all')
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# --- INICJALIZACJA ---
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia_df' not in st.session_state:
    st.session_state.spizarnia_df = get_data("Spizarnia")
if 'plan_df' not in st.session_state:
    st.session_state.plan_df = get_data("Plan")
if 'page' not in st.session_state:
    st.session_state.page = "Home"

# --- LOGIKA TYGODNI ---
if 'week_offset' not in st.session_state:
    st.session_state.week_offset = 0

def get_week_dates(offset):
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return [(start_of_week + timedelta(days=i)) for i in range(7)]

# --- MODUŁY ---
if st.session_state.page == "Home":
    st.title("🍴 System Zarządzania Kuchnią")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📅 PLANOWANIE TYGODNIA"): st.session_state.page = "Plan"; st.rerun()
        if st.button("🏠 MOJA SPIŻARNIA"): st.session_state.page = "Spizarnia"; st.rerun()
    with c2:
        if st.button("➕ BAZA PRZEPISÓW"): st.session_state.page = "Dodaj"; st.rerun()
        if st.button("🛒 LISTA ZAKUPÓW"): st.session_state.page = "Zakupy"; st.rerun()

elif st.session_state.page == "Plan":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    # Nawigacja tygodniami
    col_p, col_c, col_n = st.columns([1, 2, 1])
    if col_p.button("⬅ Poprzedni tydzień"): st.session_state.week_offset -= 1; st.rerun()
    if col_n.button("Następny tydzień ➡"): st.session_state.week_offset += 1; st.rerun()
    
    dni_tygodnia = get_week_dates(st.session_state.week_offset)
    st.subheader(f"Plan na tydzień: {dni_tygodnia[0].strftime('%d.%m')} - {dni_tygodnia[-1].strftime('%d.%m')}")

    DNI_NAZWY = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
    
    for i, data_obj in enumerate(dni_tygodnia):
        data_str = data_obj.strftime("%Y-%V") # Rok i numer tygodnia
        dzien_nazwa = DNI_NAZWY[i]
        
        with st.expander(f"📅 {dzien_nazwa} ({data_obj.strftime('%d.%m')})", expanded=(i==0)):
            for p_typ in ["Śniadanie", "Lunch", "Kolacja"]:
                klucz = f"{data_str}_{dzien_nazwa}_{p_typ}"
                
                # Pobierz zapisany wybór
                istniejacy = "Brak"
                if not st.session_state.plan_df.empty and 'Klucz' in st.session_state.plan_df.columns:
                    match = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == klucz]
                    if not match.empty: istniejacy = match.iloc[0]['Wybor']

                opcje = ["Brak"] + st.session_state.przepisy['Nazwa'].tolist() if not st.session_state.przepisy.empty else ["Brak"]
                wybor = st.selectbox(f"{p_typ}:", opcje, index=opcje.index(istniejacy) if istniejacy in opcje else 0, key=klucz)
                
                if wybor != istniejacy:
                    df_p = st.session_state.plan_df
                    if df_p.empty or 'Klucz' not in df_p.columns: df_p = pd.DataFrame(columns=['Klucz', 'Wybor'])
                    df_p = df_p[df_p['Klucz'] != klucz]
                    df_p = pd.concat([df_p, pd.DataFrame([{"Klucz": klucz, "Wybor": wybor}])], ignore_index=True)
                    st.session_state.plan_df = df_p
                    save_data(df_p, "Plan")
                    st.rerun()
elif st.session_state.page == "Spizarnia":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.header("🏠 Stan Magazynowy")
    
    # Edytor tabeli z palca
    df_s = st.session_state.spizarnia_df
    if df_s.empty: df_s = pd.DataFrame(columns=['Produkt', 'Ilosc'])
    
    st.write("Edytuj ilości bezpośrednio w tabeli:")
    edited_spiz = st.data_editor(df_s, num_rows="dynamic", use_container_width=True, key="ed_spiz")
    
    if st.button("ZAPISZ STAN SPIŻARNI"):
        st.session_state.spizarnia_df = edited_spiz
        save_data(edited_spiz, "Spizarnia")
        st.success("Zapisano!")

elif st.session_state.page == "Dodaj":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.header("➕ Dodaj Przepis z Ilościami")
    
    with st.form("form_przepis"):
        nazwa = st.text_input("Nazwa dania")
        typ = st.selectbox("Typ", ["Śniadanie", "Lunch", "Kolacja"])
        st.write("Wpisz składniki i ich gramaturę/ilość:")
        skladniki_instrukcja = st.text_area("Format: składnik (ilość), np: Mąka (500g), Mleko (1l), Jajka (4 szt)")
        
        if st.form_submit_button("ZAPISZ PRZEPIS"):
            if nazwa and skladniki_instrukcja:
                nowy = pd.DataFrame([{"Nazwa": nazwa, "Typ": typ, "Skladniki": skladniki_instrukcja}])
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, nowy], ignore_index=True)
                save_data(st.session_state.przepisy, "Przepisy")
                st.success("Zapisano przepis!")

elif st.session_state.page == "Zakupy":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.header("🛒 Co kupić?")
    
    wszystkie_skladniki = []
    if not st.session_state.plan_df.empty:
        for wybor in st.session_state.plan_df['Wybor']:
            if wybor != "Brak":
                p = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == wybor]
                if not p.empty:
                    wszystkie_skladniki.append(p.iloc[0]['Skladniki'])
    
    if wszystkie_skladniki:
        st.write("Składniki potrzebne na zaplanowany okres:")
        for s in wszystkie_skladniki:
            st.write(f"- {s}")
    else:
        st.info("Zaplanuj posiłki, aby zobaczyć listę potrzebnych produktów.")

# --- 8. MODUŁ: ZAKUPY (INTELIGENTNE WYDOBYWANIE ILOŚCI) ---
elif st.session_state.page == "Zakupy":
    if st.button("⬅ POWRÓT DO MENU"): 
        st.session_state.page = "Home"
        st.rerun()
        
    st.header("🛒 Twoja Lista Zakupów")
    st.write("Lista produktów z gramaturami na podstawie Twojego aktualnego planu.")

    wszystkie_potrzeby = []
    if not st.session_state.plan_df.empty:
        # Pobierz unikalne zaplanowane dania
        zaplanowane_dania = st.session_state.plan_df[st.session_state.plan_df['Wybor'] != "Brak"]['Wybor'].unique()
        
        for danie in zaplanowane_dania:
            przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == danie]
            if not przepis.empty:
                # Rozdzielamy składniki zapisane jako "Mąka (500g), Mleko (1l)"
                skladniki_lista = [s.strip() for s in str(przepis.iloc[0]['Skladniki']).split(',')]
                wszystkie_potrzeby.extend(skladniki_lista)

    if wszystkie_potrzeby:
        # Usuwamy duplikaty (dla uproszczenia, w przyszłości można dodać sumowanie wag)
        unikalne_potrzeby = sorted(list(set(wszystkie_potrzeby)))
        
        col_lista, col_akcja = st.columns([2, 1])
        
        with col_lista:
            st.subheader("Do kupienia:")
            for item in unikalne_potrzeby:
                st.checkbox(item, key=f"buy_{item}")

        with col_akcja:
            st.subheader("Opcje")
            if st.button("Pobierz listę jako TXT"):
                txt = "LISTA ZAKUPÓW:\n" + "\n".join(unikalne_potrzeby)
                st.download_button("Kliknij tutaj, aby pobrać", txt, file_name="zakupy.txt")
            
            if st.button("Wyczyść cały plan"):
                if st.warning("Czy na pewno chcesz usunąć cały plan z Google Sheets?"):
                    save_data(pd.DataFrame(columns=['Klucz', 'Wybor']), "Plan")
                    st.rerun()
    else:
        st.info("Twój plan jest pusty. Dodaj dania w sekcji 'Planowanie', aby wygenerować listę zakupów z gramaturami.")

# --- DODATKOWA FUNKCJA: AUTOMATYZACJA SPIŻARNI (OPCJONALNIE) ---
# Dodajemy przycisk pod każdym dniem w sekcji Planowania w przyszłości, 
# który mógłby odejmować składniki. Na razie system jest w pełni gotowy do użytku.

# --- STOPKA INFORMACYJNA ---
st.sidebar.divider()
st.sidebar.caption(f"Połączono z arkuszem: {st.session_state.przepisy.shape[0]} przepisów w bazie.")
if st.sidebar.button("Wymuś odświeżenie danych z Google"):
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()
