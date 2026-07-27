import streamlit as st
import yfinance as yf
import pandas as pd
import json
from pypdf import PdfReader
from google import genai
from google.genai import types

st.set_page_config(page_title="Stock Value & Forensics Tracker", layout="wide")

st.title("📈 Stock Value Tracker & Financial Forensics Analyst")

# Lista dei Ticker
TICKERS = [
    "NVDA", "GOOGL", "MSFT", "AMZN", "BABA", "META", "AMD", "V", "ASML", 
    "MA", "PLTR", "SAP", "CRM", "ISRG", "NOW", "MELI", "RACE", "O", 
    "OKE", "NBIS", "CRWV", "CMG", "LDO.MI", "CRCL", "LYSCF", "IREN", 
    "TYL", "FIG", "MARA"
]

# Inizializzazione della memoria di sessione per le analisi Forensics
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
# FUNZIONE PER ESTRARRE TESTO DA PDF
# ---------------------------------------------------------
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

# ---------------------------------------------------------
# FUNZIONE PER ESEGUIRE L'ANALISI FORENSICS CON GEMINI
# ---------------------------------------------------------
def analyze_report_with_gemini(ticker, pdf_text):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ Nessuna GEMINI_API_KEY trovata nei Secrets di Streamlit!")
        return None

    client = genai.Client(api_key=api_key)

    prompt = f"""
    Esegui l'analisi di Forensic Accounting per la società con ticker: {ticker}.
    Ecco il testo estratto dai documenti finanziari/trimestrali forniti:

    --- INIZIO DOCUMENTI ---
    {pdf_text[:150000]}  # Limite esteso per supportare più documenti/trimestri
    --- FINE DOCUMENTI ---

    Calcola ed estrai rigorosamente l'EPS Diluito Normalizzato TTM (depurato da componenti straordinarie, non ricorrenti, o da voci contabili distorsive).

    Restituisci un JSON strutturato esattamente con queste chiavi:
    {{
      "normalized_diluted_eps_ttm": float, # Valore calcolato dell'EPS Diluito Normalizzato TTM
      "forensic_score": float, # Voto da 1.0 a 10.0 sulla qualità e trasparenza contabile
      "quality_of_earnings": "string", # Esempi: "Alta (Cash Backed)", "Media", "Bassa (Aggressive/SBC)"
      "main_red_flag": "string", # Sintesi della principale insidia o rischio contabile emerso
      "summary_verdict": "string", # Sintesi breve del verdetto dell'Analista
      "full_report_markdown": "string" # Il report completo e dettagliato formattato in Markdown secondo i 4 punti dello schema dell'Analista
    }}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    try:
        data = json.loads(response.text)
        return data
    except Exception as e:
        st.error(f"Errore nella decodifica della risposta di Gemini: {e}")
        return None

# ---------------------------------------------------------
# BARRA LATERALE: MULTI-UPLOAD PDF & ANALISI GEMINI
# ---------------------------------------------------------
st.sidebar.header("🔍 Modulo Forensic Accounting")
selected_ticker = st.sidebar.selectbox("Seleziona Ticker dell'Azienda", TICKERS)

# Caricamento multiplo attivato impostando accept_multiple_files=True
uploaded_files = st.sidebar.file_uploader(
    "Carica Report Trimestrali (PDF multipli)", 
    type=["pdf"], 
    accept_multiple_files=True
)

if st.sidebar.button("🧪 Analizza tutti i Report con GEM Analista"):
    if uploaded_files:
        with st.spinner(f"Analisi Forensics in corso per {selected_ticker} su {len(uploaded_files)} file..."):
            combined_text = ""
            for idx, file in enumerate(uploaded_files):
                combined_text += f"\n--- DOCUMENTO {idx+1}: {file.name} ---\n"
                combined_text += extract_text_from_pdf(file)
            
            analysis_result = analyze_report_with_gemini(selected_ticker, combined_text)
            if analysis_result:
                st.session_state.forensic_data[selected_ticker] = analysis_result
                st.sidebar.success(f"Analisi per {selected_ticker} completata con successo!")
    else:
        st.sidebar.warning("Seleziona uno o più file PDF prima di avviare l'analisi.")

# ---------------------------------------------------------
# RECUPERO DATI YAHOO FINANCE
# ---------------------------------------------------------
if st.button("🔄 Aggiorna Dati Live"):
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

# Visualizzazione Tabella
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
# SEZIONE REPORT COMPLETO STAMPABILE
# ---------------------------------------------------------
st.markdown("---")
st.header("📄 Report Forensics Dettagliato")

available_reports = list(st.session_state.forensic_data.keys())
if available_reports:
    selected_report_ticker = st.selectbox("Seleziona un'azienda per leggere il Report Completo:", available_reports)
    if selected_report_ticker in st.session_state.forensic_data:
        report_md = st.session_state.forensic_data[selected_report_ticker]["full_report_markdown"]
        st.markdown(report_md)
else:
    st.info("💡 Nessun report PDF ancora analizzato in questa sessione. Carica uno o più file PDF dalla barra laterale per generare l'analisi!")
