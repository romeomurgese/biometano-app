import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from math import radians, cos, sin, asin
import numpy as np
from PIL import Image
import requests
from io import BytesIO

# =========================
# CONFIG STREAMLIT
# =========================
st.set_page_config(layout="wide")
# Logo + titolo
logo_url = "https://raw.githubusercontent.com/romeomurgese/biometano-app/main/bioenerys_logo.png"  # placeholder
response = requests.get(logo_url)
logo_img = Image.open(BytesIO(response.content))
st.image(logo_img, width=120)
st.title("🌱 Bioenerys Srl - Simulatore gara impianti rifiuti in Italia")

# =========================
# FUNZIONI
# =========================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * R * asin(np.sqrt(a))

def circle_coords(lat, lon, r_km, n_points=100):
    lat_circle, lon_circle = [], []
    for theta in np.linspace(0, 2*np.pi, n_points):
        dlat = (r_km/6371) * (180/np.pi) * np.sin(theta)
        dlon = (r_km/6371) * (180/np.pi) * np.cos(theta) / cos(radians(lat))
        lat_circle.append(lat + dlat)
        lon_circle.append(lon + dlon)
    return lat_circle, lon_circle

# =========================
# CARICA DATI
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("impianti_geocodificati.xlsx")
    df.columns = df.columns.str.lower()
    df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df = df.dropna(subset=["latitudine", "longitudine"])
    return df

df = load_data()

@st.cache_data
def load_comuni():
    df_comuni = pd.read_csv("comuni.csv")
    df_comuni["nome"] = df_comuni["name"].str.lower().str.strip()
    return df_comuni

df_comuni = load_comuni()
lista_comuni = df_comuni["nome"].sort_values().unique()

# =========================
# SIDEBAR - INPUT
# =========================
st.sidebar.header("⚙️ Parametri gara")
comune_sel = st.sidebar.selectbox("📍 Comune di gara", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio impianti (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa base di gara (€)", min_value=0, value=50)
impianti_nomi = df["comune"].str.lower().sort_values().unique()
impianto_extra = st.sidebar.text_input(
    "🔹 Aggiungi impianto manualmente (fuori dal raggio)", "",
    help="Scrivi il nome di un impianto e premi invio"
)
color_map_attivo = st.sidebar.checkbox("🎨 Color map secondo totale (t)")

# =========================
# TROVA COMUNE SELEZIONATO
# =========================
comune_sel_clean = str(comune_sel).strip().lower()
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
df_filtrato = df[df["distanza_km"] <= raggio_km]

# Aggiungi impianto extra se valido
if impianto_extra.strip() != "":
    imp_sel = df[df["comune"].str.lower() == impianto_extra.strip().lower()]
    if not imp_sel.empty:
        df_filtrato = pd.concat([df_filtrato, imp_sel]).drop_duplicates()

st.write(f"🔎 Impianti trovati nel raggio o selezionati: {len(df_filtrato)}")
if df_filtrato.empty:
    st.warning("⚠️ Nessun impianto trovato")

# =========================
# MAPPA
# =========================
st.subheader("📍 Mappa impianti e raggio di gara")
lat_circle, lon_circle = circle_coords(lat_centro, lon_centro, raggio_km)

fig = go.Figure()

# Trace raggio
fig.add_trace(go.Scattermapbox(
    lat=lat_circle,
    lon=lon_circle,
    mode='lines',
    fill='toself',
    fillcolor='rgba(0,200,0,0.1)',
    line=dict(color='green', width=2),
    name=f"Raggio {raggio_km} km"
))

# Trace comune di gara
fig.add_trace(go.Scattermapbox(
    lat=[lat_centro],
    lon=[lon_centro],
    mode='markers+text',
    text=[comune_sel],
    textposition="top center",
    marker=dict(size=14, color='red'),
    name="Comune di gara"
))

# Trace impianti
if not df_filtrato.empty:
    if color_map_attivo:
        # Color map secondo totale
        fig.add_trace(go.Scattermapbox(
            lat=df_filtrato["latitudine"],
            lon=df_filtrato["longitudine"],
            mode='markers+text',
            text=df_filtrato["comune"],
            textposition="top center",
            marker=dict(
                size=df_filtrato["totale (t)"].apply(lambda x: max(8, x/10)),
                color=df_filtrato["totale (t)"],
                colorscale="Viridis",
                colorbar=dict(title="Totale (t)"),
                sizemode="area",
                opacity=0.7
            ),
            hoverinfo="text+lat+lon",
            name="Totale (t)"
        ))
    else:
        # Punti neri pieni
        fig.add_trace(go.Scattermapbox(
            lat=df_filtrato["latitudine"],
            lon=df_filtrato["longitudine"],
            mode='markers+text',
            text=df_filtrato["comune"],
            textposition="top center",
            marker=dict(size=10, color="black"),
            hoverinfo="text+lat+lon",
            name="Impianti"
        ))

# Layout
fig.update_layout(
    mapbox_style="open-street-map",
    mapbox_center={"lat": lat_centro, "lon": lon_centro},
    mapbox_zoom=6,  # zoom iniziale moderato
    legend=dict(
        title="Legenda",
        itemsizing="constant",
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01,
        bgcolor="rgba(50,50,50,0.7)",
        font=dict(color="white")
    ),
    height=600
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# TABELLA IMPIANTI
# =========================
st.subheader("📋 Impianti partecipanti")
colonne_visibili = ["comune","tipologia","totale (t)","distanza_km"]
if not df_filtrato.empty:
    st.dataframe(df_filtrato[colonne_visibili])
