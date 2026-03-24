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

if "totale (t)" not in df.columns:
    st.error("Colonna 'totale (t)' mancante!")
    st.stop()

df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors='coerce').fillna(0)

# =========================
# FILTRI ORIZZONTALI
# =========================
tipologie = df["tipologia"].dropna().unique().tolist()

col1, col2, col3 = st.columns([2,2,1])

with col1:
    tipologia_selezionata = st.multiselect(
        "Tipologia impianti",
        options=tipologie,
        default=tipologie
    )

with col2:
    comune_input = st.text_input("Comune di riferimento", "Milano")

with col3:
    raggio_km = st.slider("Raggio (km)", 1, 100, 20)

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

lat_col = "latitudine"
lon_col = "longitudine"

if lat_col not in df.columns or lon_col not in df.columns:
    st.error("Colonne latitudine/longitudine mancanti")
    st.stop()

# =========================
# CALCOLO DISTANZA
# =========================
df["distanza_km"] = df.apply(
    lambda r: geodesic((lat_centro, lon_centro), (r[lat_col], r[lon_col])).km,
    axis=1
).round(1)

# =========================
# FILTRO DATI
# =========================
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

if len(df_filtrato) > 0:
    col3.metric("Distanza media", f"{df_filtrato['distanza_km'].mean():.1f} km")
else:
    col3.metric("Distanza media", "-")

# =========================
# MAPPA (STABILE)
# =========================
st.write("### 🗺️ Mappa impianti")

if len(df_filtrato) > 0:

    fig = px.scatter_mapbox(
        df_filtrato,
        lat=lat_col,
        lon=lon_col,
        size="totale (t)",
        color="totale (t)",
        hover_name="comune",
        hover_data={
            "tipologia": True,
            "totale (t)": True,
            "distanza_km": True,
            lat_col: False,
            lon_col: False
        },
        color_continuous_scale="Oranges",
        size_max=25,
        zoom=7,
        height=600
    )

    fig.update_layout(
        mapbox_style="open-street-map",
        margin=dict(r=0, t=0, l=0, b=0)
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Nessun impianto trovato nel raggio selezionato")

# =========================
# TABELLA SEMPLICE
# =========================
st.write("### 📊 Tabella impianti")

if len(df_filtrato) > 0:

    comuni = df_filtrato["comune"].dropna().unique().tolist()

    comune_sel = st.selectbox(
        "Filtra per comune",
        ["Tutti"] + comuni
    )

    if comune_sel != "Tutti":
        df_tabella = df_filtrato[df_filtrato["comune"] == comune_sel]
    else:
        df_tabella = df_filtrato

    st.dataframe(df_tabella, use_container_width=True)

else:
    st.warning("Nessun dato disponibile")

# =========================
# DOWNLOAD EXCEL
# =========================
output = io.BytesIO()
df_filtrato.to_excel(output, index=False, engine='openpyxl')
output.seek(0)

st.download_button(
    "💾 Scarica dati filtrati in Excel",
    data=output,
    file_name="dati_filtrati.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
