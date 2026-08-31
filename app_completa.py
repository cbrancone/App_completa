import streamlit as st
import datetime
import pandas as pd
import requests
import streamlit_authenticator as stauth

# ==========================================
# CONFIGURAZIONE WEB APP APPS SCRIPT
# ==========================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby4FRWHeuR9Clu1cCUu11CDSbW-JUlgssoDWJY051cbY3ciu6XZ0Dexoiqku_P5ARyB/exec"

def get_as_df(sheet_name):
    try:
        url = f"{WEB_APP_URL}?action=leggi&sheet={sheet_name}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data:
                return pd.DataFrame(data)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def append_row_to_sheet(sheet_name, row_data):
    try:
        payload = {"sheet": sheet_name, "row": row_data}
        response = requests.post(WEB_APP_URL, json=payload)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def update_entire_sheet(sheet_name, df):
    try:
        data_to_send = [df.columns.tolist()] + df.values.tolist()
        payload = {"sheet": sheet_name, "action": "update_table", "rows": data_to_send}
        response = requests.post(WEB_APP_URL, json=payload)
        return response.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ==========================================
# GESTIONE UTENTI & AUTENTICAZIONE
# ==========================================
st.set_page_config(page_title="Gestionale Associazione Sportiva", page_icon="🏆", layout="wide")

df_utenti = get_as_df("utenti")

if df_utenti.empty or "Username" not in df_utenti.columns:
    default_user_row = ["admin", "admin123", "Amministratore", "Admin"]
    append_row_to_sheet("utenti", default_user_row)
    df_utenti = get_as_df("utenti")

credentials = {"usernames": {}}
if not df_utenti.empty and "Username" in df_utenti.columns:
    for _, row in df_utenti.iterrows():
        username = str(row.get("Username", "")).strip()
        password_db = str(row.get("Password", "")).strip()
            
        if username and username != "nan" and username != "":
            credentials["usernames"][username] = {
                "name": str(row.get("Nome Completo", username)),
                "password": password_db,
                "email": str(row.get("Email", ""))
            }

if "admin" not in credentials["usernames"]:
    credentials["usernames"]["admin"] = {
        "name": "Amministratore",
        "password": "admin123",
        "email": ""
    }

authenticator = stauth.Authenticate(
    credentials,
    cookie_name='gestionale_as_cookie_unique_id',
    key='gestionale_as_signature_key',
    cookie_expiry_days=30,
    auto_hash=True
)

authenticator.login(location="main")

authentication_status = st.session_state.get("authentication_status")
name = st.session_state.get("name")
username = st.session_state.get("username")

LISTA_CATEGORIE = [
    "Juniores", 
    "Allievi", 
    "Giovanissimi", 
    "Pulcini", 
    "Primi Calci", 
    "Piccoli Amici"
]

if authentication_status == False:
    st.error("⚠️ Username o password errati.")
elif authentication_status == None:
    st.warning("🔐 Inserisci le tue credenziali per accedere al gestionale.")
    st.stop()
