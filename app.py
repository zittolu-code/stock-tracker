import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Stock Value Tracker", layout="wide")

st.title("📈 Stock Value Tracker")

# Tutti i 29 Ticker della tabella originale
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
            
            # Estrazione dei dati in formato NUMERICO (senza $ o stringhe)
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            eps = info.get("trailingEps")
            pe = info.get("trailingPE")
            market_cap = info.get("marketCap")
            fcf = info.get("freeCashflow")
            
            # Convertiamo in miliardi per renderli leggibili mantenendo il valore numerico
            mc_billion = (market_cap / 1e9) if isinstance(market_cap, (int, float)) else None
            fcf_billion = (fcf / 1e9) if isinstance(fcf, (int, float)) else None
            
            data_list.append({
                "Azienda": info.get("shortName", ticker),
                "Ticker": ticker,
                "Prezzo ($)": price if isinstance(price, (int, float)) else None,
                "EPS ($)": eps if isinstance(eps, (int, float)) else None,
                "P/E": pe if isinstance(pe, (int, float)) else None,
                "Market Cap ($B)": mc_billion,
                "Free Cash Flow ($B)": fcf_billion
            })
        except Exception:
            data_list.append({
                "Azienda": ticker,
                "Ticker": ticker,
                "Prezzo ($)": None,
                "EPS ($)": None,
                "P/E": None,
                "Market Cap ($B)": None,
                "Free Cash Flow ($B)": None
            })
            
    return pd.DataFrame(data_list)

with st.spinner("Recupero dati in corso da Yahoo Finance..."):
    df = fetch_data(TICKERS)

# Configurazione delle colonne per ordinare come NUMERI e mostrare il formato corretto
st.dataframe(
    df,
    use_container_width=True,
    column_config={
        "Prezzo ($)": st.column_config.NumberColumn(format="$%.2f"),
        "EPS ($)": st.column_config.NumberColumn(format="$%.2f"),
        "P/E": st.column_config.NumberColumn(format="%.2f"),
        "Market Cap ($B)": st.column_config.NumberColumn(format="$%.2f B"),
        "Free Cash Flow ($B)": st.column_config.NumberColumn(format="$%.2f B"),
    }
)
