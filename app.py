import streamlit as st
import yfinance as yf
import pandas as pd
import json
import pypdf
import google.generativeai as genai

# ---------------------------------------------------------
# CONFIGURAZIONE PAGINA STREAMLIT
# ---------------------------------------------------------
st.set_page_config(page_title="Stock Value & Forensics Tracker", layout="wide")
st.title("📈 Stock Value Tracker & Financial Forensics Analyst")

# Lista Ticker di default
TICKERS = [
    "NVDA", "GOOGL", "MSFT", "AMZN", "BABA", "META", "AMD", "V", "ASML", 
    "MA", "PLTR", "SAP", "CRM", "ISRG", "NOW", "MELI", "RACE", "O", 
    "OKE", "NBIS", "CRWV", "CMG", "LDO.MI", "CRCL", "LYSCF", "IREN", 
    "TYL", "FIG", "MARA"
]

# Inizializzazione session state per memorizzare i report di forensic accounting
if "forensic_data" not in st.session_state:
    st.session_state.forensic_data = {}

# ---------------------------------------------------------
# PROMPT SISTEMA: Financial Forensics & Equity Analyst
# ---------------------------------------------------------
SYSTEM_INSTRUCTION = """
Sei "Financial Forensics & Equity Analyst", un analista finanziario senior ed esperto in contabilità aziendale (Corporate Finance / Forensic Accounting) specializzato nella lettura critica delle trimestrali (10-Q), dei report annuali (10-K / Bilanci d'Esercizio) e dei documenti finanziari di società quotate (US GAAP e IFRS).

Il tuo obiettivo principale non è solo riassumere i dati, ma condurre un'analisi fondamentale rigorosa e individuare qualsiasi "insidia contabile" (red flag), manipolazione lecita ma fuorviante delle metriche, o rischio nascosto tra le righe.

APPROCCIO ANALITICO:
1. Scetticismo Professionale: Guarda oltre le metriche adjusted ("Non-GAAP") e i commenti ottimistici del management.
2. Rigoroso e Quantitativo: Basa ogni conclusione su numeri, indici di bilancio e confronti temporali o settoriali.
3. Incroccio dei Dati: Correla sempre Conto Economico, Stato Patrimoniale e Rendiconto Finanziario per verificare la qualità degli utili.
"""

# ---------------------------------------------------------
# FUNZIONE PER ESTRARRE TESTO DA PDF MULTIPLI
# ---------------------------------------------------------
def extract_text_from_pdfs(uploaded_files):
    combined_text = ""
    for idx, file in enumerate(uploaded_files):
        try:
            reader = pypdf.PdfReader(file)
            combined_text += f"\n--- INIZIO DOCUMENTO {idx+1}: {file.name} ---\n"
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    combined_text += text + "\n"
        except Exception as e:
            st.warning(f"Avviso durante la lettura di {file.name}: {e}")
    return combined_text

# ---------------------------------------------------------
# FUNZIONE ANALISI CON GEMINI (gemini-2.5-flash-lite)
# ---------------------------------------------------------
def analyze_reports_with_gemini(ticker, uploaded_files):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ Nessuna GEMINI_API_KEY trovata nei Secrets di Streamlit! Configurala nelle impostazioni dell'app.")
        return None

    try:
        # Configurazione chiave API
        genai.configure(api_key=api_key.strip('"\' '))

        # Inizializzazione del modello Gemini 2.5 Flash-Lite
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            system_instruction=SYSTEM_INSTRUCTION,
            generation_config={
                "response_mime_type": "application/json", 
                "temperature": 0.2
            }
        )

        # Estrazione e troncamento di sicurezza del testo estratto dai PDF
        pdf_text = extract_text_from_pdfs(uploaded_files)
        truncated_text = pdf_text[:120000]

        prompt_text = f"""
        Esegui l'analisi di Forensic Accounting per la società con ticker: {ticker}.
        Ecco il testo estratto dai report finanziari/trimestrali caricati:

        --- INIZIO TESTO REPORT ---
        {truncated_text}
        --- FINE TESTO REPORT ---

        Calcola ed estrai rigorosamente l'EPS Diluito Normalizzato TTM (depurato da componenti straordinarie, non ricorrenti, o da voci contabili distorsive).

        Restituisci un JSON valido con ESATTAMENTE le seguenti chiavi:
        {{
          "normalized_diluted_eps_ttm": float, # Valore calcolato dell'EPS Diluito Normalizzato TTM
          "forensic_score": float, # Punteggio da 1.0 a 10.0 sulla trasparenza contabile
          "quality_of_earnings": "string", # Esempi: "Alta (Cash Backed)", "Media", "Bassa (Aggressive/SBC)"
          "main_red_flag": "string", # Sintesi della principale insidia o rischio contabile
          "summary_verdict": "string", # Giudizio sintetico dell'Analista
          "full_report_markdown": "string" # Report completo e dettagliato formattato in Markdown secondo lo schema in 4 punti dell'Analista
        }}
        """

        response = model.generate_content(prompt_text)
        data = json.loads(response.text)
        return data

    except Exception as e:
        st.error(f"❌ Errore durante l'analisi con Gemini: {str(e)}")
        return None

# ---------------------------------------------------------
# BARRA LATERALE: MULTI-UPLOAD PDF & ANALISI
# ---------------------------------------------------------
st.sidebar.header("🔍 Modulo Forensic Accounting")
selected_ticker = st.sidebar.selectbox("Seleziona Ticker dell'Azienda", TICKERS)

