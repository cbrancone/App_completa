import streamlit as st
import datetime
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Boolean, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# ==========================================
# 1. CONFIGURAZIONE DATABASE
# ==========================================
DB_NAME = "associazione_sportiva.db"
engine = create_engine(f"sqlite:///{DB_NAME}", echo=False)
Base = declarative_base()

class Atleta(Base):
    __tablename__ = 'atleti'
    id = Column(Integer, primary_key=True, autoincrement=True)
    codice_fiscale = Column(String(16), unique=True, nullable=False)
    nome = Column(String(50), nullable=False)
    cognome = Column(String(50), nullable=False)
    data_nascita = Column(Date, nullable=False)
    email = Column(String(100))
    telefono = Column(String(20))
    attivo = Column(Boolean, default=True)
    
    visite_mediche = relationship("VisitaMedica", back_populates="atleta", cascade="all, delete-orphan")
    iscrizioni = relationship("IscrizioneCorso", back_populates="atleta", cascade="all, delete-orphan")
    pagamenti = relationship("Pagamento", back_populates="atleta", cascade="all, delete-orphan")

class Corso(Base):
    __tablename__ = 'corsi'
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome_corso = Column(String(100), nullable=False)
    istruttore = Column(String(100))
    quota_mensile = Column(Float, nullable=False)
    iscrizioni = relationship("IscrizioneCorso", back_populates="corso")

class IscrizioneCorso(Base):
    __tablename__ = 'iscrizioni_corsi'
    id = Column(Integer, primary_key=True, autoincrement=True)
    atleta_id = Column(Integer, ForeignKey('atleti.id'), nullable=False)
    corso_id = Column(Integer, ForeignKey('corsi.id'), nullable=False)
    data_iscrizione = Column(Date, default=datetime.date.today)
    atleta = relationship("Atleta", back_populates="iscrizioni")
    corso = relationship("Corso", back_populates="iscrizioni")

class VisitaMedica(Base):
    __tablename__ = 'visite_mediche'
    id = Column(Integer, primary_key=True, autoincrement=True)
    atleta_id = Column(Integer, ForeignKey('atleti.id'), nullable=False)
    data_visita = Column(Date, nullable=False)
    data_scadenza = Column(Date, nullable=False)
    tipo_visita = Column(String(50), default="Agonistica")
    idoneo = Column(Boolean, default=True)
    atleta = relationship("Atleta", back_populates="visite_mediche")

class Pagamento(Base):
    __tablename__ = 'pagamenti'
    id = Column(Integer, primary_key=True, autoincrement=True)
    atleta_id = Column(Integer, ForeignKey('atleti.id'), nullable=False)
    data_pagamento = Column(Date, default=datetime.date.today)
    importo = Column(Float, nullable=False)
    causale = Column(String(200), nullable=False)
    metodo = Column(String(50))
    atleta = relationship("Atleta", back_populates="pagamenti")

class SpesaGenerale(Base):
    __tablename__ = 'spese_generali'
    id = Column(Integer, primary_key=True, autoincrement=True)
    descrizione = Column(String(200), nullable=False)
    categoria = Column(String(100), nullable=False)
    importo = Column(Float, nullable=False)
    data_spesa = Column(Date, default=datetime.date.today)
    fornitore = Column(String(100))
    metodo_pagamento = Column(String(50))

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ==========================================
# 2. INTERFACCIA STREAMLIT
# ==========================================
st.set_page_config(page_title="Gestionale Associazione Sportiva", page_icon="🏆", layout="wide")
st.title("🏆 Gestionale & Contabilità Associazione Sportiva")

st.sidebar.title("Navigazione")
menu = st.sidebar.radio("Scegli Sezione:", [
    "📊 Dashboard & Bilancio", 
    "🏃 Atleti", 
    "📋 Certificati Medici", 
    "💳 Entrate (Quote Atleti)", 
    "💸 Uscite (Spese Generali)"
])

session = Session()

# ------------------------------------------
# 1. DASHBOARD & BILANCIO
# ------------------------------------------
if menu == "📊 Dashboard & Bilancio":
    st.header("📊 Panoramica Economica e Operativa")
    
    tot_entrate = session.query(func.sum(Pagamento.importo)).scalar() or 0.0
    tot_uscite = session.query(func.sum(SpesaGenerale.importo)).scalar() or 0.0
    saldo_netto = tot_entrate - tot_uscite
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Atleti Attivi", session.query(Atleta).filter_by(attivo=True).count())
    col2.metric("Totale Entrate", f"€ {tot_entrate:,.2f}")
    col3.metric("Totale Uscite", f"€ {tot_uscite:,.2f}")
    col4.metric("Saldo Cassa Netto", f"€ {saldo_netto:,.2f}")

