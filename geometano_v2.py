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
col1, col2, col3, col4 = st.columns([2,2,1,1])

with col1:
    tipologia_selezionata = st.multiselect("Tipologia impianti", options=tipologie, default=tipologie)
with col2:
    comune_input = st.text_input("Comune di riferimento", "Milano")
with col3:
    raggio_km = st.slider("Raggio (km)", 1, 100, 20)
with col4:
    if st.button("🔄 Reset selezione"):
        if "selected_comune" in st.session_state:
            del st.session_state["selected_comune"]
        st.experimental_rerun()

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
    st.error("Colonne lat/lon mancanti")
    st.stop()

# =========================
# CALCOLO DISTANZA
# =========================
def calcola_distanza(row):
    return geodesic((lat_centro, lon_centro), (row[lat_col], row[lon_col])).km

df["distanza_km"] = df.apply(calcola_distanza, axis=1).round(1)

# =========================
# FILTRO BASE
# =========================
df_filtrato = df[(df["distanza_km"] <= raggio_km) & (df["tipologia"].isin(tipologia_selezionata))].copy()
df_filtrato = df_filtrato.dropna(subset=[lat_col, lon_col])

# =========================
# KPI
# =========================
col1, col2, col3 = st.columns(3)
col1.metric("Impianti trovati", len(df_filtrato))
col2.metric("Raggio selezionato", f"{raggio_km} km")
col3.metric("Distanza media", f"{df_filtrato['distanza_km'].mean():.1f} km" if len(df_filtrato)>0 else "-")

# =========================
# MENU SELEZIONE (simula click mappa)
# =========================
impianti_list = df_filtrato["comune"].unique().tolist()
selected_comune = st.selectbox("📌 Seleziona impianto per evidenziazione", ["Tutti"] + impianti_list)
if selected_comune != "Tutti":
    st.session_state["selected_comune"] = selected_comune
else:
    st.session_state["selected_comune"] = None

# =========================
# MAPPA
# =========================
st.write("### 🗺️ Mappa interattiva")
if len(df_filtrato) > 0:
    df_filtrato["marker_size"] = df_filtrato["totale (t)"]
    df_filtrato["marker_opacity"] = 0.6
    df_filtrato["marker_color"] = df_filtrato["totale (t)"]

    if st.session_state.get("selected_comune"):
        sel = st.session_state["selected_comune"]
        df_filtrato.loc[df_filtrato["comune"] == sel, "marker_size"] = df_filtrato["totale (t)"].max() * 1.5
        df_filtrato.loc[df_filtrato["comune"] == sel, "marker_opacity"] = 1
        df_filtrato.loc[df_filtrato["comune"] == sel, "marker_color"] = df_filtrato["totale (t)"].max()

    fig = px.scatter_mapbox(
        df_filtrato,
        lat=lat_col,
        lon=lon_col,
        color="marker_color",
        size="marker_size",
        color_continuous_scale="Blues",
        size_max=25,
        hover_name="comune",
        hover_data={"distanza_km": True, lat_col: False, lon_col: False},
        zoom=7,
        height=600
    )
    fig.update_traces(marker=dict(opacity=df_filtrato["marker_opacity"]))
    fig.update_layout(mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0},
                      coloraxis_colorbar=dict(title="Totale trattato (t)"))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Nessun impianto trovato nel raggio selezionato.")

# =========================
# TABELLA INTERATTIVA
# =========================
st.write("### 📊 Tabella impianti")
df_tabella = df_filtrato.copy()
if st.session_state.get("selected_comune"):
    df_tabella = df_tabella[df_tabella["comune"] == st.session_state["selected_comune"]]

st.dataframe(df_tabella.sort_values("distanza_km"), height=400, use_container_width=True)

# =========================
# DOWNLOAD EXCEL
# =========================
output = io.BytesIO()
df_tabella.to_excel(output, index=False, engine='openpyxl')
output.seek(0)
st.download_button("💾 Scarica dati filtrati in Excel", data=output,
                   file_name="dati_filtrati.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
