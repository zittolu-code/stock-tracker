import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Stock Value Tracker", layout="wide")

st.title("📈 Prossimi Ingressi - Stock Value Tracker")

# Elenco Ticker
tickers = ["NVDA", "GOOGL", "MSFT", "AMZN", "BABA", "META", "AMD", "V", "ASML", "MA"]

if st.button("🔄 Aggiorna Dati Live"):
    st.cache_data.clear()

@st.cache_data(ttl=3600)
def fetch_data(ticker_list):
    data_list = []
    
    for ticker in ticker_list:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Estrazione dati con valori di fallback
            price = info.get("currentPrice") or info.get("regularMarketPrice") or "N/A"
            eps = info.get("trailingEps") or "N/A"
            pe = info.get("trailingPE") or "N/A"
            market_cap = info.get("marketCap") or "N/A"
            fcf = info.get("freeCashflow") or "N/A"
            
            # Formattazione
            price_str = f"${price:,.2f}" if isinstance(price, (int, float)) else "N/A"
            eps_str = f"${eps:,.2f}" if isinstance(eps, (int, float)) else "N/A"
            pe_str = f"{pe:.2f}" if isinstance(pe, (int, float)) else "N/A"
            mc_str = f"${market_cap / 1e9:,.2f} B" if isinstance(market_cap, (int, float)) else "N/A"
            fcf_str = f"${fcf / 1e9:,.2f} B" if isinstance(fcf, (int, float)) else "N/A"
            
            data_list.append({
                "Azienda": ticker,
                "Ticker": ticker,
                "Prezzo": price_str,
                "EPS": eps_str,
                "P/E": pe_str,
                "Market Cap": mc_str,
                "Free Cash Flow": fcf_str
            })
        except Exception as e:
            data_list.append({
                "Azienda": ticker,
                "Ticker": ticker,
                "Prezzo": "N/A",
                "EPS": "N/A",
                "P/E": "N/A",
                "Market Cap": "N/A",
                "Free Cash Flow": "N/A"
            })
            
    return pd.DataFrame(data_list)

with st.spinner("Recupero dati in corso da Yahoo Finance..."):
    df = fetch_data(tickers)

st.dataframe(df, use_container_width=True)
