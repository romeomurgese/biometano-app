import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from math import radians, cos, sin, asin
import numpy as np
from PIL import Image
import requests
from io import BytesIO

st.set_page_config(layout="wide")
st.title("🌱 Simulatore gara impianti trattamento rifiuti in Italia")

# =========================
# Logo Bioenerys
# =========================
logo_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Placeholder_no_text.svg/1200px-Placeholder_no_text.svg.png"
try:
    response = requests.get(logo_url)
    logo_img = Image.open(BytesIO(response.content))
    st.image(logo_img, width=120)
except:
    st.write("Bioenerys Srl")

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
# CARICA DATI IMPIANTI
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

# =========================
# CARICA COMUNI
# =========================
@st.cache_data
def load_comuni():
    df_comuni = pd.read_csv("comuni.csv")
    df_comuni["nome"] = df_comuni["name"].str.lower().str.strip()
    return df_comuni

df_comuni = load_comuni()
lista_comuni = df_comuni["nome"].sort_values().unique()

# =========================
# SIDEBAR - DASHBOARD INPUT
# =========================
st.sidebar.header("⚙️ Parametri gara")
comune_sel = st.sidebar.selectbox("📍 Comune di gara", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio impianti (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa base (€)", min_value=0.0, value=100.0, step=1.0)

# Impianti extra multipli
impianti_extra = st.sidebar.multiselect(
    "🔹 Aggiungi impianti manualmente (fuori dal raggio)",
    options=df["comune"].sort_values().unique(),
    default=[]
)

# Checkbox color map
use_color_map = st.sidebar.checkbox("🌈 Color map secondo totale (t)", value=False)

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

df_filtrato = df[df["distanza_km"] <= raggio_km].copy()
if impianti_extra:
    df_extra_sel = df[df["comune"].isin(impianti_extra)]
    df_filtrato = pd.concat([df_filtrato, df_extra_sel]).drop_duplicates()

# Colonne per editor
df_filtrato["in_gara"] = True
df_filtrato["tariffa"] = tariffa_base

# =========================
# DATA EDITOR INTERATTIVO
# =========================
st.subheader("📋 Impianti partecipanti")
colonne_visibili = ["in_gara", "comune", "tipologia", "totale (t)", "distanza_km", "tariffa"]

edited_df = st.data_editor(
    df_filtrato[colonne_visibili],
    column_config={
        "in_gara": st.column_config.CheckboxColumn("In gara"),
        "tariffa": st.column_config.NumberColumn("Tariffa (€)", min_value=0.0, step=1.0, format="%0.2f")
    },
    hide_index=True
)

df_finale = edited_df[edited_df["in_gara"] == True]

st.write(f"🔎 Impianti selezionati: {len(df_finale)}")
if df_finale.empty:
    st.warning("⚠️ Nessun impianto selezionato")

# =========================
# MAPPA
# =========================
st.subheader("📍 Mappa impianti e raggio di gara")
lat_circle, lon_circle = circle_coords(lat_centro, lon_centro, raggio_km)

# Mappa scatter
if not df_finale.empty:
    if use_color_map:
        sizeref = 2.*max(df_finale["totale (t)"])/100**2
        fig = px.scatter_mapbox(
            df_finale,
            lat="latitudine",
            lon="longitudine",
            size="totale (t)",
            color="totale (t)",
            hover_name="comune",
            hover_data=["tipologia","totale (t)","distanza_km"],
            center={"lat": lat_centro, "lon": lon_centro},
            zoom=6,
            height=600,
            size_max=50,
            color_continuous_scale="YlOrRd"
        )
    else:
        fig = px.scatter_mapbox(
            df_finale,
            lat="latitudine",
            lon="longitudine",
            hover_name="comune",
            hover_data=["tipologia","totale (t)","distanza_km"],
            center={"lat": lat_centro, "lon": lon_centro},
            zoom=6,
            height=600,
        )
        fig.update_traces(marker=dict(size=10, color="black"))

# Raggio e centro
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
    mode='markers+text',
    marker=dict(size=14, color='red'),
    text=[comune_sel],
    textposition="top center",
    name="Comune di gara"
))

# Ottimizza legenda
fig.update_layout(
    mapbox_style="open-street-map",
    legend=dict(title="Legenda", yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)"),
    margin={"r":0,"t":0,"l":0,"b":0}
)

st.plotly_chart(fig, use_container_width=True)
