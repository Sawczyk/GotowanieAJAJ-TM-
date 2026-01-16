import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Planer Inteligentny PRO", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(worksheet_name):
    try:
        df = conn.read(worksheet=worksheet_name, ttl=0)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

def save_data(df, worksheet_name):
    df = df.dropna(how='all')
    conn.update(worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# --- INICJALIZACJA ---
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = get_data("Przepisy")
if 'spizarnia_df' not in st.session_state:
    df_s = get_data("Spizarnia")
    if df_s.empty or 'Produkt' not in df_s.columns:
        df_s = pd.DataFrame(columns=['Produkt', 'Ilosc'])
    st.session_state.spizarnia_df = df_s
if 'plan_df' not in st.session_state:
    df_p = get_data("Plan")
    if df_p.empty or 'Klucz' not in df_p.columns:
        df_p = pd.DataFrame(columns=['Klucz', 'Wybor'])
    st.session_state.plan_df = df_p

if 'page' not in st.session_state:
    st.session_state.page = "Home"

# Pomocnicza funkcja sprawdzania (uproszczona pod kątem nazw)
def sprawdz_skladniki(danie_nazwa):
    if not danie_nazwa or danie_nazwa == "Brak" or st.session_state.przepisy.empty: 
        return None
    przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == danie_nazwa]
    if przepis.empty: return None
    
    wymagane = [s.strip().lower() for s in str(przepis.iloc[0]['Skladniki']).split(',')]
    zapasy = st.session_state.spizarnia_df['Produkt'].str.lower().tolist()
    
    mam = [s for s in wymagane if s in zapasy]
    brak = [s for s in wymagane if s not in zapasy]
    return {"mam": mam, "brak": brak}

# --- MENU ---
if st.session_state.page == "Home":
    st.title("🍴 Planer z Magazynem")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📅 PLANOWANIE"): st.session_state.page = "Plan"; st.rerun()
        if st.button("🏠 SPIŻARNIA (ILOŚCI)"): st.session_state.page = "Spizarnia"; st.rerun()
    with col2:
        if st.button("➕ DODAJ PRZEPIS"): st.session_state.page = "Dodaj"; st.rerun()
        if st.button("🛒 ZAKUPY"): st.session_state.page = "Zakupy"; st.rerun()

# --- MODUŁ PLANOWANIA (FIXED) ---
elif st.session_state.page == "Plan":
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    st.header("Plan na 7 dni")
    
    for i in range(7):
        data_str = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        with st.expander(f"Dzień: {data_str}", expanded=(i==0)):
            for p_typ in ["Śniadanie", "Lunch", "Kolacja"]:
                klucz = f"{data_str}_{p_typ}"
                
                # Bezpieczne pobieranie wyboru
                istniejacy = "Brak"
                if not st.session_state.plan_df.empty and 'Klucz' in st.session_state.plan_df.columns:
                    match = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == klucz]
                    if not match.empty: istniejacy = match.iloc[0]['Wybor']

                opcje = ["Brak"] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == p_typ]['Nazwa'].tolist() if not st.session_state.przepisy.empty else ["Brak"]
                
                wybor = st.selectbox(f"{p_typ}:", opcje, index=opcje.index(istniejacy) if istniejacy in opcje else 0, key=klucz)
                
                if wybor != istniejacy:
                    # Naprawa błędu KeyError przez jawną obsługę pustego DF
                    df_plan = st.session_state.plan_df
                    if df_plan.empty or 'Klucz' not in df_plan.columns:
                        df_plan = pd.DataFrame(columns=['Klucz', 'Wybor'])
                    
                    new_plan = df_plan[df_plan['Klucz'] != klucz]
                    new_plan = pd.concat([new_plan, pd.DataFrame([{"Klucz": klucz, "Wybor": wybor}])], ignore_index=True)
                    st.session_state.plan_df = new_plan
                    save_data(new_plan, "Plan")
                    st.rerun()

                res = sprawdz_skladniki(wybor)
                if res:
                    if res['mam']: st.caption(f"✅ Mam: {', '.join(res['mam'])}")
                    if res['brak']: st.caption(f"🛒 Brak: {', '.join(res['brak'])}")

                # --- 6. MODUŁ: SPIŻARNIA (Z ILOŚCIAMI) ---
