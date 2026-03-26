# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from math import radians, cos, sin, asin, sqrt
import io

st.set_page_config(layout="wide")
st.title("🌱 Impianti di trattamento rifiuti urbani in Italia")

# =========================
# CARICAMENTO DATI
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("impianti_geocodificati.xlsx")
    df.columns = df.columns.str.lower()
    df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors="coerce").fillna(0)
    return df

df = load_data()

# =========================
# FILTRI
# =========================
tipologie = df["tipologia"].dropna().unique().tolist()
col1, col2, col3 = st.columns([2,2,1])

with col1:
    tipologia_selezionata = st.multiselect("Tipologia impianti", options=tipologie, default=tipologie)

comuni_ref = df[["comune", "latitudine", "longitudine"]].drop_duplicates()

with col2:
    comune_sel = st.selectbox("Comune di riferimento", comuni_ref["comune"].unique())

with col3:
    raggio_km = st.slider("Raggio (km)", 1, 100, 20)

row_sel = comuni_ref[comuni_ref["comune"] == comune_sel].iloc[0]
lat_centro = row_sel["latitudine"]
lon_centro = row_sel["longitudine"]

# =========================
# DISTANZA (Haversine)
# =========================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

df = df.dropna(subset=["latitudine", "longitudine"])
df["distanza_km"] = df.apply(lambda r: haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"]), axis=1).round(1)

df_filtrato = df[(df["distanza_km"] <= raggio_km) & (df["tipologia"].isin(tipologia_selezionata))]

# =========================
# MAPPA
# =========================
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
st.dataframe(df_filtrato)

# =========================
# DOWNLOAD
# =========================
output = io.BytesIO()
df_filtrato.to_excel(output, index=False)
output.seek(0)

st.download_button("💾 Scarica Excel", data=output, file_name="dati_filtrati.xlsx")
