import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Planer Inteligentny PRO", layout="wide", initial_sidebar_state="collapsed")

# Połączenie z Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. FUNKCJE DANYCH (ODCZYT/ZAPIS) ---
def get_data(worksheet_name):
    try:
        # ttl=0 wymusza pobranie świeżych danych przy każdym przeładowaniu
        return conn.read(worksheet=worksheet_name, ttl=0)
    except:
        return pd.DataFrame()

def save_data(df, worksheet_name):
    # Czyścimy puste wiersze przed zapisem
    df = df.dropna(how='all')
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# Załaduj dane do sesji (cache tymczasowy dla szybkości)
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia' not in st.session_state:
    df_spiz = get_data("Spizarnia")
    st.session_state.spizarnia = df_spiz['Produkt'].tolist() if (not df_spiz.empty and 'Produkt' in df_spiz.columns) else []
if 'plan_df' not in st.session_state:
    st.session_state.plan_df = get_data("Plan")
if 'page' not in st.session_state:
    st.session_state.page = "Home"

# --- 3. LOGIKA POMOCNICZA ---
DNI = {0: "Poniedziałek", 1: "Wtorek", 2: "Środa", 3: "Czwartek", 4: "Piątek", 5: "Sobota", 6: "Niedziela"}

def sprawdz_skladniki(danie_nazwa):
    if not danie_nazwa or danie_nazwa == "Brak" or st.session_state.przepisy.empty: 
        return None
    przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == danie_nazwa]
    if przepis.empty: 
        return None
    wymagane = [s.strip().lower() for s in str(przepis.iloc[0]['Skladniki']).split(',')]
    mam = [s for s in wymagane if s in st.session_state.spizarnia]
    brak = [s for s in wymagane if s not in st.session_state.spizarnia]
    return {"mam": mam, "brak": brak}

# --- 4. NAWIGACJA (HOME) ---
if st.session_state.page == "Home":
    st.title("🍴 Mój Inteligentny Planer")
    st.info("Dane są synchronizowane z Twoim arkuszem Google Sheets.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📅 MÓJ PLAN"): st.session_state.page = "Plan"; st.rerun()
        if st.button("🏠 MOJA SPIŻARNIA"): st.session_state.page = "Spizarnia"; st.rerun()
    with c2:
        if st.button("➕ DODAJ PRZEPIS"): st.session_state.page = "Dodaj"; st.rerun()
        if st.button("🛒 LISTA ZAKUPÓW"): st.session_state.page = "Zakupy"; st.rerun()

# --- 5. MODUŁ: PLANOWANIE ---
elif st.session_state.page == "Plan":
    if st.button("⬅ POWRÓT DO MENU"): st.session_state.page = "Home"; st.rerun()
    st.header("Planowanie na 7 dni")
    
    for i in range(7):
        data = datetime.now() + timedelta(days=i)
        data_str = data.strftime("%Y-%m-%d")
        naglowek = f"{DNI[data.weekday()]} ({data_str})"
        
        with st.expander(naglowek, expanded=(i==0)):
            for p_typ in ["Śniadanie", "Lunch", "Kolacja"]:
                klucz = f"{data_str}_{p_typ}"
                
                istniejacy_wybor = "Brak"
                if not st.session_state.plan_df.empty and 'Klucz' in st.session_state.plan_df.columns:
                    match = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == klucz]
                    if not match.empty:
                        istniejacy_wybor = match.iloc[0]['Wybor']

                opcje = ["Brak"] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == p_typ]['Nazwa'].tolist() if not st.session_state.przepisy.empty else ["Brak"]
                
                wybor = st.selectbox(f"{p_typ}:", opcje, index=opcje.index(istniejacy_wybor) if istniejacy_wybor in opcje else 0, key=klucz)
                
                if wybor != istniejacy_wybor:
                    new_plan = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != klucz] if not st.session_state.plan_df.empty else pd.DataFrame(columns=['Klucz', 'Wybor'])
                    new_plan = pd.concat([new_plan, pd.DataFrame([{"Klucz": klucz, "Wybor": wybor}])], ignore_index=True)
                    st.session_state.plan_df = new_plan
                    save_data(new_plan, "Plan")
                    st.toast(f"Zapisano wybór: {wybor}")

                res = sprawdz_skladniki(wybor)
                if res:
                    col_m, col_b = st.columns(2)
                    if res['mam']: col_m.success(f"Mam: {', '.join(res['mam'])}")
                    if res['brak']: col_b.error(f"Kup: {', '.join(res['brak'])}")


