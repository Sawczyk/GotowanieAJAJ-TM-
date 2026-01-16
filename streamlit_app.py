import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Konfiguracja
st.set_page_config(page_title="Planer Inteligentny", layout="wide", initial_sidebar_state="collapsed")

# Polski format dni tygodnia
DNI_TYGODNIA = {
    0: "Poniedziałek", 1: "Wtorek", 2: "Środa", 3: "Czwartek",
    4: "Piątek", 5: "Sobota", 6: "Niedziela"
}

# Style CSS dla dużych przycisków
st.markdown("""
    <style>
    div.stButton > button { width: 100%; height: 80px; font-size: 18px; font-weight: bold; border-radius: 12px; }
    .status-ok { color: #2ecc71; font-weight: bold; }
    .status-alert { color: #e74c3c; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INICJALIZACJA DANYCH ---
if 'przepisy' not in st.session_state:
    st.session_state.przepisy = pd.DataFrame([
        {"Nazwa": "Jajecznica", "Typ": "Śniadanie", "Skladniki": "jajka, masło"},
        {"Nazwa": "Kurczak", "Typ": "Lunch", "Skladniki": "kurczak, ryż"},
    ])

if 'spizarnia' not in st.session_state:
    st.session_state.spizarnia = set(["jajka", "ryż"]) # Przykładowe zapasy

if 'plan' not in st.session_state:
    dni = []
    for i in range(7):
        d = datetime.now() + timedelta(days=i)
        nazwa_dnia = f"{d.strftime('%Y-%m-%d')} ({DNI_TYGODNIA[d.weekday()]})"
        dni.append(nazwa_dnia)
    st.session_state.plan = pd.DataFrame({"Data": dni, "Śniadanie": "", "Lunch": "", "Kolacja": ""})

if 'page' not in st.session_state:
    st.session_state.page = "Home"

# --- LOGIKA ---
def sprawdz_skladniki(danie_nazwa):
    if not danie_nazwa: return ""
    przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == danie_nazwa]
    if przepis.empty: return ""
    
    wymagane = [s.strip().lower() for s in przepis.iloc[0]['Skladniki'].split(',')]
    brakujace = [s for s in wymagane if s not in st.session_state.spizarnia]
    
    if not brakujace:
        return "✅ (Wszystko jest)"
    else:
        return f"🛒 Brak: {', '.join(brakujace)}"

# --- NAWIGACJA ---
if st.session_state.page == "Home":
    st.title("🍴 Planer z Inteligencją Spiżarni")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📅 MÓJ PLAN"): st.session_state.page = "Plan"; st.rerun()
        if st.button("➕ DODAJ PRZEPIS"): st.session_state.page = "Dodaj"; st.rerun()
    with c2:
        if st.button("🏠 MOJA SPIŻARNIA"): st.session_state.page = "Spizarnia"; st.rerun()
        if st.button("🛒 LISTA ZAKUPÓW"): st.session_state.page = "Zakupy"; st.rerun()

elif st.session_state.page == "Spizarnia":
    if st.button("⬅ Powrót"): st.session_state.page = "Home"; st.rerun()
    st.subheader("Zarządzaj zapasami")
    nowy_produkt = st.text_input("Dodaj produkt do spiżarni (np. jajka, mleko):").lower()
    if st.button("Dodaj do spiżarni"):
        st.session_state.spizarnia.add(nowy_produkt)
    
    st.write("### Twoje zapasy:")
    do_usuniecia = []
    for p in sorted(list(st.session_state.spizarnia)):
        col_p, col_del = st.columns([4, 1])
        col_p.write(f"- {p}")
        if col_del.button("Usuń", key=f"del_{p}"):
            do_usuniecia.append(p)
    
    for p in do_usuniecia:
        st.session_state.spizarnia.remove(p)
        st.rerun()

elif st.session_state.page == "Plan":
    if st.button("⬅ Powrót"): st.session_state.page = "Home"; st.rerun()
    st.subheader("Planowanie tygodnia")
    
    # Wyświetlamy statusy pod tabelą dla przejrzystości
    for index, row in st.session_state.plan.iterrows():
        with st.expander(f"📅 {row['Data']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                opts = [""] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == "Śniadanie"]['Nazwa'].tolist()
                st.session_state.plan.at[index, 'Śniadanie'] = st.selectbox(f"Śniadanie", opts, index=opts.index(row['Śniadanie']) if row['Śniadanie'] in opts else 0, key=f"s_{index}")
                st.write(sprawdz_skladniki(st.session_state.plan.at[index, 'Śniadanie']))
            with col2:
                opts = [""] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == "Lunch"]['Nazwa'].tolist()
                st.session_state.plan.at[index, 'Lunch'] = st.selectbox(f"Lunch", opts, index=opts.index(row['Lunch']) if row['Lunch'] in opts else 0, key=f"l_{index}")
                st.write(sprawdz_skladniki(st.session_state.plan.at[index, 'Lunch']))
            with col3:
                opts = [""] + st.session_state.przepisy[st.session_state.przepisy['Typ'] == "Kolacja"]['Nazwa'].tolist()
                st.session_state.plan.at[index, 'Kolacja'] = st.selectbox(f"Kolacja", opts, index=opts.index(row['Kolacja']) if row['Kolacja'] in opts else 0, key=f"k_{index}")
                st.write(sprawdz_skladniki(st.session_state.plan.at[index, 'Kolacja']))

elif st.session_state.page == "Dodaj":
    if st.button("⬅ Powrót"): st.session_state.page = "Home"; st.rerun()
    st.subheader("Nowy przepis")
    with st.form("f"):
        n = st.text_input("Nazwa")
        t = st.selectbox("Typ", ["Śniadanie", "Lunch", "Kolacja"])
        s = st.text_area("Składniki (przecinek)")
        if st.form_submit_button("Zapisz"):
            st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa":n, "Typ":t, "Skladniki":s.lower()}])], ignore_index=True)
            st.success("Dodano!")

elif st.session_state.page == "Zakupy":
    if st.button("⬅ Powrót"): st.session_state.page = "Home"; st.rerun()
    st.subheader("Lista zakupów (tylko brakujące)")
    
    potrzebne = []
    zaplanowane = pd.concat([st.session_state.plan['Śniadanie'], st.session_state.plan['Lunch'], st.session_state.plan['Kolacja']])
    zaplanowane = zaplanowane[zaplanowane != ""]
    
    for danie in zaplanowane:
        przepis = st.session_state.przepisy[st.session_state.przepisy['Nazwa'] == danie]
        if not przepis.empty:
            potrzebne.extend([i.strip().lower() for i in przepis.iloc[0]['Skladniki'].split(',')])
    
    do_kupienia = sorted(list(set([p for p in potrzebne if p not in st.session_state.spizarnia])))
    
    if do_kupienia:
        for item in do_kupienia: st.checkbox(item, key=f"buy_{item}")
    else:
        st.success("Masz wszystko w spiżarni! Brak zakupów.")
