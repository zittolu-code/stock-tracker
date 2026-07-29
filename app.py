import os
import pandas as pd
import streamlit as st
import yfinance as yf
from google import genai

st.set_page_config(page_title="Stock Value Tracker", layout="wide")

st.title("📈 Prossimi Ingressi - Stock Value Tracker")

# File CSV per il salvataggio dei dati manuali
CSV_FILE = "dati_manuali.csv"

TICKERS = [
    "NVDA", "GOOGL", "MSFT", "AMZN", "BABA", "META", "AMD", "V", "ASML", 
    "MA", "PLTR", "SAP", "CRM", "ISRG", "NOW", "MELI", "RACE", "O", 
    "OKE", "NBIS", "CRWV", "CMG", "LDO.MI", "CRCL", "LYSCF", "IREN", 
    "TYL", "FIG", "MARA"
]

REQUIRED_COLUMNS = ["Ticker", "Anno", "Metrica", "Q1", "Q2", "Q3", "Q4"]

# --- GESTIONE DATI MANUALI ROBUSTA ---
def load_manual_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            if not all(col in df.columns for col in REQUIRED_COLUMNS):
                return pd.DataFrame(columns=REQUIRED_COLUMNS)
            return df
        except Exception:
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
    else:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

def save_manual_data(df):
    df.to_csv(CSV_FILE, index=False)

if "manual_df" not in st.session_state:
    st.session_state.manual_df = load_manual_data()

# --- CALCOLO DINAMICO TTM PER OGNI TICKER ---
def calculate_manual_eps_ttm(df):
    eps_ttm_map = {}
    if df.empty:
        return eps_ttm_map

    # Filtra qualsiasi riga la cui Metrica contenga la parola 'EPS'
    eps_rows = df[df["Metrica"].astype(str).str.contains("EPS", case=False, na=False)].copy()

    for ticker in TICKERS:
        ticker_data = eps_rows[eps_rows["Ticker"] == ticker]
        if ticker_data.empty:
            continue

        # Converti Anno in numerico e ordina dal più recente
        ticker_data["Anno"] = pd.to_numeric(ticker_data["Anno"], errors="coerce")
        ticker_data = ticker_data.sort_values(by="Anno", ascending=False)

        collected_quarters = []
        for _, row in ticker_data.iterrows():
            # Scorri i trimestri dal più recente Q4 al Q1
            for q in ["Q4", "Q3", "Q2", "Q1"]:
                val = row[q]
                if pd.notna(val) and str(val).strip() != "":
                    try:
                        num_val = float(val)
                        collected_quarters.append(num_val)
                        if len(collected_quarters) == 4:
                            break
                    except ValueError:
                        continue
            if len(collected_quarters) == 4:
                break

        # Se sono stati trovati esattamente 4 trimestri, calcola il TTM
        if len(collected_quarters) == 4:
            eps_ttm_map[ticker] = sum(collected_quarters)

    return eps_ttm_map

# --- DATI LIVE YAHOO FINANCE ---
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

# Inserimento dinamico della colonna TTM calcolata dai dati manuali aggiornati
manual_eps_map = calculate_manual_eps_ttm(st.session_state.manual_df)
df_summary["EPS Diluito Normalizzato TTM ($)"] = df_summary["Ticker"].map(manual_eps_map)

# Riordino logico delle colonne
columns_order = [
    "Azienda", "Ticker", "Prezzo ($)", "Basic EPS TTM ($)", "Diluted EPS TTM ($)", 
    "EPS Diluito Normalizzato TTM ($)", "P/E", "Market Cap ($B)", "Free Cash Flow ($B)", "FCF/EPS Ratio"
]
existing_cols = [col for col in columns_order if col in df_summary.columns]
df_summary = df_summary[existing_cols]

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
    "EPS Diluito Normalizzato TTM ($)": "${:,.2f}",
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

# --- INSERIMENTO DATI PER ANNO E TRIMESTRI (Q1-Q4) ---
st.markdown("---")
st.subheader("✍️ Inserimento Dati Trimestrali per Anno")

col1, col2 = st.columns([2, 1])

with col1:
    selected_ticker = st.selectbox("Seleziona Ticker:", TICKERS)

manual_df = st.session_state.manual_df
if not manual_df.empty and "Anno" in manual_df.columns:
    existing_years = sorted(manual_df["Anno"].dropna().unique().astype(int).tolist(), reverse=True)
else:
    existing_years = []

default_years = [2026, 2025, 2024]
all_years = sorted(list(set(existing_years + default_years)), reverse=True)

with col2:
    selected_year = st.selectbox("Seleziona o Aggiungi Anno:", all_years)

st.markdown(f"### Tabella Trimestrale **{selected_ticker}** - Anno **{selected_year}**")

ticker_year_df = manual_df[(manual_df["Ticker"] == selected_ticker) & (manual_df["Anno"] == selected_year)]

if ticker_year_df.empty:
    working_df = pd.DataFrame([
        {"Metrica": "Revenue ($B)", "Q1": None, "Q2": None, "Q3": None, "Q4": None},
        {"Metrica": "Diluted EPS ($)", "Q1": None, "Q2": None, "Q3": None, "Q4": None}
    ])
else:
    working_df = ticker_year_df[["Metrica", "Q1", "Q2", "Q3", "Q4"]].reset_index(drop=True)

st.info("💡 Modifica i valori o aggiungi nuove metriche. Salva per aggiornare istantaneamente il TTM nella tabella in alto.")

edited_df = st.data_editor(
    working_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Metrica": st.column_config.TextColumn("Metrica", required=True),
        "Q1": st.column_config.NumberColumn("Q1", format="%.2f"),
        "Q2": st.column_config.NumberColumn("Q2", format="%.2f"),
        "Q3": st.column_config.NumberColumn("Q3", format="%.2f"),
        "Q4": st.column_config.NumberColumn("Q4", format="%.2f"),
    }
)

if st.button(f"💾 Salva Modifiche {selected_ticker} ({selected_year})"):
    edited_df = edited_df.dropna(subset=["Metrica"])
    edited_df["Ticker"] = selected_ticker
    edited_df["Anno"] = selected_year
    
    # Rimuoviamo i vecchi record per lo stesso Ticker e Anno
    other_records = manual_df[~((manual_df["Ticker"] == selected_ticker) & (manual_df["Anno"] == selected_year))]
    
    # Uniamo, salviamo su disk e aggiorniamo il session_state
    updated_full_df = pd.concat([other_records, edited_df], ignore_index=True)
    save_manual_data(updated_full_df)
    st.session_state.manual_df = updated_full_df
    
    st.success(f"Dati di {selected_ticker} ({selected_year}) salvati! Tabella TTM aggiornata.")
    st.rerun()

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
                context_manual = working_df.to_csv(index=False)
                
                prompt = f"""
                Sei un analista finanziario esperto. 
                
                Dati di mercato live e TTM manuali:
                {context_summary}
                
                Dati trimestrali inseriti per {selected_ticker} ({selected_year}):
                {context_manual}
                
                Rispondi in modo sintetico alla seguente richiesta:
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
