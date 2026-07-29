import os
import pandas as pd
import streamlit as st
import yfinance as yf
from google import genai

st.set_page_config(page_title="Stock Value Tracker", layout="wide")

st.title("📈 Prossimi Ingressi - Stock Value Tracker")

# File per la memorizzazione dei dati manuali
CSV_FILE = "dati_manuali.csv"

# Elenco completo dei Ticker
TICKERS = [
    "NVDA", "GOOGL", "MSFT", "AMZN", "BABA", "META", "AMD", "V", "ASML", 
    "MA", "PLTR", "SAP", "CRM", "ISRG", "NOW", "MELI", "RACE", "O", 
    "OKE", "NBIS", "CRWV", "CMG", "LDO.MI", "CRCL", "LYSCF", "IREN", 
    "TYL", "FIG", "MARA"
]

# --- FUNZIONI DI GESTIONE MEMORIZZAZIONE MANUALE ---
def load_manual_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        # Schema iniziale vuoto se il file non esiste
        return pd.DataFrame(columns=["Ticker", "Periodo", "Data/Riferimento", "Revenue ($B)", "Diluted EPS ($)"])

def save_manual_data(df):
    df.to_csv(CSV_FILE, index=False)

# Inizializzazione dello Stato Locale
if "manual_df" not in st.session_state:
    st.session_state.manual_df = load_manual_data()

# --- RECOVERY DATI LIVE DA YAHOO (PER TABELLA PRINCIPALE) ---
if st.button("🔄 Aggiorna Dati Live Yahoo"):
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

with st.spinner("Recupero panoramica generale da Yahoo Finance..."):
    df_summary = fetch_summary_data(TICKERS)

# --- TABELLA PRINCIPALE ---
st.subheader("📋 Panoramica Titoli Live")

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

# --- SEZIONE INSERIMENTO E ANALISI MANUALE PER TICKER ---
st.markdown("---")
st.subheader("✍️ Gestione e Inserimento Dati Manuali")

col_select1, col_select2 = st.columns([2, 1])

with col_select1:
    selected_ticker = st.selectbox("Seleziona un Ticker su cui lavorare:", TICKERS)

with col_select2:
    freq = st.radio("Periodo di analisi:", ["Anno", "Trimestre"], horizontal=True)

if selected_ticker:
    st.markdown(f"### Dati Storici Inseriti: **{selected_ticker}** ({freq})")
    
    # Filtriamo il dataframe globale per il ticker e il periodo selezionati
    full_df = st.session_state.manual_df
    filtered_df = full_df[(full_df["Ticker"] == selected_ticker) & (full_df["Periodo"] == freq)].copy()
    
    # Rimuoviamo colonne non necessarie alla vista singola
    working_df = filtered_df[["Data/Riferimento", "Revenue ($B)", "Diluted EPS ($)"]].reset_index(drop=True)

    tab_edit, tab_chart = st.tabs(["📝 Modifica / Inserisci Dati", "📊 Grafici Trend"])

    with tab_edit:
        st.info("💡 Puoi inserire nuovi dati direttamente nella tabella o modificare quelli esistenti. Clicca su **Salva Modifiche** per memorizzarli permanentemente.")
        
        # Data Editor interattivo
        edited_df = st.data_editor(
            working_df,
            num_rows="dynamic", # Permette di aggiungere/rimuovere righe
            use_container_width=True,
            column_config={
                "Data/Riferimento": st.column_config.TextColumn("Data / Periodo (es. 2024, Q1 2024)", required=True),
                "Revenue ($B)": st.column_config.NumberColumn("Revenue ($B)", format="$%.2f B"),
                "Diluted EPS ($)": st.column_config.NumberColumn("Diluted EPS ($)", format="$%.2f"),
            }
        )

        if st.button("💾 Salva Modifiche per " + selected_ticker):
            # Ricostruiamo i metadati per il salvare nel CSV globale
            edited_df["Ticker"] = selected_ticker
            edited_df["Periodo"] = freq
            
            # Rimuoviamo i vecchi record per questo Ticker + Periodo e inseriamo i nuovi
            other_records = full_df[~((full_df["Ticker"] == selected_ticker) & (full_df["Periodo"] == freq))]
            updated_full_df = pd.concat([other_records, edited_df], ignore_index=True)
            
            # Salviamo su file e in session state
            save_manual_data(updated_full_df)
            st.session_state.manual_df = updated_full_df
            st.success(f"Dati per {selected_ticker} ({freq}) memorizzati con successo!")
            st.rerun()

    with tab_chart:
        if not working_df.empty and working_df["Data/Riferimento"].notna().any():
            chart_df = working_df.set_index("Data/Riferimento")
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.markdown("**Revenue (Fatturato in $B)**")
                st.bar_chart(chart_df["Revenue ($B)"])
            with col_g2:
                st.markdown("**EPS Diluito ($)**")
                st.line_chart(chart_df["Diluted EPS ($)"])
        else:
            st.warning("Nessun dato valido inserito per generare i grafici.")

# --- ASSISTENTE GEMINI ---
st.markdown("---")
st.subheader("🤖 Assistente Finanziario Gemini")

api_key = st.secrets.get("GEMINI_API_KEY")

if not api_key:
    st.info("💡 Per attivare l'assistente, inserisci la tua GEMINI_API_KEY nei Secrets di Streamlit Cloud.")
else:
    user_prompt = st.text_input(f"Fai una domanda su {selected_ticker} o sui dati inseriti:")
    
    if st.button("✨ Chiedi a Gemini") and user_prompt:
        with st.spinner("Gemini sta analizzando i dati..."):
            try:
                client = genai.Client(api_key=api_key)
                
                context_summary = df_summary.to_csv(index=False)
                context_manual = working_df.to_csv(index=False) if 'working_df' in locals() else "Nessun dato manuale inserito."
                
                prompt = f"""
                Sei un analista finanziario esperto. 
                
                Dati di mercato live:
                {context_summary}
                
                Dati storici inseriti dall'utente per {selected_ticker}:
                {context_manual}
                
                Rispondi in modo sintetico alla richiesta:
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