# --- 6. MODUŁ: SPIŻARNIA ---
elif st.session_state.page == "Spizarnia":
    if st.button("⬅ POWRÓT DO MENU"): 
        st.session_state.page = "Home"
        st.rerun()
    
    st.header("Zarządzaj swoją spiżarnią")
    st.write("Dodaj produkty, które masz już w domu, aby aplikacja mogła je uwzględnić.")
    
    nowy_prod = st.text_input("Nazwa produktu (np. mąka, sól):").lower().strip()
    if st.button("DODAJ DO ZAPASÓW"):
        if nowy_prod and nowy_prod not in st.session_state.spizarnia:
            st.session_state.spizarnia.append(nowy_prod)
            # Zapisujemy do arkusza jako nową tabelę
            df_do_zapisu = pd.DataFrame({"Produkt": st.session_state.spizarnia})
            save_data(df_do_zapisu, "Spizarnia")
            st.success(f"Dodano: {nowy_prod}")
            st.rerun()

    st.divider()
    st.subheader("Produkty w Twoim domu (kliknij, aby usunąć):")
    if st.session_state.spizarnia:
        cols = st.columns(4)
        for idx, item in enumerate(sorted(st.session_state.spizarnia)):
            if cols[idx % 4].button(f"🗑️ {item}", key=f"inv_{item}"):
                st.session_state.spizarnia.remove(item)
                df_do_zapisu = pd.DataFrame({"Produkt": st.session_state.spizarnia})
                save_data(df_do_zapisu, "Spizarnia")
                st.rerun()
    else:
        st.info("Twoja spiżarnia jest pusta.")

# --- 7. MODUŁ: DODAJ PRZEPIS ---
elif st.session_state.page == "Dodaj":
    if st.button("⬅ POWRÓT DO MENU"): 
        st.session_state.page = "Home"
        st.rerun()
        
    st.header("Dodaj nowy przepis do bazy")
    with st.form("new_recipe_form"):
        n = st.text_input("Nazwa potrawy")
        t = st.selectbox("Typ posiłku", ["Śniadanie", "Lunch", "Kolacja"])
        s = st.text_area("Składniki (rozdzielone przecinkami, np: kurczak, ryż, curry)")
        
        if st.form_submit_button("ZAPISZ PRZEPIS W CHMURZE"):
            if n and s:
                nowy_row = pd.DataFrame([{"Nazwa": n, "Typ": t, "Skladniki": s.lower()}])
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, nowy_row], ignore_index=True)
                save_data(st.session_state.przepisy, "Przepisy")
                st.success(f"Przepis na '{n}' został zapisany!")
            else:
                st.error("Uzupełnij wszystkie pola!")

# --- 8. MODUŁ: LISTA ZAKUPÓW ---
elif st.session_state.page == "Zakupy":
    if st.button("⬅ POWRÓT DO MENU"): 
        st.session_state.page = "Home"
        st.rerun()
        
    st.header("Twoja inteligentna lista zakupów")
    
    brakujace_globalnie = []
    if not st.session_state.plan_df.empty:
        # Przeskanuj wszystkie zaplanowane posiłki
        for danie in st.session_state.plan_df['Wybor']:
            wynik = sprawdz_skladniki(danie)
            if wynik and wynik['brak']:
                brakujace_globalnie.extend(wynik['brak'])
    
    # Usuwamy duplikaty i sortujemy
    lista_final = sorted(list(set(brakujace_globalnie)))
    
    if lista_final:
        st.write("Tych składników brakuje Ci do zrealizowania planu:")
        for produkt in lista_final:
            st.checkbox(f"Kup: {produkt}", key=f"shop_{produkt}")
        
        st.download_button(
            label="Eksportuj listę do tekstu",
            data="\n".join(lista_final),
            file_name="lista_zakupow.txt",
            mime="text/plain"
        )
    else:
        st.success("Masz wszystko w spiżarni! Nie musisz nic kupować.")
