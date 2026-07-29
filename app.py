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
def fetch_summary_data(ticker_list):
    data_list = []
    for ticker in ticker_list:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            pe = info.get("trailingPE")
            market_cap = info.get("marketCap")
            fcf = info.get("freeCashflow")
            shares_outstanding = info.get("sharesOutstanding")
            eps_trailing = info.get("trailingEps")

            fcf_per_share = None
            fcf_eps_ratio = None
            
            if isinstance(fcf, (int, float)) and isinstance(shares_outstanding, (int, float)) and shares_outstanding > 0:
                fcf_per_share = fcf / shares_outstanding
                
            if isinstance(fcf_per_share, (int, float)) and isinstance(eps_trailing, (int, float)) and eps_trailing > 0:
                fcf_eps_ratio = fcf_per_share / eps_trailing

            mc_billion = (market_cap / 1e9) if isinstance(market_cap, (int, float)) else None
            fcf_billion = (fcf / 1e9) if isinstance(fcf, (int, float)) else None
            
            data_list.append({
                "Azienda": info.get("shortName", ticker),
                "Ticker": ticker,
                "Prezzo ($)": price if isinstance(price, (int, float)) else None,
                "Basic EPS TTM ($)": eps_trailing if isinstance(eps_trailing, (int, float)) else None,
                "Diluted EPS TTM ($)": eps_trailing if isinstance(eps_trailing, (int, float)) else None,
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
            
    df_raw = pd.DataFrame(data_list)
    return df_raw.dropna(how='all', axis=1)

@st.cache_data(ttl=3600)
def fetch_detailed_financials(ticker_symbol, freq="Annual"):
    stock = yf.Ticker(ticker_symbol)
    if freq == "Quarterly":
        fin = stock.quarterly_financials
    else:
        fin = stock.financials

    if fin is None or fin.empty:
        return pd.DataFrame()

    df_fin = fin.T  # Trasposizione per avere le date come righe
    df_fin.index = pd.to_datetime(df_fin.index).strftime('%Y-%m-%d')
    df_fin = df_fin.sort_index(ascending=True)

    extracted = pd.DataFrame(index=df_fin.index)

    # Estrazione Revenue
    for col in ["Total Revenue", "Operating Revenue"]:
        if col in df_fin.columns:
            extracted["Revenue ($B)"] = df_fin[col] / 1e9
            break

    # Estrazione Diluted EPS
    for col in ["Diluted EPS", "Normalized Diluted EPS", "Diluted NI Availto Com Stock"]:
        if col in df_fin.columns:
            extracted["Diluted EPS ($)"] = df_fin[col]
            break

    return extracted

with st.spinner("Recupero panoramica generale da Yahoo Finance..."):
    df_summary = fetch_summary_data(TICKERS)

# --- TABELLA PRINCIPALE ---
st.subheader("📋 Panoramica Titoli")

def highlight_fcf_ratio(val):
    if pd.isna(val) or val is None:
        return ''
    elif val > 1.0:
        return 'background-color: #2e7d32; color: white; font-weight: bold;'
    else:
        return 'background-color: #c62828; color: white; font-weight: bold;'

format_dict = {
    "Prezzo ($)": "${:,.2f}",
    "Basic EPS TTM ($)": "${:,.2f}",
    "Diluted EPS TTM ($)": "${:,.2f}",
    "P/E": "{:,.2f}",
    "Market Cap ($B)": "${:,.2f} B",
    "Free Cash Flow ($B)": "${:,.2f} B",
    "FCF/EPS Ratio": "{:,.2f}"
}
active_formats = {col: fmt for col, fmt in format_dict.items() if col in df_summary.columns}

if 'FCF/EPS Ratio' in df_summary.columns:
    styled_df = df_summary.style.map(highlight_fcf_ratio, subset=['FCF/EPS Ratio'])\
                                .format(active_formats, na_rep="N/A")
else:
    styled_df = df_summary.style.format(active_formats, na_rep="N/A")

st.dataframe(styled_df, use_container_width=True)

# --- SEZIONE DI DETTAGLIO PER TICKER ---
st.markdown("---")
st.subheader("🔍 Scheda di Dettaglio Aziendale")

col_select1, col_select2 = st.columns([2, 1])

with col_select1:
    selected_ticker = st.selectbox("Seleziona un Ticker per analizzare i dettagli:", TICKERS)

with col_select2:
    freq = st.radio("Periodo di analisi:", ["Anno", "Trimestre"], horizontal=True)

freq_key = "Quarterly" if freq == "Trimestre" else "Annual"

if selected_ticker:
    df_detail = fetch_detailed_financials(selected_ticker, freq=freq_key)
    
    if not df_detail.empty:
        st.markdown(f"### Storico {selected_ticker} ({freq})")
        
        tab1, tab2 = st.tabs(["📊 Grafici Trend", "📄 Tabella Dati"])
        
        with tab1:
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                if "Revenue ($B)" in df_detail.columns:
                    st.markdown("**Revenue (Fatturato in $B)**")
                    st.bar_chart(df_detail["Revenue ($B)"])
                else:
                    st.info("Dati Revenue non disponibili per questo periodo.")
                    
            with col_g2:
                if "Diluted EPS ($)" in df_detail.columns:
                    st.markdown("**EPS Diluito ($)**")
                    st.line_chart(df_detail["Diluted EPS ($)"])
                else:
                    st.info("Dati EPS Diluito non disponibili per questo periodo.")

        with tab2:
            st.dataframe(df_detail.style.format({
                "Revenue ($B)": "${:,.2f} B",
                "Diluted EPS ($)": "${:,.2f}"
            }, na_rep="N/A"), use_container_width=True)
    else:
        st.warning(f"Nessun dato storico finanziario disponibile per {selected_ticker}.")

# --- ASSISTENTE GEMINI ---
st.markdown("---")
st.subheader("🤖 Assistente Finanziario Gemini")

api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.info("💡 Per attivare l'assistente, inserisci la tua GEMINI_API_KEY nei Secrets di Streamlit Cloud.")
else:
    user_prompt = st.text_input(f"Fai una domanda su {selected_ticker} o sull'intera lista (es: 'Confronta il fatturato di {selected_ticker} con i competitor'):")
    
    if st.button("✨ Chiedi a Gemini") and user_prompt:
        with st.spinner("Gemini sta analizzando i dati..."):
            try:
                client = genai.Client(api_key=api_key)
                
                context_summary = df_summary.to_csv(index=False)
                context_detail = df_detail.to_csv() if 'df_detail' in locals() and not df_detail.empty else "Nessun dettaglio aggiuntivo"
                
                prompt = f"""
                Sei un analista finanziario esperto. 
                
                Ecco la panoramica generale di mercato:
                {context_summary}
                
                Ecco i dettagli storici dell'azienda selezionata ({selected_ticker}):
                {context_detail}
                
                Rispondi in modo sintetico e professionale alla seguente richiesta dell'utente:
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
