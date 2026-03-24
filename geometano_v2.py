# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import plotly.express as px

# CONFIG
st.set_page_config(layout="wide")

st.title("🌱 Impianti di trattamento rifiuti urbani in Italia")

# =========================
# LOAD DATA
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("impianti.xlsx")
    df.columns = df.columns.str.lower()
    return df

df = load_data()

# =========================
# SIDEBAR
# =========================
st.sidebar.header("🔍 Filtri")

comune_input = st.sidebar.text_input("Comune", "Milano")
raggio_km = st.sidebar.slider("Raggio (km)", 1, 100, 20)

# =========================
# GEOLOCALIZZAZIONE
# =========================
geolocator = Nominatim(user_agent="biometano_app")
location = geolocator.geocode(comune_input + ", Italia")

if location is None:
    st.error("Comune non trovato")
    st.stop()

lat_centro = location.latitude
lon_centro = location.longitude

# =========================
# COLONNE
# =========================
lat_col = "latitudine"
lon_col = "longitudine"

if lat_col not in df.columns or lon_col not in df.columns:
    st.error("Colonne lat/lon mancanti")
    st.write(df.columns)
    st.stop()

# =========================
# DISTANZA
# =========================
def calcola_distanza(row):
    return geodesic(
        (lat_centro, lon_centro),
        (row[lat_col], row[lon_col])
    ).km

df = df.copy()
df["distanza_km"] = df.apply(calcola_distanza, axis=1)

df_filtrato = df[df["distanza_km"] <= raggio_km].copy()

# pulizia
df_filtrato = df_filtrato.dropna(subset=[lat_col, lon_col])

# =========================
# KPI (FIGO!)
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Impianti trovati", len(df_filtrato))
col2.metric("Raggio selezionato", f"{raggio_km} km")

if len(df_filtrato) > 0:
    col3.metric("Distanza media", f"{round(df_filtrato['distanza_km'].mean(),1)} km")
else:
    col3.metric("Distanza media", "-")

# =========================
# MAPPA
# =========================
st.write("### 🗺️ Mappa interattiva")

if len(df_filtrato) > 0:

    # DESCRIZIONE COMPLETA
    df_filtrato["info"] = (
        "📍 Comune: " + df_filtrato.get("comune", "").astype(str) +
        "<br>🏭 Tipo: " + df_filtrato.get("tipologia", "N/A").astype(str) +
        "<br>📏 Distanza: " + df_filtrato["distanza_km"].round(1).astype(str) + " km"
    )

    fig = px.scatter_mapbox(
        df_filtrato,
        lat=lat_col,
        lon=lon_col,
        color="distanza_km",  # colore per distanza
        size="distanza_km",   # dimensione marker
        hover_name="comune",
        hover_data={
            "distanza_km": True,
            lat_col: False,
            lon_col: False
        },
        zoom=7,
        height=600
    )

    fig.update_traces(
        marker=dict(size=10, opacity=0.7)
    )

    fig.update_layout(
        mapbox_style="open-street-map",
        margin={"r":0,"t":0,"l":0,"b":0}
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Nessun impianto trovato")

# =========================
# TABELLA
# =========================
st.write("### 📊 Tabella")

st.dataframe(
    df_filtrato.sort_values("distanza_km"),
    height=400,
    use_container_width=True
)

# =========================
# DOWNLOAD
# =========================
st.download_button(
    label="📥 Scarica risultati in Excel",
    data=df_filtrato.to_excel(index=False, engine='openpyxl'),
    file_name="impianti_filtrati.xlsx"
)
