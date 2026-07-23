import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Stock Tracker", layout="wide")
st.title("📈 Prossimi Ingressi - Stock Value Tracker")

TICKERS = [
    "NVDA", "GOOGL", "MSFT", "AMZN", "BABA", "META", "AMD", "V", "ASML", 
    "MA", "PLTR", "SAP", "CRM", "ISRG", "NOW", "MELI", "RACE", "O", 
    "OKE", "NBIS", "CRWV", "CMG", "LDO.MI", "CRCL", "LYSCF", "IREN", 
    "TYL", "FIG", "MARA"
]

@st.cache_data(ttl=600)
def fetch_stock_data(tickers):
    data_list = []
    for symbol in tickers:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            price = info.get('currentPrice') or info.get('regularMarketPrice', 'N/A')
            currency = info.get('currency', 'USD')
            eps = info.get('trailingEps', 'N/A')
            pe = info.get('trailingPE', 'N/A')
            market_cap = info.get('marketCap', None)
            fcf = info.get('freeCashflow', None)
            
            market_cap_b = f"{market_cap / 1e9:.2f} B" if isinstance(market_cap, (int, float)) else "N/A"
            fcf_b = f"{fcf / 1e9:.2f} B" if isinstance(fcf, (int, float)) else "N/A"
            
            data_list.append({
                "Azienda": info.get('shortName', symbol),
                "Ticker": symbol,
                "Prezzo": f"{price} {currency}" if price != "N/A" else "N/A",
                "EPS": round(eps, 2) if isinstance(eps, (int, float)) else "N/A",
                "P/E": round(pe, 2) if isinstance(pe, (int, float)) else "N/A",
                "Market Cap": market_cap_b,
                "Free Cash Flow": fcf_b
            })
        except Exception:
            data_list.append({
                "Azienda": symbol, "Ticker": symbol, "Prezzo": "N/A", 
                "EPS": "N/A", "P/E": "N/A", "Market Cap": "N/A", "Free Cash Flow": "N/A"
            })
            
    return pd.DataFrame(data_list)

if st.button("🔄 Aggiorna Dati Live"):
    st.cache_data.clear()

with st.spinner("Scaricamento dati da Yahoo Finance in corso..."):
    df = fetch_stock_data(TICKERS)

st.dataframe(df, use_container_width=True)
