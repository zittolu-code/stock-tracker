import streamlit as st
import yfinance as yf
import pandas as pd
from google import genai

st.set_page_config(page_title="Stock Value Tracker", layout="wide")

st.title("📈 Prossimi Ingressi - Stock Value Tracker")

# Elenco completo dei Ticker
TICKERS = [
    "NVDA", "GOOGL", "MSFT", "AMZN", "BABA", "META", "AMD", "V", "ASML", 
    "MA", "PLTR", "SAP", "CRM", "ISRG", "NOW", "MELI", "RACE", "O", 
    "OKE", "NBIS", "CRWV", "CMG", "LDO.MI", "CRCL", "LYSCF", "IREN", 
    "TYL", "FIG", "MARA"
]

if st.button("🔄 Aggiorna Dati Live"):
    st.cache_data.clear()

@st.cache_data(ttl=3600)
def fetch_data(ticker_list):
    data_list = []
    
    for ticker in ticker_list:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            pe = info.get("trailingPE")
            market_cap = info.get("marketCap")
            fcf = info.get("freeCashflow")
            shares_outstanding = info.get("sharesOutstanding")
            
            basic_eps_ttm = None
            diluted_eps_ttm = None
            
            try:
                financials = stock.ttm_financials
                if financials is not None and not financials.empty:
                    if "Basic EPS" in financials.index:
                        val = financials.loc["Basic EPS"].iloc[0]
                        if pd.notna(val):
                            basic_eps_ttm = float(val)
                    
                    if "Diluted EPS" in financials.index:
                        val = financials.loc["Diluted EPS"].iloc[0]
                        if pd.notna(val):
                            diluted_eps_ttm = float(val)
            except Exception:
                pass
            
            if basic_eps_ttm is None and info.get("trailingEps") is not None:
                basic_eps_ttm = float(info.get("trailingEps"))
            if diluted_eps_ttm is None and info.get("trailingEps") is not None:
                diluted_eps_ttm = float(info.get("trailingEps"))

            fcf_per_share = None
            fcf_eps_ratio = None
            
            if isinstance(fcf, (int, float)) and isinstance(shares_outstanding, (int, float)) and shares_outstanding > 0:
                fcf_per_share = fcf / shares_outstanding
                
            if isinstance(fcf_per_share, (int, float)) and isinstance(diluted_eps_ttm, (int, float)) and diluted_eps_ttm > 0:
                fcf_eps_ratio = fcf_per_share / diluted_eps_ttm

            mc_billion = (market_cap / 1e9) if isinstance(market_cap, (int, float)) else None
            fcf_billion = (fcf / 1e9) if isinstance(fcf, (int, float)) else None
            
            data_list.append({
                "Azienda": info.get("shortName", ticker),
                "Ticker": ticker,
                "Prezzo ($)": price if isinstance(price, (int, float)) else None,
                "Basic EPS TTM ($)": basic_eps_ttm,
                "Diluted EPS TTM ($)": diluted_eps_ttm,
                "P/E": pe if isinstance(pe, (int, float)) else None,
                "Market Cap ($B)": mc_billion,
                "Free Cash Flow ($B)": fcf_billion,
                "FCF/EPS Ratio": fcf_eps_ratio
            })
        except Exception:
            data_list.append({
                "Azienda": ticker,
                "Ticker": ticker,
                "Prezzo ($)": None,
                "Basic EPS TTM ($)": None,
                "Diluted EPS TTM ($)": None,
                "P/E": None,
                "Market Cap ($B)": None,
                "Free Cash Flow ($B)": None,
                "FCF/EPS Ratio": None
            })
            
    return pd.DataFrame(data_list)

with st.spinner("Recupero dati finanziari..."):
    df = fetch_data(TICKERS)

def highlight_fcf_ratio(val):
    if pd.isna(val) or val is None:
        return ''
    elif val > 1.0:
        return 'background-color: #2e7d32; color: white; font-weight: bold;'
    else:
        return 'background-color: #c62828; color: white; font-weight: bold;'

styled_df = df.style.map(highlight_fcf_ratio, subset=['FCF/EPS Ratio'])\
                    .format({
                        "Prezzo ($)": "${:,.2f}",
                        "Basic EPS TTM ($)": "${:,.2f}",
                        "Diluted EPS TTM ($)": "${:,.2f}",
                        "P/E": "{:,.2f}",
                        "Market Cap ($B)": "${:,.2f} B",
                        "Free Cash Flow ($B)": "${:,.2f} B",
                        "FCF/EPS Ratio": "{:,.2f}"
                    }, na_rep="N/A")

st.dataframe(styled_df, use_container_width=True)

# -------------------------------------------------------------
# INTEGRAZIONE ASSISTENTE GEMINI
# -------------------------------------------------------------
st.markdown("---")
st.subheader("🤖 Assistente Finanziario Gemini")

# Recupero della chiave API dai secrets di Streamlit
api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.info("💡 Per attivare l'assistente, inserisci la tua GEMINI_API_KEY nei Secrets di Streamlit Cloud.")
else:
    user_prompt = st.text_input("Fai una domanda sui dati della tabella (es: 'Analizza le 3 aziende con FCF/EPS Ratio migliore'):")
    
    if st.button("✨ Chiedi a Gemini") and user_prompt:
        with st.spinner("Gemini sta analizzando i dati..."):
            try:
                client = genai.Client(api_key=api_key)
                
                # Prepariamo i dati della tabella in testo da passare al contesto
                table_context = df.to_csv(index=False)
                
                prompt = f"""
                Sei un analista finanziario esperto. Analizza la seguente tabella di dati di bilancio:
                
                {table_context}
                
                Rispondi alla seguente domanda dell'utente fornendo un'analisi sintetica e professionale:
                {user_prompt}
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                
                st.markdown("### Risposta di Gemini:")
                st.write(response.text)
                
            except Exception as e:
                st.error(f"Errore durante la comunicazione con Gemini: {e}")