# ------------------------------------------
# 2. ATLETI (CON FORM NUOVO ATLETA)
# ------------------------------------------
elif menu == "🏃 Atleti":
    st.header("🏃 Gestione Atleti")
    tab1, tab2 = st.tabs(["📋 Elenco Atleti", "➕ Registra Nuovo Atleta"])
    
    with tab1:
        atleti = session.query(Atleta).all()
        if atleti:
            st.dataframe(pd.DataFrame([{"ID": a.id, "Nome": a.nome, "Cognome": a.cognome, "CF": a.codice_fiscale, "Telefono": a.telefono} for a in atleti]), use_container_width=True)
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
                    try:
                        nuovo = Atleta(nome=nome, cognome=cognome, codice_fiscale=cf, data_nascita=data_nascita, email=email, telefono=telefono)
                        session.add(nuovo)
                        session.commit()
                        st.success(f"Atleta {nome} {cognome} salvato con successo!")
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error("Errore: Il Codice Fiscale inserito esiste già nel database.")
                else:
                    st.warning("Compila i campi obbligatori (Nome, Cognome, Codice Fiscale).")

# ------------------------------------------
# 3. CERTIFICATI MEDICI
# ------------------------------------------
# ------------------------------------------
# 3. CERTIFICATI MEDICI
# ------------------------------------------
elif menu == "📋 Certificati Medici":
    st.header("📋 Gestione Visite e Certificati Medici")
    tab1, tab2, tab3 = st.tabs(["⚠️ Certificati in Scadenza", "➕ Inserisci / Rinnova Certificato", "📚 Storico Certificati"])
    
    with tab1:
        giorni = st.slider("Mostra certificati in scadenza nei prossimi (giorni):", 15, 90, 60)
        limite = datetime.date.today() + datetime.timedelta(days=giorni)
        
        query = session.query(Atleta, VisitaMedica).join(VisitaMedica).filter(
            VisitaMedica.data_scadenza <= limite
        ).order_by(VisitaMedica.data_scadenza.asc()).all()
        
        if query:
            st.warning(f"Trovati {len(query)} certificati scaduti o in scadenza!")
            
            # Preparazione dei dati con i "semafori"
            data_tabella = []
            oggi = datetime.date.today()
            
            for a, v in query:
                giorni_rimanenti = (v.data_scadenza - oggi).days
                
                # Logica del semaforo
                if giorni_rimanenti < 0:
                    stato_semaforo = "🔴 Scaduto"
                elif giorni_rimanenti <= 30:
                    stato_semaforo = "🟡 In scadenza"
                else:
                    stato_semaforo = "🟢 Valido"
                
                data_tabella.append({
                    "Stato": stato_semaforo,
                    "Atleta": f"{a.nome} {a.cognome}",
                    "Tipo Visita": v.tipo_visita,
                    "Data Scadenza": v.data_scadenza,
                    "Giorni Rimanenti": f"{giorni_rimanenti} giorni" if giorni_rimanenti >= 0 else f"Scaduto da {-giorni_rimanenti} giorni",
                    "Telefono": a.telefono,
                    "Email": a.email
                })
                
            st.dataframe(pd.DataFrame(data_tabella), use_container_width=True)
        else:
            st.success("Nessun certificato in scadenza nel periodo selezionato!")

    with tab2:
        atleti_list = session.query(Atleta).all()
        if not atleti_list:
            st.warning("Devi prima inserire almeno un atleta per poter registrare un certificato medico.")
        else:
            mappa_atleti = {f"{a.nome} {a.cognome} ({a.codice_fiscale})": a.id for a in atleti_list}
            with st.form("form_visita_medica", clear_on_submit=True):
                scelta_atleta = st.selectbox("Seleziona Atleta *", list(mappa_atleti.keys()))
                
                col_c1, col_c2 = st.columns(2)
                data_visita = col_c1.date_input("Data Effettuazione Visita", value=datetime.date.today())
                
                # Calcola automaticamente la scadenza ad 1 anno dopo la visita
                sc scadenza_predefinita = data_visita + datetime.timedelta(days=365)
                data_scadenza = col_c2.date_input("Data Scadenza Certificato", value=scadenza_predefinita)
                
                tipo_visita = col_c1.selectbox("Tipo Visita", ["Agonistica", "Non Agonistica", "Elettrocardiogramma"])
                idoneo = col_c2.checkbox("Idoneità Concessa", value=True)
                
                if st.form_submit_button("Salva Certificato Medico"):
                    atleta_id = mappa_atleti[scelta_atleta]
                    nuova_visita = VisitaMedica(
                        atleta_id=atleta_id,
                        data_visita=data_visita,
                        data_scadenza=data_scadenza,
                        tipo_visita=tipo_visita,
                        idoneo=idoneo
                    )
                    session.add(nuova_visita)
                    session.commit()
                    st.success("Certificato medico registrato correttamente!")
                    st.rerun()

    with tab3:
        visite_tutte = session.query(VisitaMedica, Atleta).join(Atleta).order_by(VisitaMedica.data_scadenza.desc()).all()
        if visite_tutte:
            data_storico = []
            oggi = datetime.date.today()
            
            for v, a in visite_tutte:
                giorni_rimanenti = (v.data_scadenza - oggi).days
                if giorni_rimanenti < 0:
                    stato_semaforo = "🔴 Scaduto"
                elif giorni_rimanenti <= 30:
                    stato_semaforo = "🟡 In scadenza"
                else:
                    stato_semaforo = "🟢 Valido"
                    
                data_storico.append({
                    "Stato": stato_semaforo,
                    "Atleta": f"{a.nome} {a.cognome}",
                    "Tipo Visita": v.tipo_visita,
                    "Data Visita": v.data_visita,
                    "Data Scadenza": v.data_scadenza,
                    "Idoneo": "Sì" if v.idoneo else "No"
                })
                
            st.dataframe(pd.DataFrame(data_storico), use_container_width=True)
        else:
            st.info("Nessun certificato presente in archivio.")

