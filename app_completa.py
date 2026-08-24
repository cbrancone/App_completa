import streamlit as st
import datetime
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 1. CONFIGURAZIONE CONNESSIONE GOOGLE SHEETS
# ==========================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def init_connection():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(credentials)

gc = init_connection()

# Inserisci qui l'URL completo del tuo Google Sheet
SPREADSHEET_URL = "INSERISCI_QUI_IL_LINK_DEL_TUO_FOGLIO_GOOGLE"

try:
    sh = gc.open_by_url(SPREADSHEET_URL)
except Exception as e:
    st.error(f"Errore di connessione al Foglio Google. Verifica l'URL o la condivisione con il Service Account. Dettaglio: {e}")
    st.stop()

# Funzione di supporto per leggere una tabella come DataFrame
def get_as_df(worksheet_name):
    try:
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()

# ==========================================
# 2. INTERFACCIA STREAMLIT
# ==========================================
st.set_page_config(page_title="Gestionale Associazione Sportiva", page_icon="🏆", layout="wide")
st.title("🏆 Gestionale & Contabilità Associazione Sportiva (Google Sheets)")

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
    
    atleti_attivi = len(df_atleti[df_atleti["attivo"] == True]) if not df_atleti.empty and "attivo" in df_atleti.columns else len(df_atleti)
    tot_entrate = df_pagamenti["importo"].sum() if not df_pagamenti.empty and "importo" in df_pagamenti.columns else 0.0
    tot_uscite = df_spese["importo"].sum() if not df_spese.empty and "importo" in df_spese.columns else 0.0
    saldo_netto = tot_entrate - tot_uscite
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Atleti Totali/Attivi", atleti_attivi)
    col2.metric("Totale Entrate", f"€ {tot_entrate:,.2f}")
    col3.metric("Totale Uscite", f"€ {tot_uscite:,.2f}")
    col4.metric("Saldo Cassa Netto", f"€ {saldo_netto:,.2f}")

