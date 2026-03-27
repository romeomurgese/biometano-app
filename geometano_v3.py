import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import plotly.graph_objects as go
from math import radians, cos, sin, asin, sqrt
import numpy as np

# =========================
# CONFIG STREAMLIT
# =========================
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
# CARICA DATI IMPIANTI
# =========================
@st.cache_data
def load_data():
    # Usa URL GitHub raw per evitare problemi di percorsi locali
    url = "https://raw.githubusercontent.com/romeomurgese/biometano-app/main/impianti_geocodificati.xlsx"
    df = pd.read_excel(url)
    df.columns = df.columns.str.lower()
    df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df = df.dropna(subset=["latitudine", "longitudine"])
    return df

df = load_data()

# =========================
# CARICA COMUNI
# =========================
@st.cache_data
def load_comuni():
    df_comuni = pd.read_csv("https://raw.githubusercontent.com/romeomurgese/biometano-app/main/comuni.csv")
    df_comuni["nome"] = df_comuni["name"].str.lower().str.strip()
    return df_comuni

df_comuni = load_comuni()
lista_comuni = df_comuni["nome"].sort_values().unique()

# =========================
# SIDEBAR - CRUSCOTTO INPUT
# =========================
st.sidebar.header("⚙️ Parametri gara")

comune_sel = st.sidebar.selectbox("📍 Comune di gara", lista_comuni)

raggio_km = st.sidebar.slider("📏 Raggio impianti (km)", 1, 200, 50)

# Multiselect impianti extra (fuori dal raggio)
impianti_nomi = df["comune"].sort_values().unique()
impianti_extra_sel = st.sidebar.multiselect(
    "🔹 Aggiungi impianti manualmente (fuori dal raggio)",
    options=impianti_nomi
)

# =========================
# TROVA COMUNE SELEZIONATO
# =========================
comune_sel_clean = comune_sel.strip().lower()
match = df_comuni[df_comuni["nome"] == comune_sel_clean]
if match.empty:
    st.error("❌ Comune non trovato")
    st.stop()

row_comune = match.iloc[0]
lat_centro = row_comune["lat"]
lon_centro = row_comune["lng"]

# =========================
# CALCOLO DISTANZE
# =========================
df["distanza_km"] = df.apply(
    lambda r: haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"]), axis=1
).round(1)

# Impianti nel raggio
df_filtrato = df[df["distanza_km"] <= raggio_km]

# Aggiungi impianti extra selezionati
if impianti_extra_sel:
    imp_sel = df[df["comune"].isin(impianti_extra_sel)]
    df_filtrato = pd.concat([df_filtrato, imp_sel]).drop_duplicates()

st.write(f"🔎 Impianti trovati nel raggio o selezionati: {len(df_filtrato)}")
if df_filtrato.empty:
    st.warning("⚠️ Nessun impianto trovato")

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
    hover_data=["tipologia","totale (t)","distanza_km"],
    center={"lat": lat_centro, "lon": lon_centro},
    zoom=7,
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
fig.add_trace(go.Scattermapbox(
    lat=[lat_centro],
    lon=[lon_centro],
    mode='markers',
    marker=dict(size=14, color='red'),
    name="Comune di gara"
))

# Legenda a destra e leggibile
fig.update_layout(
    mapbox_style="open-street-map",
    legend=dict(
        title="Legenda",
        yanchor="top",
        y=0.95,
        xanchor="right",
        x=0.99,
        bgcolor="rgba(255,255,255,0.7)"
    )
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# TABELLA IMPIANTI
# =========================
st.subheader("📋 Impianti partecipanti")
colonne_visibili = ["comune","tipologia","totale (t)","distanza_km"]
if not df_filtrato.empty:
    st.dataframe(df_filtrato[colonne_visibili])