# ------------------------------------------
# 5. USCITE / SPESE GENERALI (CON FORM NUOVA SPESA)
# ------------------------------------------
elif menu == "💸 Uscite (Spese Generali)":
    st.header("💸 Gestione Spese Generali dell'Associazione")
    tab1, tab2 = st.tabs(["📋 Elenco Uscite", "➕ Registra Nuova Spesa"])
    
    with tab1:
        spese = session.query(SpesaGenerale).order_by(SpesaGenerale.data_spesa.desc()).all()
        if spese:
            st.dataframe(pd.DataFrame([{"Data": s.data_spesa, "Descrizione": s.descrizione, "Categoria": s.categoria, "Importo (€)": s.importo, "Metodo": s.metodo_pagamento} for s in spese]), use_container_width=True)
        else:
            st.info("Nessuna spesa registrata.")
            
    with tab2:
        with st.form("form_spesa", clear_on_submit=True):
            col_1, col_2 = st.columns(2)
            descrizione = col_1.text_input("Descrizione Spesa (es. Affitto Palestra)")
            categoria = col_2.selectbox("Categoria", [
                "Affitto Impianti / Palestra", 
                "Utenze (Luce, Gas, Acqua)", 
                "Compensi Istruttori / Collaboratori", 
                "Attrezzatura e Materiale Sportivo", 
                "Assicurazioni e Tesseramenti Fed.", 
                "Commercialista e Spese Amministrative", 
                "Altro"
            ])
            importo = col_1.number_input("Importo (€)", min_value=0.01, step=10.0)
            data_spesa = col_2.date_input("Data del Pagamento", value=datetime.date.today())
            fornitore = col_1.text_input("Fornitore / Beneficiario")
            metodo = col_2.selectbox("Metodo Pagamento", ["Bonifico", "Carta / POS", "Contanti", "RID / Addebito Diretto"])
            
            if st.form_submit_button("Salva Spesa"):
                if descrizione and importo > 0:
                    nuova_spesa = SpesaGenerale(descrizione=descrizione, categoria=categoria, importo=importo, data_spesa=data_spesa, fornitore=fornitore, metodo_pagamento=metodo)
                    session.add(nuova_spesa)
                    session.commit()
                    st.success("Spesa registrata correttamente!")
                    st.rerun()
                else:
                    st.warning("Inserisci una descrizione e un importo valido.")

session.close()
