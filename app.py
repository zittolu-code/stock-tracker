import streamlit as st
import yfinance as yf
import pandas as pd

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
            
            # Prezzo e altre metriche generali
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            pe = info.get("trailingPE")
            market_cap = info.get("marketCap")
            fcf = info.get("freeCashflow")
            
            # Recupero dati TTM dal conto economico (Financials)
            basic_eps_ttm = None
            diluted_eps_ttm = None
            
            try:
                # Estrazione del prospetto contabile TTM
                financials = stock.ttm_financials
                if financials is not None and not financials.empty:
                    # Estrazione Basic EPS TTM
                    if "Basic EPS" in financials.index:
                        val = financials.loc["Basic EPS"].iloc[0]
                        if pd.notna(val):
                            basic_eps_ttm = float(val)
                    
                    # Estrazione Diluted EPS TTM
                    if "Diluted EPS" in financials.index:
                        val = financials.loc["Diluted EPS"].iloc[0]
                        if pd.notna(val):
                            diluted_eps_ttm = float(val)
            except Exception:
                pass
            
            # Fallback a trailingEps in info se la tabella financials TTM non fosse disponibile
            if basic_eps_ttm is None and info.get("trailingEps") is not None:
                basic_eps_ttm = float(info.get("trailingEps"))
            if diluted_eps_ttm is None and info.get("trailingEps") is not None:
                diluted_eps_ttm = float(info.get("trailingEps"))

            # Conversione in miliardi per Market Cap e Free Cash Flow
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
                "Free Cash Flow ($B)": fcf_billion
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
                "Free Cash Flow ($B)": None
            })
            
    return pd.DataFrame(data_list)

with st.spinner("Recupero rendiconti finanziari (Financials TTM) da Yahoo Finance..."):
    df = fetch_data(TICKERS)

# Configurazione della visualizzazione con supporto al sorting numerico
st.dataframe(
    df,
    use_container_width=True,
    column_config={
        "Prezzo ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Basic EPS TTM ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Diluted EPS TTM ($)": st.column_config.NumberColumn(format="$%.2f"),
        "P/E": st.column_config.NumberColumn(format="%.2f"),
        "Market Cap ($B)": st.column_config.NumberColumn(format="$%.2f B"),
        "Free Cash Flow ($B)": st.column_config.NumberColumn(format="$%.2f B"),
    }
)