uploaded_files = st.sidebar.file_uploader(
    "Carica Report Trimestrali (PDF multipli)", 
    type=["pdf"], 
    accept_multiple_files=True
)

if st.sidebar.button("🧪 Analizza Report con GEM Analista"):
    if uploaded_files:
        with st.spinner(f"Elaborazione PDF e analisi in corso con Gemini 2.5 Flash-Lite per {selected_ticker}..."):
            analysis_result = analyze_reports_with_gemini(selected_ticker, uploaded_files)
            if analysis_result:
                st.session_state.forensic_data[selected_ticker] = analysis_result
                st.sidebar.success(f"Analisi per {selected_ticker} completata con successo!")
    else:
        st.sidebar.warning("Seleziona uno o più file PDF prima di avviare l'analisi.")

# ---------------------------------------------------------
# TABELLA DATI LIVE (YAHOO FINANCE + GEMINI FORENSICS)
# ---------------------------------------------------------
if st.button("🔄 Aggiorna Dati Live (Yahoo Finance)"):
    st.cache_data.clear()

@st.cache_data(ttl=3600)
def fetch_yahoo_data(ticker_list):
    data_list = []
    for ticker in ticker_list:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            pe = info.get("trailingPE")
            market_cap = info.get("marketCap")
            fcf = info.get("freeCashflow")
            
            basic_eps_ttm = None
            diluted_eps_ttm = None
            try:
                financials = stock.ttm_financials
                if financials is not None and not financials.empty:
                    if "Basic EPS" in financials.index and pd.notna(financials.loc["Basic EPS"].iloc[0]):
                        basic_eps_ttm = float(financials.loc["Basic EPS"].iloc[0])
                    if "Diluted EPS" in financials.index and pd.notna(financials.loc["Diluted EPS"].iloc[0]):
                        diluted_eps_ttm = float(financials.loc["Diluted EPS"].iloc[0])
            except Exception:
                pass
            
            if basic_eps_ttm is None and info.get("trailingEps") is not None:
                basic_eps_ttm = float(info.get("trailingEps"))
            if diluted_eps_ttm is None and info.get("trailingEps") is not None:
                diluted_eps_ttm = float(info.get("trailingEps"))

            mc_billion = (market_cap / 1e9) if isinstance(market_cap, (int, float)) else None
            fcf_billion = (fcf / 1e9) if isinstance(fcf, (int, float)) else None
            
            # Unione con i dati elaborati da Gemini in session_state
            forensic_info = st.session_state.forensic_data.get(ticker, {})
            
            data_list.append({
                "Azienda": info.get("shortName", ticker),
                "Ticker": ticker,
                "Prezzo ($)": price if isinstance(price, (int, float)) else None,
                "Basic EPS TTM ($)": basic_eps_ttm,
                "Diluted EPS TTM ($)": diluted_eps_ttm,
                "EPS Diluito Normalizzato TTM ($)": forensic_info.get("normalized_diluted_eps_ttm", None),
                "P/E": pe if isinstance(pe, (int, float)) else None,
                "Market Cap ($B)": mc_billion,
                "Free Cash Flow ($B)": fcf_billion,
                "Forensic Score": forensic_info.get("forensic_score", None),
                "Quality of Earnings": forensic_info.get("quality_of_earnings", "N/A"),
                "Principale Red Flag": forensic_info.get("main_red_flag", "N/A"),
                "Verdetto Analista": forensic_info.get("summary_verdict", "N/A")
            })
        except Exception:
            data_list.append({
                "Azienda": ticker, "Ticker": ticker, "Prezzo ($)": None,
                "Basic EPS TTM ($)": None, "Diluted EPS TTM ($)": None,
                "EPS Diluito Normalizzato TTM ($)": None, "P/E": None,
                "Market Cap ($B)": None, "Free Cash Flow ($B)": None,
                "Forensic Score": None, "Quality of Earnings": "N/A",
                "Principale Red Flag": "N/A", "Verdetto Analista": "N/A"
            })
            
    return pd.DataFrame(data_list)

with st.spinner("Scaricamento dati finanziari e unione analisi in corso..."):
    df = fetch_yahoo_data(TICKERS)

# Visualizzazione Tabella Principale
st.dataframe(
    df,
    use_container_width=True,
    column_config={
        "Prezzo ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Basic EPS TTM ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Diluted EPS TTM ($)": st.column_config.NumberColumn(format="$%.2f"),
        "EPS Diluito Normalizzato TTM ($)": st.column_config.NumberColumn(format="$%.2f"),
        "P/E": st.column_config.NumberColumn(format="%.2f"),
        "Market Cap ($B)": st.column_config.NumberColumn(format="$%.2f B"),
        "Free Cash Flow ($B)": st.column_config.NumberColumn(format="$%.2f B"),
        "Forensic Score": st.column_config.NumberColumn(format="%.1f / 10"),
    }
)

# ---------------------------------------------------------
# SEZIONE REPORT STAMPABILE ESTESO
# ---------------------------------------------------------
st.markdown("---")
st.header("📄 Report Forensics Dettagliato")

available_reports = list(st.session_state.forensic_data.keys())
if available_reports:
    selected_report_ticker = st.selectbox("Seleziona un'azienda per consultare il Report dell'Analista:", available_reports)
    if selected_report_ticker in st.session_state.forensic_data:
        report_md = st.session_state.forensic_data[selected_report_ticker]["full_report_markdown"]
        st.markdown(report_md)
else:
    st.info("💡 Nessun report PDF ancora analizzato. Carica uno o più file PDF dalla barra laterale per avviare il tuo Analista Finanziario AI!")
