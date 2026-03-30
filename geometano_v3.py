import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import time
import unicodedata

st.set_page_config(layout="wide")

# =========================
# NORMALIZZA COLONNE
# =========================
def normalize_cols(df):
    df.columns = (
        df.columns
        .str.lower()
        .str.replace(" ", "_")
        .map(lambda x: unicodedata.normalize('NFKD', str(x)).encode('ascii', errors='ignore').decode('utf-8'))
    )
    return df

# =========================
# LOAD DATI
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("impianti_geocodificati.xlsx")
    df = normalize_cols(df)
    df["totale_(t)"] = pd.to_numeric(df["totale_(t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df["flag"] = True
    return df

# refresh manuale
if st.sidebar.button("🔄 Aggiorna dati"):
    st.cache_data.clear()

df = load_data()

# =========================
# LABEL (con società)
# =========================
df["label"] = (
    df["comune"] + " (" + df["provincia"].fillna("") + ")"
    + " - " + df["societa"].fillna("N/D")
)

# =========================
# SIDEBAR
# =========================
st.sidebar.header("⚙️ Parametri")

raggio_km = st.sidebar.slider("Raggio massimo (km)", 10, 300, 100)
penale_km = st.sidebar.slider("Penale €/km oltre soglia", 0, 5, 1)

simula = st.sidebar.button("🚀 Simula gara")

# =========================
# MAPPA (SEMPRE VISIBILE)
# =========================
st.subheader("🗺️ Mappa impianti")

fig_map = px.scatter_mapbox(
    df,
    lat="latitudine",
    lon="longitudine",
    hover_name="label",
    zoom=5,
    height=500
)

fig_map.update_layout(mapbox_style="open-street-map")

st.plotly_chart(fig_map, use_container_width=True)

# =========================
# TABELLA FILTRATA
# =========================
st.subheader("📋 Selezione impianti")

df_filtrato = df.copy()

# formattazione quantità
df_filtrato["quantita_fmt"] = df_filtrato["totale_(t)"].apply(
    lambda x: f"{int(x):,}".replace(",", ".")
)

df_table = df_filtrato[[
    "flag", "label", "tipologia", "quantita_fmt"
]].rename(columns={
    "flag": "Seleziona",
    "label": "Impianto",
    "tipologia": "Tipologia",
    "quantita_fmt": "Quantità"
})

edited_df = st.data_editor(
    df_table,
    use_container_width=True,
    disabled=["Impianto", "Tipologia", "Quantità"]
)

df_filtrato["flag"] = edited_df["Seleziona"]

# =========================
# FUNZIONE HIGHLIGHT
# =========================
def highlight_text(row):
    if row["Posizione"] == 1:
        return ["background-color: #90EE90"] * len(row)
    elif row["Posizione"] == 2:
        return ["background-color: #FFD580"] * len(row)
    elif row["Posizione"] == 3:
        return ["background-color: #FFFF99"] * len(row)
    else:
        return [""] * len(row)

# =========================
# SIMULAZIONE GARA
# =========================
if simula:

    with st.spinner("⏳ Calcolo in corso..."):
        time.sleep(0.5)

        df_finale = df_filtrato[df_filtrato["flag"]].copy()

        # simulazione offerta casuale
        df_finale["offerta"] = np.random.uniform(80, 120, len(df_finale))

        # distanza fake (se non già presente)
        if "distanza_km" not in df_finale.columns:
            df_finale["distanza_km"] = np.random.uniform(10, 200, len(df_finale))

        df_finale["km_fuori"] = (df_finale["distanza_km"] - raggio_km).clip(lower=0)
        df_finale["penalita"] = df_finale["km_fuori"] * penale_km
        df_finale["offerta_finale"] = df_finale["offerta"] - df_finale["penalita"]

        df_finale = df_finale.sort_values("offerta_finale", ascending=False)
        df_finale["ranking"] = range(1, len(df_finale)+1)

    # KPI
    best = df_finale.iloc[0]
    worst = df_finale.iloc[-1]

    col1, col2, col3 = st.columns(3)
    col1.metric("🥇 Migliore offerta", f"{best['offerta_finale']:.1f} €")
    col2.metric("📉 Peggiore offerta", f"{worst['offerta_finale']:.1f} €")
    col3.metric("Δ Spread", f"{best['offerta_finale'] - worst['offerta_finale']:.1f} €")

    # =========================
    # TABELLA RISULTATI
    # =========================
    st.subheader("🏆 Risultato gara")

    df_gara = df_finale[[
        "ranking","label","offerta","penalita","offerta_finale"
    ]].rename(columns={
        "ranking":"Posizione",
        "label":"Impianto",
        "offerta":"Offerta (€)",
        "penalita":"Penalità (€)",
        "offerta_finale":"Offerta finale (€)"
    })

    styled = df_gara.style.apply(highlight_text, axis=1)

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True
    )

    # =========================
    # GRAFICO
    # =========================
    fig_bar = px.bar(
        df_finale,
        x="label",
        y="offerta_finale",
        title="📊 Ranking offerte"
    )

    st.plotly_chart(fig_bar, use_container_width=True)
