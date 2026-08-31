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
            return pd.DataFrame(response.json())
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

# Recupera gli utenti da Google Sheets
df_utenti = get_as_df("utenti")

# Se il foglio utenti è vuoto, creiamo un utente amministratore di default
if df_utenti.empty:
    # Utente predefinito: admin / admin123 (Nota: in produzione le password andrebbero criptate, qui usiamo testo chiaro per semplicità di avvio)
    default_user_row = ["admin", "admin123", "Amministratore", "Admin"]
    append_row_to_sheet("utenti", default_user_row)
    df_utenti = get_as_df("utenti")

# Prepara la struttura dati per streamlit-authenticator
credentials = {"usernames": {}}
if not df_utenti.empty and "Username" in df_utenti.columns:
    for _, row in df_utenti.iterrows():
        username = str(row.get("Username"))
        if username and username != "nan":
            credentials["usernames"][username] = {
                "name": str(row.get("Nome Completo", username)),
                "password": str(row.get("Password", "")),
                "email": ""
            }

authenticator = stauth.Authenticate(
    credentials,
    "gestionale_as_cookie",
    "cookie_signature_key",
    cookie_expiry_days=30
)

# Mostra il form di login nella schermata principale
name, authentication_status, username = authenticator.login("Login", location="main")

if authentication_status == False:
    st.error("⚠️ Username o password errati.")
elif authentication_status == None:
    st.warning("🔐 Inserisci le tue credenziali per accedere al gestionale.")
    st.stop()  # Interrompe l'esecuzione finché non si effettua il login

elif authentication_status == True:
    # ==========================================
    # INTERFACCIA STREAMLIT (ACCESSO CONSENTITO)
    # ==========================================
    
    # Bottone di logout e benvenuto nella barra laterale
    authenticator.logout("Logout", "sidebar", key="logout_btn")
    st.sidebar.markdown(f"Benvenuto/a, **{name}** (`{username}`)")
    st.sidebar.divider()

    st.sidebar.title("Navigazione")
    menu = st.sidebar.radio("Scegli Sezione:", [
        "📊 Dashboard & Bilancio", 
        "🏃 Atleti", 
        "📋 Certificati Medici", 
        "💳 Entrate (Quote Atleti)", 
        "💸 Uscite (Spese Generali)"
    ])

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
            st.info("💡 Modifica i dati direttamente nella tabella e clicca su 'Salva modifiche su Google'.")
            df_atleti = get_as_df("atleti")
            if not df_atleti.empty:
                edited_df_atleti = st.data_editor(df_atleti, use_container_width=True, key="editor_atleti")
                if st.button("💾 Salva modifiche su Google (Atleti)", key="btn_atleti"):
                    res = update_entire_sheet("atleti", edited_df_atleti)
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
                data_nascita = col_b.date_input("Data di Nascita", value=datetime.date(2005, 1, 1))
                email = col_a.text_input("Email")
                telefono = col_b.text_input("Telefono")
                
                if st.form_submit_button("Salva Nuovo Atleta"):
                    if nome and cognome and cf:
                        df_esistenti = get_as_df("atleti")
                        if not df_esistenti.empty and "Codice Fiscale" in df_esistenti.columns and cf in df_esistenti["Codice Fiscale"].values:
                            st.error("Errore: Il Codice Fiscale inserito esiste già nel foglio.")
                        else:
                            res = append_row_to_sheet("atleti", [nome, cognome, cf, str(data_nascita), email, telefono])
                            if res.get("status") == "success":
                                st.success(f"Atleta {nome} {cognome} salvato con successo!")
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
        
        df_pagamenti = get_as_df("pagamenti")
        df_atleti = get_as_df("atleti")
        
        with tab1:
            if not df_pagamenti.empty:
                edited_df_pagamenti = st.data_editor(df_pagamenti, use_container_width=True, key="editor_pagamenti")
                if st.button("💾 Salva modifiche su Google (Incassi)", key="btn_incassi"):
                    res = update_entire_sheet("pagamenti", edited_df_pagamenti)
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
                    scelta_atleta = st.selectbox("Selezione Atleta", lista_atleti)
                    causale = st.text_input("Causale")
                    importo = st.number_input("Importo (€)", min_value=1.0, step=5.0)
                    metodo = st.selectbox("Metodo di Pagamento", ["Bonifico", "Contanti", "POS / Carta"])
                    data_pag = st.date_input("Data Pagamento", value=datetime.date.today())
                    
                    if st.form_submit_button("Registra Incasso"):
                        res = append_row_to_sheet("pagamenti", [scelta_atleta, causale, importo, metodo, str(data_pag)])
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
                edited_df_spese = st.data_editor(df_spese, use_container_width=True, key="editor_spese")
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
