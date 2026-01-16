# --- 4. NAWIGACJA HOME ---
if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"<div class='today-highlight'><h1 style='margin:0; color:white;'>{dni_pl[teraz.weekday()]}</h1><p style='margin:0; color:white;'>{teraz.strftime('%d.%m.%Y')}</p></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    pages = [("PLANOWANIE", "Plan", "📅"), ("SPIŻARNIA", "Spizarnia", "🏠"), ("PRZEPISY", "Dodaj", "📖"), ("ZAKUPY", "Zakupy", "🛒")]
    for i, (label, pg, icon) in enumerate(pages):
        with [c1, c2, c3, c4][i]:
            st.markdown(f"<div class='menu-box'>{icon}</div>", unsafe_allow_html=True)
            if st.button(label, use_container_width=True): st.session_state.page = pg; st.rerun()

# --- 5. MODUŁ: PLANOWANIE ---
elif st.session_state.page == "Plan":
    st.header("📅 Planowanie")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    if col_prev.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    dates = get_week_dates(st.session_state.week_offset)
    col_info.markdown(f"<h3 style='text-align:center;'>{dates[0].strftime('%d.%m')} - {dates[-1].strftime('%d.%m')}</h3>", unsafe_allow_html=True)
    if col_next.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()
    
    with st.expander("📊 ANALIZA SKŁADNIKÓW", expanded=True):
        b = analizuj_zapasy()
        for p, d in b.items():
            st.write(f"**{p.capitalize()}**: {d['mam']}/{d['potr']} " + (f"🔴 Brakuje: {d['brak']}" if d['brak'] > 0 else "🟢 OK"))

    t_id = dates[0].strftime("%Y-%V")
    for i, d_obj in enumerate(dates):
        with st.expander(f"{dni_pl[i]} ({d_obj.strftime('%d.%m')})"):
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{dni_pl[i]}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if not st.session_state.plan_df.empty and k in st.session_state.plan_df['Klucz'].values else "Brak"
                opcje = ["Brak"] + st.session_state.przepisy['Nazwa'].tolist()
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                if wyb != istn:
                    df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)
                    save_data(st.session_state.plan_df, "Plan"); st.rerun()

# --- 6. MODUŁ: SPIŻARNIA (Z EDYCJĄ ILOŚCI) ---
elif st.session_state.page == "Spizarnia":
    st.header("🏠 Spiżarnia")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    with st.form("add_stock"):
        st.write("**Dodaj nowy produkt:**")
        c1, c2, c3 = st.columns([3, 1, 1])
        new_p = c1.text_input("Nazwa produktu")
        new_i = c2.number_input("Ilość początkowa", min_value=0.0, step=0.1)
        if c3.form_submit_button("➕ DODAJ"):
            if new_p:
                st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": new_p, "Ilosc": new_i}])], ignore_index=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

    st.markdown("---")
    st.write("**Twoje zapasy (możesz edytować ilości bezpośrednio):**")
    
    for idx, row in st.session_state.spizarnia_df.iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([0.5, 3, 1.5, 0.5])
            c1.write(f"{idx+1}.")
            c2.write(f"**{row['Produkt']}**")
            
            # Pole do szybkiej edycji ilości
            edited_qty = c3.number_input("Ilość", value=float(row['Ilosc']), step=0.1, key=f"edit_qty_{idx}", label_visibility="collapsed")
            
            # Jeśli ilość została zmieniona, zapisujemy
            if edited_qty != float(row['Ilosc']):
                st.session_state.spizarnia_df.at[idx, 'Ilosc'] = edited_qty
                save_data(st.session_state.spizarnia_df, "Spizarnia")
                st.rerun()
                
            if c4.button("🗑️", key=f"del_s_{idx}"):
                st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

