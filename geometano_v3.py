# app.py - versione con raggio evidenziato sulla mappa

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from math import radians, cos, sin, asin, sqrt
import io
import requests
import numpy as np

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

st.set_page_config(layout="wide")
st.title("🌱 Simulatore gara impianti trattamento rifiuti in Italia")

# =========================
# FUNZIONI
# =========================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(sqrt(a))

def circle_coords(lat, lon, r_km, n_points=100):
    lat_circle = []
    lon_circle = []
    for theta in np.linspace(0, 2*np.pi, n_points):
        dlat = (r_km/6371) * (180/np.pi) * np.sin(theta)
        dlon = (r_km/6371) * (180/np.pi) * np.cos(theta) / cos(radians(lat))
        lat_circle.append(lat + dlat)
        lon_circle.append(lon + dlon)
    return lat_circle, lon_circle

# =========================
# CARICAMENTO DATI DA GITHUB
# =========================
@st.cache_data
def load_data():
    github_url = "https://raw.githubusercontent.com/romeomurgese/biometano-app/main/impianti_geocodificati.xlsx"
    r = requests.get(github_url)
    r.raise_for_status()
    df = pd.read_excel(io.BytesIO(r.content))
    df.columns = df.columns.str.lower()
    df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df = df.dropna(subset=["latitudine", "longitudine"])
    return df

df = load_data()

# =========================
# LISTA COMUNI ITALIANI
# =========================
# puoi usare un dataset CSV con tutti i comuni italiani oppure
# definire manualmente una lista minima di esempio
# =========================
# CARICAMENTO COMUNI ITALIANI REALI
# =========================
@st.cache_data
def load_comuni():
    url_comuni = "https://raw.githubusercontent.com/matteocontrini/comuni-json/master/comuni.json"
    comuni = pd.read_json(url_comuni)
    return comuni

df_comuni = load_comuni()

# lista comuni ordinata
lista_comuni = df_comuni["nome"].sort_values().unique()

comune_sel = st.selectbox(
    "Comune di gara (tutti i comuni italiani)",
    lista_comuni
)

raggio_km = st.slider("Raggio impianti partecipanti (km)", 1, 200, 50)

# =========================
# OTTIENI LAT/LON DEL COMUNE SELEZIONATO
# =========================
@st.cache_data
def geocode_comune(comune):
    geolocator = Nominatim(user_agent="simulatore_gara")
    try:
        location = geolocator.geocode(f"{comune}, Italia", timeout=10)
        if location:
            return location.latitude, location.longitude
    except GeocoderTimedOut:
        return None, None
    return None, None

#lat_centro, lon_centro = geocode_comune(comune_sel)
row_comune = df_comuni[df_comuni["nome"] == comune_sel].iloc[0]

lat_centro = row_comune["lat"]
lon_centro = row_comune["lng"]

if lat_centro is None or lon_centro is None:
    st.error("❌ Non è stato possibile geocodificare il comune selezionato.")
    st.stop()

# =========================
# CALCOLO DISTANZE
# =========================
df["distanza_km"] = df.apply(lambda r: haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"]), axis=1).round(1)
df_filtrato = df[df["distanza_km"] <= raggio_km]

# =========================
# MAPPA
# =========================
st.subheader("📍 Mappa impianti e raggio di gara")
lat_circle, lon_circle = circle_coords(lat_centro, lon_centro, raggio_km)

fig = px.scatter_mapbox(
    df_filtrato,
    lat="latitudine",
    lon="longitudine",
    size="totale (t)",
    color="totale (t)",
    hover_name="comune",
    hover_data=["tipologia", "totale (t)", "distanza_km"],
    zoom=6,
    height=600
)

fig.add_trace(go.Scattermapbox(
    lat=lat_circle,
    lon=lon_circle,
    mode='lines',
    fill='toself',
    fillcolor='rgba(0,200,0,0.1)',
    line=dict(color='green', width=2),
    name=f"Raggio {raggio_km} km"
))

fig.update_layout(mapbox_style="open-street-map")
st.plotly_chart(fig, use_container_width=True)

# =========================
# TABELLA (nasconde lat/lon)
# =========================
st.subheader("📋 Impianti partecipanti")
colonne_visibili = ["comune", "tipologia", "totale (t)", "distanza_km"]
st.dataframe(df_filtrato[colonne_visibili])
