import streamlit as st
import yfinance as yf
import pandas as pd
import json
import pypdf
import google.generativeai as genai

# Configurazione Pagina Streamlit
st.set_page_config(page_title="Stock Value & Forensics Tracker", layout="wide")
st.title("📈 Stock Value Tracker & Financial Forensics Analyst")

# Lista Ticker
TICKERS = [
    "NVDA", "GOOGL", "MSFT", "AMZN", "BABA", "META", "AMD", "V", "ASML", 
    "MA", "PLTR", "SAP", "CRM", "ISRG", "NOW", "MELI", "RACE", "O", 
    "OKE", "NBIS", "CRWV", "CMG", "LDO.MI", "CRCL", "LYSCF", "IREN", 
    "TYL", "FIG", "MARA"
]

# Inizializzazione session state
if "forensic_data" not in st.session_state:
    st.session_state.forensic_data = {}

# Prompt Financial Forensics & Equity Analyst
SYSTEM_INSTRUCTION = """
Sei "Financial Forensics & Equity Analyst", un analista finanziario senior ed esperto in contabilità aziendale (Corporate Finance / Forensic Accounting) specializzato nella lettura critica delle trimestrali (10-Q), dei report annuali (10-K / Bilanci d'Esercizio) e dei documenti finanziari di società quotate (US GAAP e IFRS).

Il tuo obiettivo principale non è solo riassumere i dati, ma condurre un'analisi fondamentale rigorosa e individuare qualsiasi "insidia contabile" (red flag), manipolazione lecita ma fuorviante delle metriche, o rischio nascosto tra le righe.

APPROCCIO ANALITICO:
1. Scetticismo Professionale: Guarda oltre le metriche adjusted ("Non-GAAP") e i commenti ottimistici del management.
2. Rigoroso e Quantitativo: Basa ogni conclusione su numeri, indici di bilancio e confronti temporali o settoriali.
3. Incroccio dei Dati: Correla sempre Conto Economico, Stato Patrimoniale e Rendiconto Finanziario per verificare la qualità degli utili.
"""

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
            st.warning(f"Avviso lettura file {file.name}: {e}")
    return combined_text

def analyze_reports_with_gemini(ticker, uploaded_files):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("⚠️ Nessuna GEMINI_API_KEY trovata nei Secrets di Streamlit!")
        return None

    try:
        # Configurazione API Key
        genai.configure(api_key=api_key.strip('"\' '))

        # Configurazione del modello Gemini 1.5 Flash con System Instruction
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=SYSTEM_INSTRUCTION,
            generation_config={"response_mime_type": "application/json", "temperature": 0.2}
        )

        # Estrazione del testo e troncamento a 100k caratteri per garantire la massima velocità nel piano gratuito
        pdf_text = extract_text_from_pdfs(uploaded_files)
        truncated_text = pdf_text[:100000]

        prompt_text = f"""
        Esegui l'analisi di Forensic Accounting per la società con ticker: {ticker}.
        Ecco il testo estratto dai report finanziari caricati:

        --- INIZIO TESTO ---
        {truncated_text}
        --- FINE TESTO ---

        Calcola ed estrai rigorosamente l'EPS Diluito Normalizzato TTM (depurato da componenti straordinarie, non ricorrenti, o da voci contabili distorsive).

        Restituisci un JSON valido esattamente con queste chiavi:
        {{
          "normalized_diluted_eps_ttm": float,
          "forensic_score": float,
          "quality_of_earnings": "string",
          "main_red_flag": "string",
          "summary_verdict": "string",
          "full_report_markdown": "string"
        }}
        """

        response = model.generate_content(prompt_text)
        data = json.loads(response.text)
        return data

    except Exception as e:
        st.error(f"❌ Errore durante l'analisi con Gemini: {str(e)}")
        return None

# Sidebar Upload
st.sidebar.header("🔍 Modulo Forensic Accounting")
selected_ticker = st.sidebar.selectbox("Seleziona Ticker dell'Azienda", TICKERS)

uploaded_files = st.sidebar.file_uploader(
    "Carica Report Trimestrali (PDF multipli)", 
    type=["pdf"], 
    accept_multiple_files=True
)

if st.sidebar.button("🧪 Analizza Report con GEM Analista"):
    if uploaded_files:
        with st.spinner(f"Analisi in corso per {selected_ticker}..."):
            analysis_result = analyze_reports_with_gemini(selected_ticker, uploaded_files)
            if analysis_result:
                st.session_state.forensic_data[selected_ticker] = analysis_result
                st.sidebar.success(f"Analisi per {selected_ticker} completata!")
    else:
        st.sidebar.warning("Seleziona almeno un PDF prima di procedere.")

# Fetch Yahoo Finance Data
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

# Visualizzazione Dataframe
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

# Report Dettagliato
st.markdown("---")
st.header("📄 Report Forensics Dettagliato")

available_reports = list(st.session_state.forensic_data.keys())
if available_reports:
    selected_report_ticker = st.selectbox("Seleziona un'azienda per leggere il Report dell'Analista:", available_reports)
    if selected_report_ticker in st.session_state.forensic_data:
        report_md = st.session_state.forensic_data[selected_report_ticker]["full_report_markdown"]
        st.markdown(report_md)
else:
    st.info("💡 Nessun report PDF ancora analizzato. Carica uno o più file PDF dalla barra laterale per avviare il tuo Analista Finanziario AI!")
# --- PULSANTE TEMPORANEO PER VEDERE I MODELLI DISPONIBILI ---
if st.sidebar.button("🔍 Mostra Modelli Disponibili"):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        try:
            genai.configure(api_key=api_key.strip('"\' '))
            st.sidebar.write("### Modelli supportati:")
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    st.sidebar.code(m.name)
        except Exception as e:
            st.sidebar.error(f"Errore: {e}")
    else:
        st.sidebar.error("Manca GEMINI_API_KEY nei Secrets!")