elif authentication_status == True:
    
    authenticator.logout("Logout", "sidebar", key="logout_btn")
    st.sidebar.markdown(f"Benvenuto/a, **{name}** (`{username}`)")
    st.sidebar.divider()

    st.sidebar.title("Navigazione")
    lista_menu = [
        "📊 Dashboard & Bilancio", 
        "🏃 Atleti", 
        "📋 Certificati Medici", 
        "💳 Entrate (Quote Atleti)", 
        "💸 Uscite (Spese Generali)"
    ]
    
    # Mostra la gestione utenti solo se l'utente loggato è admin
    if username == "admin":
        lista_menu.append("👥 Gestione Utenti")

    menu = st.sidebar.radio("Scegli Sezione:", lista_menu)

    # ------------------------------------------
    # 1. DASHBOARD & BILANCIO
    # ------------------------------------------
    if menu == "📊 Dashboard & Bilancio":
        st.header("📊 Panoramica Economica e Operativa")
        
        df_atleti = get_as_df("atleti")
        df_pagamenti = get_as_df("pagamenti")
        df_spese = get_as_df("spese_generali")
        
        atleti_attivi = len(df_atleti) if not df_atleti.empty else 0
        tot_entrate = pd.to_numeric(df_pagamenti["Importo"]).sum() if not df_pagamenti.empty and "Importo" in df_pagamenti.columns else 0.0
        tot_uscite = pd.to_numeric(df_spese["Importo Spesa"]).sum() if not df_spese.empty and "Importo Spesa" in df_spese.columns else 0.0
        saldo_netto = tot_entrate - tot_uscite
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Atleti Registrati", atleti_attivi)
        col2.metric("Totale Entrate", f"€ {tot_entrate:,.2f}")
        col3.metric("Totale Uscite", f"€ {tot_uscite:,.2f}")
        col4.metric("Saldo Cassa Netto", f"€ {saldo_netto:,.2f}")

    # ------------------------------------------
    # 2. ATLETI
    # ------------------------------------------
    elif menu == "🏃 Atleti":
        st.header("🏃 Gestione Atleti")
        tab1, tab2 = st.tabs(["📋 Modifica ed Elenco Atleti", "➕ Registra Nuovo Atleta"])
        
        with tab1:
            df_atleti_completo = get_as_df("atleti")
            if not df_atleti_completo.empty:
                st.write("🎯 **Filtra Atleti per Categoria:**")
                cols_cat_atleti = st.columns(len(LISTA_CATEGORIE) + 1)
                
                if "filtro_atleti_attivo" not in st.session_state:
                    st.session_state.filtro_atleti_attivo = "Tutti"
                
                if cols_cat_atleti[0].button("⚪ Tutti", key="btn_atleti_tutti"):
                    st.session_state.filtro_atleti_attivo = "Tutti"
                    st.rerun()
                    
                for i, cat in enumerate(LISTA_CATEGORIE):
                    if cols_cat_atleti[i+1].button(f"🟢 {cat}", key=f"btn_atleti_{cat}"):
                        st.session_state.filtro_atleti_attivo = cat
                        st.rerun()
                
                df_filtrato = df_atleti_completo.copy()
                if st.session_state.filtro_atleti_attivo != "Tutti":
                    st.info(f"Stai visualizzando solo gli atleti della categoria: **{st.session_state.filtro_atleti_attivo}** (Le modifiche e cancellazioni terranno conto di tutto il database).")
                    if "Categoria" in df_filtrato.columns:
                        df_filtrato = df_filtrato[df_filtrato["Categoria"] == st.session_state.filtro_atleti_attivo]

                ricerca_atleta = st.text_input("🔎 Cerca per Nome, Cognome o Codice Fiscale:", "", key="ricerca_atleti_input")
                if ricerca_atleta:
                    mask_atleti = df_filtrato.astype(str).apply(lambda x: x.str.contains(ricerca_atleta, case=False)).any(axis=1)
                    df_filtrato = df_filtrato[mask_atleti]

                st.info("💡 **Istruzioni:** Modifica i dati o elimina le righelezionandole e premendo *Canc*.")
                
                edited_df_filtrato = st.data_editor(df_filtrato, num_rows="dynamic", use_container_width=True, key="editor_atleti")
                
                if st.button("💾 Salva modifiche su Google (Atleti)", key="btn_atleti"):
                    # Ricostruiamo il dataframe completo unendo le parti non visualizzate con quelle modificate
                    if st.session_state.filtro_atleti_attivo != "Tutti" and "Categoria" in df_atleti_completo.columns:
                        df_resto = df_atleti_completo[df_atleti_completo["Categoria"] != st.session_state.filtro_atleti_attivo]
                        df_finale = pd.concat([df_resto, edited_df_filtrato], ignore_index=True)
                    else:
                        df_finale = edited_df_filtrato
                        
                    res = update_entire_sheet("atleti", df_finale)
                    if res.get("status") == "success":
                        st.success("Tabella atleti aggiornata con successo su Google Sheets!")
                        st.rerun()
                    else:
                        st.error(f"Errore: {res.get('message')}")
            else:
                st.info("Nessun atleta registrato nel foglio `atleti`.")
                
        with tab2:
            with st.form("form_nuovo_atleta", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                nome = col_a.text_input("Nome *")
                cognome = col_b.text_input("Cognome *")
                cf = col_a.text_input("Codice Fiscale *").upper().strip()
                categoria = col_b.selectbox("Categoria Sportiva *", LISTA_CATEGORIE)
                data_nascita = col_a.date_input("Data di Nascita", value=datetime.date(2005, 1, 1))
                email = col_b.text_input("Email")
                telefono = col_a.text_input("Telefono")
                
                if st.form_submit_button("Salva Nuovo Atleta"):
                    if nome and cognome and cf:
                        df_esistenti = get_as_df("atleti")
                        if not df_esistenti.empty and "Codice Fiscale" in df_esistenti.columns and cf in df_esistenti["Codice Fiscale"].values:
                            st.error("Errore: Il Codice Fiscale inserito esiste già nel foglio.")
                        else:
                            res = append_row_to_sheet("atleti", [nome, cognome, cf, categoria, str(data_nascita), email, telefono])
                            if res.get("status") == "success":
                                st.success(f"Atleta {nome} {cognome} ({categoria}) salvato con successo!")
                                st.rerun()
                            else:
                                st.error(f"Errore: {res.get('message')}")
                    else:
                        st.warning("Compila i campi obbligatori.")

    # ------------------------------------------
    # 3. CERTIFICATI MEDICI
    # ------------------------------------------
    elif menu == "📋 Certificati Medici":
        st.header("📋 Gestione Visite e Certificati Medici")
        tab1, tab2, tab3 = st.tabs(["⚠️ Certificati in Scadenza", "➕ Inserisci Certificato", "📚 Modifica Storico Certificati"])
        
        df_visite = get_as_df("visite_mediche")
        df_atleti = get_as_df("atleti")
        
        with tab1:
            giorni = st.slider("Mostra certificati in scadenza nei prossimi (giorni):", 15, 90, 60)
            oggi = datetime.date.today()
            limite = oggi + datetime.timedelta(days=giorni)
            
            if not df_visite.empty:
                df_visite["data_scadenza_dt"] = pd.to_datetime(df_visite["Data scadenza Certificato"]).dt.date
                filtrati = df_visite[df_visite["data_scadenza_dt"] <= limite].sort_values(by="Data scadenza Certificato")
                
                if not filtrati.empty:
                    data_tabella = []
                    for _, row in filtrati.iterrows():
                        giorni_rimanenti = (row["data_scadenza_dt"] - oggi).days
                        stato = "🔴 Scaduto" if giorni_rimanenti < 0 else ("🟡 In scadenza" if giorni_rimanenti <= 30 else "🟢 Valido")
                        data_tabella.append({
                            "Stato": stato,
                            "Atleta": row.get("Selezione Atleta", ""),
                            "Tipo Visita": row.get("Tipo Visita", ""),
                            "Data Scadenza": row.get("Data scadenza Certificato", ""),
                            "Giorni Rimanenti": f"{giorni_rimanenti} giorni" if giorni_rimanenti >= 0 else f"Scaduto da {-giorni_rimanenti} giorni"
                        })
                    st.dataframe(pd.DataFrame(data_tabella), use_container_width=True)
                else:
                    st.success("Nessun certificato in scadenza nel periodo selezionato!")
            else:
                st.info("Nessun certificato registrato.")

        with tab2:
            if df_atleti.empty:
                st.warning("Devi prima inserire almeno un atleta nella sezione Atleti.")
            else:
                lista_atleti = [f"{r.get('Nome', '')} {r.get('Cognome', '')}".strip() for _, r in df_atleti.iterrows()]
                with st.form("form_visita_medica", clear_on_submit=True):
                    scelta_atleta = st.selectbox("Selezione Atleta *", lista_atleti)
                    col_c1, col_c2 = st.columns(2)
                    data_visita = col_c1.date_input("Data Effettuazione Visita", value=datetime.date.today())
                    data_scadenza = col_c2.date_input("Data scadenza Certificato", value=data_visita + datetime.timedelta(days=365))
                    tipo_visita = col_c1.selectbox("Tipo Visita", ["Agonistica", "Non Agonistica", "Elettrocardiogramma"])
                    idoneo = col_c2.checkbox("Idoneità Concessa", value=True)
                    
                    if st.form_submit_button("Salva Certificato Medico"):
                        res = append_row_to_sheet("visite_mediche", [scelta_atleta, str(data_visita), str(data_scadenza), tipo_visita, idoneo])
                        if res.get("status") == "success":
                            st.success("Certificato medico registrato correttamente!")
                            st.rerun()
                        else:
                            st.error(f"Errore: {res.get('message')}")

        with tab3:
            st.info("Puoi modificare lo storico delle visite direttamente qui sotto:")
            if not df_visite.empty:
                edited_df_visite = st.data_editor(df_visite, use_container_width=True, key="editor_visite")
                if st.button("💾 Salva modifiche su Google (Visite)", key="btn_visite"):
                    res = update_entire_sheet("visite_mediche", edited_df_visite)
                    if res.get("status") == "success":
                        st.success("Tabella visite aggiornata con successo!")
                        st.rerun()
                    else:
                        st.error(f"Errore: {res.get('message')}")
            else:
                st.info("Nessun certificato presente in archivio.")

    # ------------------------------------------
    # 4. ENTRATE / QUOTE
    # ------------------------------------------
    elif menu == "💳 Entrate (Quote Atleti)":
        st.header("💳 Registro Incassi Quote")
        tab1, tab2 = st.tabs(["📋 Modifica ed Elenco Incassi", "➕ Registra Incasso Quota"])
        
        df_pagamenti_completo = get_as_df("pagamenti")
        df_atleti = get_as_df("atleti")
        
        with tab1:
            if not df_pagamenti_completo.empty:
                st.write("🎯 **Filtra Incassi per Categoria:**")
                cols_cat_pag = st.columns(len(LISTA_CATEGORIE) + 1)
                
                if "filtro_pag_attivo" not in st.session_state:
                    st.session_state.filtro_pag_attivo = "Tutti"
                
                if cols_cat_pag[0].button("⚪ Tutti", key="btn_pag_tutti"):
                    st.session_state.filtro_pag_attivo = "Tutti"
                    st.rerun()
                    
                for i, cat in enumerate(LISTA_CATEGORIE):
                    if cols_cat_pag[i+1].button(f"🟢 {cat}", key=f"btn_pag_{cat}"):
                        st.session_state.filtro_pag_attivo = cat
                        st.rerun()
                
                df_pag_filtrato = df_pagamenti_completo.copy()
                if st.session_state.filtro_pag_attivo != "Tutti":
                    st.info(f"Stai visualizzando solo gli incassi della categoria: **{st.session_state.filtro_pag_attivo}**")
                    if "Categoria" in df_pag_filtrato.columns:
                        df_pag_filtrato = df_pag_filtrato[df_pag_filtrato["Categoria"] == st.session_state.filtro_pag_attivo]

                ricerca_testo = st.text_input("🔎 Cerca per Atleta o Causale:", "", key="ricerca_incassi")
                if ricerca_testo:
                    mask = df_pag_filtrato.astype(str).apply(lambda x: x.str.contains(ricerca_testo, case=False)).any(axis=1)
                    df_pag_filtrato = df_pag_filtrato[mask]

                edited_df_pagamenti = st.data_editor(df_pag_filtrato, num_rows="dynamic", use_container_width=True, key="editor_pagamenti")
                
                if st.button("💾 Salva modifiche su Google (Incassi)", key="btn_incassi"):
                    if st.session_state.filtro_pag_attivo != "Tutti" and "Categoria" in df_pagamenti_completo.columns:
                        df_pag_resto = df_pagamenti_completo[df_pagamenti_completo["Categoria"] != st.session_state.filtro_pag_attivo]
                        df_pag_finale = pd.concat([df_pag_resto, edited_df_pagamenti], ignore_index=True)
                    else:
                        df_pag_finale = edited_df_pagamenti
                        
                    res = update_entire_sheet("pagamenti", df_pag_finale)
                    if res.get("status") == "success":
                        st.success("Tabella incassi aggiornata con successo!")
                        st.rerun()
                    else:
                        st.error(f"Errore: {res.get('message')}")
            else:
                st.info("Nessun incasso registrato.")
                
        with tab2:
            if df_atleti.empty:
                st.warning("Devi prima registrare almeno un atleta.")
            else:
                lista_atleti = [f"{r.get('Nome', '')} {r.get('Cognome', '')}".strip() for _, r in df_atleti.iterrows()]
                with st.form("form_incasso", clear_on_submit=True):
                    col_p1, col_p2 = st.columns(2)
                    scelta_atleta = col_p1.selectbox("Selezione Atleta", lista_atleti)
                    categoria_quota = col_p2.selectbox("Categoria di Riferimento", LISTA_CATEGORIE)
                    causale = st.text_input("Causale (es. Quota Mensile / Annua)")
                    importo = st.number_input("Importo (€)", min_value=1.0, step=5.0)
                    metodo = st.selectbox("Metodo di Pagamento", ["Bonifico", "Contanti", "POS / Carta"])
                    data_pag = st.date_input("Data Pagamento", value=datetime.date.today())
                    
                    if st.form_submit_button("Registra Incasso"):
                        res = append_row_to_sheet("pagamenti", [scelta_atleta, categoria_quota, causale, importo, metodo, str(data_pag)])
                        if res.get("status") == "success":
                            st.success("Pagamento registrato correttamente!")
                            st.rerun()
                        else:
                            st.error(f"Errore: {res.get('message')}")

    # ------------------------------------------
    # 5. USCITE / SPESE GENERALI
    # ------------------------------------------
    elif menu == "💸 Uscite (Spese Generali)":
        st.header("💸 Gestione Spese Generali dell'Associazione")
        tab1, tab2 = st.tabs(["📋 Modifica ed Elenco Uscite", "➕ Registra Nuova Spesa"])
        
        df_spese = get_as_df("spese_generali")
        
        with tab1:
            if not df_spese.empty:
                edited_df_spese = st.data_editor(df_spese, num_rows="dynamic", use_container_width=True, key="editor_spese")
                if st.button("💾 Salva modifiche su Google (Spese)", key="btn_spese"):
                    res = update_entire_sheet("spese_generali", edited_df_spese)
                    if res.get("status") == "success":
                        st.success("Tabella spese aggiornata con successo!")
                        st.rerun()
                    else:
                        st.error(f"Errore: {res.get('message')}")
            else:
                st.info("Nessuna spesa registrata.")
                
        with tab2:
            with st.form("form_spesa", clear_on_submit=True):
                col_1, col_2 = st.columns(2)
                descrizione = col_1.text_input("Descrizione Spesa")
                categoria = col_2.selectbox("Categoria", ["Affitto Palestra", "Utenze", "Istruttori", "Materiale", "Altro"])
                importo = col_1.number_input("Importo Spesa (€)", min_value=0.01, step=10.0)
                data_spesa = col_2.date_input("Data del Pagamento", value=datetime.date.today())
                fornitore = col_1.text_input("Fornitore/Beneficiario")
                metodo = col_2.selectbox("Metodo di Pagamento Spesa", ["Bonifico", "Carta / POS", "Contanti"])
                
                if st.form_submit_button("Salva Spesa"):
                    if descrizione and importo > 0:
                        res = append_row_to_sheet("spese_generali", [descrizione, categoria, importo, str(data_spesa), fornitore, metodo])
                        if res.get("status") == "success":
                            st.success("Spesa registrata correttamente!")
                            st.rerun()
                        else:
                            st.error(f"Errore: {res.get('message')}")
                    else:
                        st.warning("Inserisci una descrizione e un importo valido.")

    # ------------------------------------------
    # 6. GESTIONE UTENTI (SOLO ADMIN)
    # ------------------------------------------
    elif menu == "👥 Gestione Utenti" and username == "admin":
        st.header("👥 Gestione Utenti del Gestionale")
        tab_u1, tab_u2 = st.tabs(["📋 Elenco e Modifica Utenti", "➕ Crea Nuovo Utente"])
        
        df_utenti_sheet = get_as_df("utenti")
        
        with tab_u1:
            if not df_utenti_sheet.empty:
                st.info("Puoi modificare le credenziali o cancellare utenti dalla tabella sottostante:")
                edited_df_utenti = st.data_editor(df_utenti_sheet, num_rows="dynamic", use_container_width=True, key="editor_utenti")
                if st.button("💾 Salva modifiche su Google (Utenti)", key="btn_salva_utenti"):
                    res = update_entire_sheet("utenti", edited_df_utenti)
                    if res.get("status") == "success":
                        st.success("Tabella utenti aggiornata con successo! Ricarica la pagina per applicare le modifiche di accesso.")
                        st.rerun()
                    else:
                        st.error(f"Errore: {res.get('message')}")
            else:
                st.info("Nessun utente trovato.")
                
        with tab_u2:
            with st.form("form_nuovo_utente", clear_on_submit=True):
                col_u1, col_u2 = st.columns(2)
                nuovo_user = col_u1.text_input("Username (es. mario.rossi) *").strip()
                nuova_pass = col_u2.text_input("Password *", type="password")
                nome_completo = col_u1.text_input("Nome e Cognome *")
                email_utente = col_u2.text_input("Email (opzionale)")
                
                if st.form_submit_button("Crea Nuovo Utente"):
                    if nuovo_user and nuova_pass and nome_completo:
                        if not df_utenti_sheet.empty and "Username" in df_utenti_sheet.columns and nuovo_user in df_utenti_sheet["Username"].values:
                            st.error("Errore: Questo username esiste già.")
                        else:
                            res = append_row_to_sheet("utenti", [nuovo_user, nuova_pass, nome_completo, email_utente])
                            if res.get("status") == "success":
                                st.success(f"Utente '{nuovo_user}' creato con successo!")
                                st.rerun()
                            else:
                                st.error(f"Errore: {res.get('message')}")
                    else:
                        st.warning("Compila tutti i campi obbligatori contrassegnati con l'asterisco.")