# --- 7. MODUŁ: PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.header("📖 Baza Przepisów")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    with st.form("add_recipe"):
        n = st.text_input("Nazwa potrawy")
        s = st.text_area("Składniki (np. Jajka (3), Mleko (0.5))")
        if st.form_submit_button("➕ DODAJ PRZEPIS"):
            if n and s:
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": n, "Skladniki": s}])], ignore_index=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

    st.markdown("---")
    for idx, row in st.session_state.przepisy.iterrows():
        with st.container():
            st.markdown(f"<div class='recipe-card'><b>{idx+1}. {row['Nazwa']}</b><br><small>{row['Skladniki']}</small></div>", unsafe_allow_html=True)
            if st.button(f"Usuń: {row['Nazwa']}", key=f"del_r_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

# --- 8. MODUŁ: ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.header("🛒 Zakupy")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    b = analizuj_zapasy()
    braki = {k: v for k, v in b.items() if v['brak'] > 0}
    if braki:
        for p, d in braki.items(): st.warning(f"🔸 **{p.capitalize()}**: {d['brak']}")
    else: st.success("Spiżarnia gotowa! 🎉")


# --- 4. NAWIGACJA HOME ---
if st.session_state.page == "Home":
    teraz = datetime.now()
    st.markdown(f"<div class='today-highlight'><h1 style='margin:0; color:white;'>{dni_pl[teraz.weekday()]}</h1><p style='margin:0; color:white;'>{teraz.strftime('%d.%m.%Y')}</p></div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    pages = [("PLANOWANIE", "Plan", "📅"), ("SPIŻARNIA", "Spizarnia", "🏠"), ("PRZEPISY", "Dodaj", "📖"), ("ZAKUPY", "Zakupy", "🛒")]
    for i, (label, pg, icon) in enumerate(pages):
        with [c1, c2, c3, c4][i]:
            st.markdown(f"<div class='menu-box'>{icon}</div>", unsafe_allow_html=True)
            if st.button(label, use_container_width=True): st.session_state.page = pg; st.rerun()

# --- 5. MODUŁ: PLANOWANIE ---
elif st.session_state.page == "Plan":
    st.header("📅 Planowanie")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    if col_prev.button("⬅ Poprzedni"): st.session_state.week_offset -= 1; st.rerun()
    dates = get_week_dates(st.session_state.week_offset)
    col_info.markdown(f"<h3 style='text-align:center;'>{dates[0].strftime('%d.%m')} - {dates[-1].strftime('%d.%m')}</h3>", unsafe_allow_html=True)
    if col_next.button("Następny ➡"): st.session_state.week_offset += 1; st.rerun()
    
    with st.expander("📊 ANALIZA SKŁADNIKÓW", expanded=True):
        b = analizuj_zapasy()
        for p, d in b.items():
            st.write(f"**{p.capitalize()}**: {d['mam']}/{d['potr']} " + (f"🔴 Brakuje: {d['brak']}" if d['brak'] > 0 else "🟢 OK"))

    t_id = dates[0].strftime("%Y-%V")
    for i, d_obj in enumerate(dates):
        with st.expander(f"{dni_pl[i]} ({d_obj.strftime('%d.%m')})"):
            for typ in ["Śniadanie", "Obiad", "Kolacja"]:
                k = f"{t_id}_{dni_pl[i]}_{typ}"
                istn = st.session_state.plan_df[st.session_state.plan_df['Klucz'] == k]['Wybor'].values[0] if not st.session_state.plan_df.empty and k in st.session_state.plan_df['Klucz'].values else "Brak"
                opcje = ["Brak"] + st.session_state.przepisy['Nazwa'].tolist()
                wyb = st.selectbox(f"{typ}:", opcje, index=opcje.index(istn) if istn in opcje else 0, key=k)
                if wyb != istn:
                    df = st.session_state.plan_df[st.session_state.plan_df['Klucz'] != k]
                    st.session_state.plan_df = pd.concat([df, pd.DataFrame([{"Klucz": k, "Wybor": wyb}])], ignore_index=True)
                    save_data(st.session_state.plan_df, "Plan"); st.rerun()

# --- 6. MODUŁ: SPIŻARNIA (Z EDYCJĄ ILOŚCI) ---
elif st.session_state.page == "Spizarnia":
    st.header("🏠 Spiżarnia")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    
    with st.form("add_stock"):
        st.write("**Dodaj nowy produkt:**")
        c1, c2, c3 = st.columns([3, 1, 1])
        new_p = c1.text_input("Nazwa produktu")
        new_i = c2.number_input("Ilość początkowa", min_value=0.0, step=0.1)
        if c3.form_submit_button("➕ DODAJ"):
            if new_p:
                st.session_state.spizarnia_df = pd.concat([st.session_state.spizarnia_df, pd.DataFrame([{"Produkt": new_p, "Ilosc": new_i}])], ignore_index=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

    st.markdown("---")
    st.write("**Twoje zapasy (możesz edytować ilości bezpośrednio):**")
    
    for idx, row in st.session_state.spizarnia_df.iterrows():
        with st.container():
            c1, c2, c3, c4 = st.columns([0.5, 3, 1.5, 0.5])
            c1.write(f"{idx+1}.")
            c2.write(f"**{row['Produkt']}**")
            
            # Pole do szybkiej edycji ilości
            edited_qty = c3.number_input("Ilość", value=float(row['Ilosc']), step=0.1, key=f"edit_qty_{idx}", label_visibility="collapsed")
            
            # Jeśli ilość została zmieniona, zapisujemy
            if edited_qty != float(row['Ilosc']):
                st.session_state.spizarnia_df.at[idx, 'Ilosc'] = edited_qty
                save_data(st.session_state.spizarnia_df, "Spizarnia")
                st.rerun()
                
            if c4.button("🗑️", key=f"del_s_{idx}"):
                st.session_state.spizarnia_df = st.session_state.spizarnia_df.drop(idx).reset_index(drop=True)
                save_data(st.session_state.spizarnia_df, "Spizarnia"); st.rerun()

# --- 7. MODUŁ: PRZEPISY ---
elif st.session_state.page == "Dodaj":
    st.header("📖 Baza Przepisów")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    with st.form("add_recipe"):
        n = st.text_input("Nazwa potrawy")
        s = st.text_area("Składniki (np. Jajka (3), Mleko (0.5))")
        if st.form_submit_button("➕ DODAJ PRZEPIS"):
            if n and s:
                st.session_state.przepisy = pd.concat([st.session_state.przepisy, pd.DataFrame([{"Nazwa": n, "Skladniki": s}])], ignore_index=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

    st.markdown("---")
    for idx, row in st.session_state.przepisy.iterrows():
        with st.container():
            st.markdown(f"<div class='recipe-card'><b>{idx+1}. {row['Nazwa']}</b><br><small>{row['Skladniki']}</small></div>", unsafe_allow_html=True)
            if st.button(f"Usuń: {row['Nazwa']}", key=f"del_r_{idx}"):
                st.session_state.przepisy = st.session_state.przepisy.drop(idx).reset_index(drop=True)
                save_data(st.session_state.przepisy, "Przepisy"); st.rerun()

# --- 8. MODUŁ: ZAKUPY ---
elif st.session_state.page == "Zakupy":
    st.header("🛒 Zakupy")
    if st.button("⬅ POWRÓT"): st.session_state.page = "Home"; st.rerun()
    b = analizuj_zapasy()
    braki = {k: v for k, v in b.items() if v['brak'] > 0}
    if braki:
        for p, d in braki.items(): st.warning(f"🔸 **{p.capitalize()}**: {d['brak']}")
    else: st.success("Spiżarnia gotowa! 🎉")