elif st.session_state.page == "Spizarnia":
    if st.button("⬅ POWRÓT DO MENU"): 
        st.session_state.page = "Home"
        st.rerun()
    
    st.header("🏠 Twoje Zapasy")
    st.write("Zarządzaj ilością produktów w domu. Wpisz produkt i ilość (np. '2 litry', '4 szt').")

    # Dodawanie nowych produktów
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 2, 1])
        nowy_p = c1.text_input("Nazwa produktu:", placeholder="np. Mleko")
        nowa_i = c2.text_input("Ilość:", placeholder="np. 2 litry")
        if c3.button("DODAJ", use_container_width=True):
            if nowy_p:
                # Sprawdź czy produkt już istnieje, jeśli tak - nadpisz, jeśli nie - dodaj
                df = st.session_state.spizarnia_df
                df = df[df['Produkt'].str.lower() != nowy_p.lower()] # Usuń stary jeśli był
                nowy_row = pd.DataFrame([{"Produkt": nowy_p, "Ilosc": nowa_i}])
                st.session_state.spizarnia_df = pd.concat([df, nowy_row], ignore_index=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia")
                st.success(f"Zaktualizowano: {nowy_p}")
                st.rerun()

    st.divider()

    # Tabela edycji "z palca"
    if not st.session_state.spizarnia_df.empty:
        st.subheader("Aktualny stan magazynowy")
        st.info("Możesz edytować ilości bezpośrednio w tabeli poniżej i kliknąć Zapisz Zmiany.")
        
        # Funkcja do edycji tabeli
        edited_df = st.data_editor(
            st.session_state.spizarnia_df,
            column_config={
                "Produkt": st.column_config.TextColumn("Produkt", disabled=True),
                "Ilosc": st.column_config.TextColumn("Ilość (edytuj z palca)", required=True),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_spizarnia"
        )

        if st.button("💾 ZAPISZ ZMIANY W TABELI"):
            st.session_state.spizarnia_df = edited_df
            save_data(edited_df, "Spizarnia")
            st.success("Zapisano stan magazynowy!")
            st.rerun()
    else:
        st.info("Spiżarnia jest pusta. Dodaj pierwszy produkt powyżej.")

# --- 7. MODUŁ: DODAJ PRZEPIS ---
elif st.session_state.page == "Dodaj":
    if st.button("⬅ POWRÓT"): 
        st.session_state.page = "Home"
        st.rerun()
        
    st.header("➕ Nowy Przepis")
    with st.form("new_recipe_form"):
        n = st.text_input("Nazwa potrawy")
        t = st.selectbox("Typ posiłku", ["Śniadanie", "Lunch", "Kolacja"])
        s = st.text_area("Składniki (rozdzielone przecinkami, np: kurczak, ryż, brokuł)")
        
        if st.form_submit_button("ZAPISZ PRZEPIS"):
            if n and s:
                nowy_row = pd.DataFrame([{"Nazwa": n, "Typ": t, "Skladniki": s.lower()}])
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, nowy_row], ignore_index=True)
                save_data(st.session_state.przepisy, "Przepisy")
                st.success(f"Dodano przepis: {n}")
            else:
                st.error("Uzupełnij nazwę i składniki.")

# --- 8. MODUŁ: LISTA ZAKUPÓW ---
elif st.session_state.page == "Zakupy":
    if st.button("⬅ POWRÓT"): 
        st.session_state.page = "Home"
        st.rerun()
        
    st.header("🛒 Lista Zakupów")
    
    brakujace_globalnie = []
    if not st.session_state.plan_df.empty:
        for danie in st.session_state.plan_df['Wybor']:
            wynik = sprawdz_skladniki(danie)
            if wynik and wynik['brak']:
                brakujace_globalnie.extend(wynik['brak'])
    
    lista_final = sorted(list(set(brakujace_globalnie)))
    
    if lista_final:
        st.write("Tych rzeczy brakuje Ci do zaplanowanych dań:")
        for produkt in lista_final:
            st.checkbox(f"Kup: {produkt}", key=f"shop_{produkt}")
            
        st.download_button(
            "Pobierz listę (.txt)",
            "\n".join(lista_final),
            "zakupy.txt"
        )
    else:
        st.success("Wszystko masz! Twoja spiżarnia pokrywa zaplanowane posiłki.")