# ------------------------------------------
# 2. ATLETI
# ------------------------------------------
elif menu == "🏃 Atleti":
    st.header("🏃 Gestione Atleti")
    tab1, tab2 = st.tabs(["📋 Elenco Atleti", "➕ Registra Nuovo Atleta"])
    
    with tab1:
        df_atleti = get_as_df("atleti")
        if not df_atleti.empty:
            st.dataframe(df_atleti, use_container_width=True)
        else:
            st.info("Nessun atleta registrato.")
            
    with tab2:
        with st.form("form_nuovo_atleta", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            nome = col_a.text_input("Nome *")
            cognome = col_b.text_input("Cognome *")
            cf = col_a.text_input("Codice Fiscale *").upper().strip()
            data_nascita = col_b.date_input("Data di Nascita", value=datetime.date(2005, 1, 1))
            email = col_a.text_input("Email")
            telefono = col_b.text_input("Telefono")
            
            if st.form_submit_button("Salva Atleta"):
                if nome and cognome and cf:
                    ws = sh.worksheet("atleti")
                    df_esistenti = get_as_df("atleti")
                    
                    # Controllo duplicato codice fiscale
                    if not df_esistenti.empty and "codice_fiscale" in df_esistenti.columns and cf in df_esistenti["codice_fiscale"].values:
                        st.error("Errore: Il Codice Fiscale inserito esiste già nel foglio.")
                    else:
                        # Trova un ID progressivo
                        nuovo_id = len(df_esistenti) + 1 if not df_esistenti.empty else 1
                        ws.append_row([nuovo_id, cf, nome, cognome, str(data_nascita), email, telefono, True])
                        st.success(f"Atleta {nome} {cognome} salvato con successo!")
                        st.rerun()
                else:
                    st.warning("Compila i campi obbligatori (Nome, Cognome, Codice Fiscale).")

# ------------------------------------------
# 3. CERTIFICATI MEDICI
# ------------------------------------------
elif menu == "📋 Certificati Medici":
    st.header("📋 Gestione Visite e Certificati Medici")
    tab1, tab2, tab3 = st.tabs(["⚠️ Certificati in Scadenza", "➕ Inserisci / Rinnova Certificato", "📚 Storico Certificati"])
    
    df_visite = get_as_df("visite_mediche")
    df_atleti = get_as_df("atleti")
    
    with tab1:
        giorni = st.slider("Mostra certificati in scadenza nei prossimi (giorni):", 15, 90, 60)
        oggi = datetime.date.today()
        limite = oggi + datetime.timedelta(days=giorni)
        
        if not df_visite.empty and not df_atleti.empty:
            # Uniamo i dati via pandas
            df_unito = pd.merge(df_visite, df_atleti, left_on="atleta_id", right_on="id", suffixes=('_visita', '_atleta'))
            df_unito["data_scadenza_dt"] = pd.to_datetime(df_unito["data_scadenza"]).dt.date
            
            filtrati = df_unito[df_unito["data_scadenza_dt"] <= limite].sort_values(by="data_scadenza")
            
            if not filtrati.empty:
                data_tabella = []
                for _, row in filtrati.iterrows():
                    giorni_rimanenti = (row["data_scadenza_dt"] - oggi).days
                    stato = "🔴 Scaduto" if giorni_rimanenti < 0 else ("🟡 In scadenza" if giorni_rimanenti <= 30 else "🟢 Valido")
                    data_tabella.append({
                        "Stato": stato,
                        "Atleta": f"{row['nome']} {row['cognome']}",
                        "Tipo Visita": row["tipo_visita"],
                        "Data Scadenza": row["data_scadenza"],
                        "Giorni Rimanenti": f"{giorni_rimanenti} giorni" if giorni_rimanenti >= 0 else f"Scaduto da {-giorni_rimanenti} giorni",
                        "Telefono": row["telefono"],
                        "Email": row["email"]
                    })
                st.dataframe(pd.DataFrame(data_tabella), use_container_width=True)
            else:
                st.success("Nessun certificato in scadenza nel periodo selezionato!")
        else:
            st.info("Dati insufficienti o nessun certificato registrato.")

    with tab2:
        if df_atleti.empty:
            st.warning("Devi prima inserire almeno un atleta.")
        else:
            mappa_atleti = {f"{row['nome']} {row['cognome']} ({row['codice_fiscale']})": row['id'] for _, row in df_atleti.iterrows()}
            with st.form("form_visita_medica", clear_on_submit=True):
                scelta_atleta = st.selectbox("Seleziona Atleta *", list(mappa_atleti.keys()))
                col_c1, col_c2 = st.columns(2)
                data_visita = col_c1.date_input("Data Effettuazione Visita", value=datetime.date.today())
                data_scadenza = col_c2.date_input("Data Scadenza Certificato", value=data_visita + datetime.timedelta(days=365))
                tipo_visita = col_c1.selectbox("Tipo Visita", ["Agonistica", "Non Agonistica", "Elettrocardiogramma"])
                idoneo = col_c2.checkbox("Idoneità Concessa", value=True)
                
                if st.form_submit_button("Salva Certificato Medico"):
                    atleta_id = mappa_atleti[scelta_atleta]
                    ws = sh.worksheet("visite_mediche")
                    nuovo_id = len(df_visite) + 1 if not df_visite.empty else 1
                    ws.append_row([nuovo_id, atleta_id, str(data_visita), str(data_scadenza), tipo_visita, idoneo])
                    st.success("Certificato medico registrato correttamente!")
                    st.rerun()

    with tab3:
        if not df_visite.empty and not df_atleti.empty:
            df_unito = pd.merge(df_visite, df_atleti, left_on="atleta_id", right_on="id")
            st.dataframe(df_unito[["tipo_visita", "data_visita", "data_scadenza", "idoneo", "nome", "cognome"]], use_container_width=True)
        else:
            st.info("Nessun certificato presente in archivio.")

# ------------------------------------------
# 4. ENTRATE / QUOTE
# ------------------------------------------
elif menu == "💳 Entrate (Quote Atleti)":
    st.header("💳 Registro Incassi Quote")
    tab1, tab2 = st.tabs(["📋 Elenco Incassi", "➕ Registra Incasso Quota"])
    
    df_pagamenti = get_as_df("pagamenti")
    df_atleti = get_as_df("atleti")
    
    with tab1:
        if not df_pagamenti.empty and not df_atleti.empty:
            df_unito = pd.merge(df_pagamenti, df_atleti, left_on="atleta_id", right_on="id")
            st.dataframe(df_unito[["data_pagamento", "nome", "cognome", "causale", "importo", "metodo"]], use_container_width=True)
        else:
            st.info("Nessun incasso registrato.")
            
    with tab2:
        if df_atleti.empty:
            st.warning("Devi prima registrare almeno un atleta.")
        else:
            mappa_atleti = {f"{row['nome']} {row['cognome']} ({row['codice_fiscale']})": row['id'] for _, row in df_atleti.iterrows()}
            with st.form("form_incasso", clear_on_submit=True):
                scelta_atleta = st.selectbox("Seleziona Atleta", list(mappa_atleti.keys()))
                causale = st.text_input("Causale (es. Quota Mese)")
                importo = st.number_input("Importo (€)", min_value=1.0, step=5.0)
                metodo = st.selectbox("Metodo di Pagamento", ["Bonifico", "Contanti", "POS / Carta"])
                data_pag = st.date_input("Data Pagamento", value=datetime.date.today())
                
                if st.form_submit_button("Registra Incasso"):
                    atleta_id = mappa_atleti[scelta_atleta]
                    ws = sh.worksheet("pagamenti")
                    nuovo_id = len(df_pagamenti) + 1 if not df_pagamenti.empty else 1
                    ws.append_row([nuovo_id, atleta_id, str(data_pag), importo, causale, metodo])
                    st.success("Pagamento registrato correttamente!")
                    st.rerun()

# ------------------------------------------
# 5. USCITE / SPESE GENERALI
# ------------------------------------------
elif menu == "💸 Uscite (Spese Generali)":
    st.header("💸 Gestione Spese Generali dell'Associazione")
    tab1, tab2 = st.tabs(["📋 Elenco Uscite", "➕ Registra Nuova Spesa"])
    
    df_spese = get_as_df("spese_generali")
    
    with tab1:
        if not df_spese.empty:
            st.dataframe(df_spese, use_container_width=True)
        else:
            st.info("Nessuna spesa registrata.")
            
    with tab2:
        with st.form("form_spesa", clear_on_submit=True):
            col_1, col_2 = st.columns(2)
            descrizione = col_1.text_input("Descrizione Spesa")
            categoria = col_2.selectbox("Categoria", ["Affitto Palestra", "Utenze", "Istruttori", "Materiale", "Altro"])
            importo = col_1.number_input("Importo (€)", min_value=0.01, step=10.0)
            data_spesa = col_2.date_input("Data del Pagamento", value=datetime.date.today())
            fornitore = col_1.text_input("Fornitore")
            metodo = col_2.selectbox("Metodo Pagamento", ["Bonifico", "Carta / POS", "Contanti"])
            
            if st.form_submit_button("Salva Spesa"):
                if descrizione and importo > 0:
                    ws = sh.worksheet("spese_generali")
                    nuovo_id = len(df_spese) + 1 if not df_spese.empty else 1
                    ws.append_row([nuovo_id, descrizione, categoria, importo, str(data_spesa), fornitore, metodo])
                    st.success("Spesa registrata correttamente!")
                    st.rerun()
                else:
                    st.warning("Inserisci una descrizione e un importo valido.")
