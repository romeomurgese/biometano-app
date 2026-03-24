# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import plotly.express as px
import io

# =========================
# CONFIG
# =========================
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
# SIDEBAR - FILTRI
# =========================
st.sidebar.header("🔍 Filtri")

# Slicer per tipologia
tipologie = df["tipologia"].dropna().unique().tolist()
tipologia_selezionata = st.sidebar.multiselect(
    "Seleziona tipologia impianti",
    options=tipologie,
    default=tipologie
)

comune_input = st.sidebar.text_input("Comune di riferimento", "Milano")
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
# COLONNE LAT/LON
# =========================
lat_col = "latitudine"
lon_col = "longitudine"

if lat_col not in df.columns or lon_col not in df.columns:
    st.error("Colonne lat/lon mancanti")
    st.write(df.columns)
    st.stop()

# =========================
# CALCOLO DISTANZE
# =========================
def calcola_distanza(row):
    return geodesic(
        (lat_centro, lon_centro),
        (row[lat_col], row[lon_col])
    ).km

df = df.copy()
df["distanza_km"] = df.apply(calcola_distanza, axis=1).round(1)  # arrotondamento a 1 decimale

# FILTRI
df_filtrato = df[
    (df["distanza_km"] <= raggio_km) &
    (df["tipologia"].isin(tipologia_selezionata))
].copy()

df_filtrato = df_filtrato.dropna(subset=[lat_col, lon_col])

# =========================
# KPI
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("Impianti trovati", len(df_filtrato))
col2.metric("Raggio selezionato", f"{raggio_km} km")
col3.metric(
    "Distanza media",
    f"{df_filtrato['distanza_km'].mean():.1f} km" if len(df_filtrato) > 0 else "-"
)

# =========================
# MAPPA
# =========================
# =========================
# =========================
# MAPPA
# =========================
st.write("### 🗺️ Mappa interattiva")

if len(df_filtrato) > 0:
    df_filtrato["info"] = (
        "📍 Comune: " + df_filtrato.get("comune", "").astype(str) +
        "<br>🏭 Tipo: " + df_filtrato.get("tipologia", "N/A").astype(str) +
        "<br>📏 Distanza: " + df_filtrato["distanza_km"].astype(str) + " km"
    )

# Esempio
fig = px.scatter_mapbox(
    df_filtrato,
    lat=lat_col,
    lon=lon_col,
    color="quantita_rifiuti",  # colore basato sulle quantità trattate
    size="distanza_km",         # dimensione marker opzionale, o fissa
    color_continuous_scale="YlOrRd",  # giallo → rosso
    hover_name="comune",
    hover_data={"distanza_km": True, lat_col: False, lon_col: False},
    zoom=7,
    height=600
)
fig.update_layout(coloraxis_colorbar=dict(title="Quantità trattate"))

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Nessun impianto trovato nel raggio selezionato.")
# =========================
# TABELLA
# =========================
st.write("### 📊 Tabella impianti")
st.dataframe(
    df_filtrato.sort_values("distanza_km"),
    height=400,
    use_container_width=True
)

# =========================
# DOWNLOAD EXCEL
# =========================
output = io.BytesIO()
df_filtrato.to_excel(output, index=False, engine='openpyxl')
output.seek(0)

st.download_button(
    label="💾 Scarica dati filtrati in Excel",
    data=output,
    file_name="dati_filtrati.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
