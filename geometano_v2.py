import streamlit as st
import pandas as pd
import plotly.express as px
from math import radians, cos, sin, asin, sqrt
import io
import os

st.set_page_config(layout="wide")
st.title("🌱 Impianti di trattamento rifiuti urbani in Italia")

# =========================
# FUNZIONI
# =========================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

# =========================
# CARICAMENTO DATI
# =========================
def load_data():
    # Se il file geocodificato esiste, lo carica
    if os.path.exists("impianti_geocodificati.xlsx"):
        df = pd.read_excel("impianti_geocodificati.xlsx")
    else:
        # Altrimenti permette all'utente di caricarlo
        uploaded_file = st.file_uploader("Carica il file geocodificato (.xlsx)", type="xlsx")
        if uploaded_file is None:
            st.warning("⚠️ Nessun file trovato. Carica il file Excel geocodificato per vedere la mappa.")
            st.stop()
        df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.lower()
    df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df = df.dropna(subset=["latitudine", "longitudine"])
    return df

df = load_data()

if df.empty:
    st.warning("⚠️ Nessun dato valido con latitudine e longitudine.")
    st.stop()

# =========================
# FILTRI LATERALI
# =========================
with st.sidebar:
    st.header("Filtri")
    tipologie = df["tipologia"].dropna().unique().tolist()
    tipologia_selezionata = st.multiselect("Tipologia impianti", options=tipologie, default=tipologie)

    comuni_ref = df[["comune", "latitudine", "longitudine"]].drop_duplicates()
    comune_sel = st.selectbox("Comune di riferimento", comuni_ref["comune"].unique())

    raggio_km = st.slider("Raggio (km)", min_value=1, max_value=200, value=50)

# =========================
# CALCOLO DISTANZA
# =========================
row_sel = comuni_ref[comuni_ref["comune"] == comune_sel].iloc[0]
lat_centro = row_sel["latitudine"]
lon_centro = row_sel["longitudine"]

df["distanza_km"] = df.apply(lambda r: haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"]), axis=1).round(1)

df_filtrato = df[(df["distanza_km"] <= raggio_km) & (df["tipologia"].isin(tipologia_selezionata))]

if df_filtrato.empty:
    st.warning("⚠️ Nessun impianto trovato con i filtri selezionati.")
else:
    # =========================
    # MAPPA
    # =========================
    st.subheader("📍 Mappa impianti")
    fig = px.scatter_mapbox(
        df_filtrato,
        lat="latitudine",
        lon="longitudine",
        size="totale (t)",
        color="totale (t)",
        hover_name="comune",
        hover_data=["tipologia", "distanza_km"],
        zoom=6,
        height=600
    )
    fig.update_layout(mapbox_style="open-street-map")
    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # TABELLA
    # =========================
    st.subheader("📋 Tabella dati filtrati")
    st.dataframe(df_filtrato)

    # =========================
    # DOWNLOAD EXCEL
    # =========================
    output = io.BytesIO()
    df_filtrato.to_excel(output, index=False)
    output.seek(0)
    st.download_button("💾 Scarica Excel filtrato", data=output, file_name="dati_filtrati.xlsx")
