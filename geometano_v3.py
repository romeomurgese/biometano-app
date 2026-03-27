import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from math import radians, cos, sin, asin, sqrt
import numpy as np

st.set_page_config(layout="wide")
st.title("🌱 Bioenerys Srl - Simulatore gara impianti trattamento rifiuti in Italia")

# =========================
# Logo Bioenerys Srl
# =========================
logo_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7f/Placeholder_logo.png/320px-Placeholder_logo.png"
st.image(logo_url, width=150)

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

def calcola_zoom(raggio_km):
    if raggio_km <= 10:
        return 12
    elif raggio_km <= 25:
        return 11
    elif raggio_km <= 50:
        return 10
    elif raggio_km <= 100:
        return 9
    elif raggio_km <= 200:
        return 8
    else:
        return 7

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
# SIDEBAR - CRUSCOTTO INPUT
# =========================
st.sidebar.header("⚙️ Parametri gara")
comune_sel = st.sidebar.selectbox("📍 Comune di gara", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio impianti (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa base di gara (€)", min_value=0.0, value=100.0, step=10.0)

# Input manuale di impianti extra
impianti_nomi = df["comune"].str.lower().sort_values().unique()
impianto_extra = st.sidebar.text_input(
    "🔹 Aggiungi impianto manualmente (fuori dal raggio)", 
    "", 
    help="Scrivi il nome di un impianto e premi invio"
)

# Checkbox per color map secondo totale
color_map = st.sidebar.checkbox("🎨 Color map secondo totale (t)")

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

# Zoom iniziale più ampio
zoom_iniziale = 7 + max(0, 10 - raggio_km/20)  # zoom più ampio per raggio grande

fig = go.Figure()

# Raggio
fig.add_trace(go.Scattermapbox(
    lat=lat_circle,
    lon=lon_circle,
    mode='lines',
    fill='toself',
    fillcolor='rgba(0,200,0,0.1)',
    line=dict(color='green', width=2),
    name=f"Raggio {raggio_km} km"
))

# Comune di gara
fig.add_trace(go.Scattermapbox(
    lat=[lat_centro],
    lon=[lon_centro],
    mode='markers+text',
    marker=dict(size=14, color='red'),
    text=[comune_sel.capitalize()],
    textposition="top right",
    name="Comune di gara"
))

# Impianti
for idx, row in df_filtrato.iterrows():
    if color_map:
        size = max(5, row["totale (t)"]**0.5)
        color = row["totale (t)"]
    else:
        size = 8
        color = "black"

    fig.add_trace(go.Scattermapbox(
        lat=[row["latitudine"]],
        lon=[row["longitudine"]],
        mode='markers+text',
        marker=dict(
            size=size, 
            color=color, 
            showscale=color_map, 
            colorscale="Viridis" if color_map else None,
            colorbar=dict(
                title="Totale (t)",
                thickness=15,
                x=0.95,
                y=0.5,
                outlinecolor="rgba(0,0,0,0.5)",
                titleside="right"
            ) if color_map else None
        ),
        text=[row["comune"]],
        textposition="top center",
        hoverinfo="text",
        name=row["comune"]
    ))

# Layout mappa
fig.update_layout(
    mapbox_style="open-street-map",
    mapbox=dict(center={"lat": lat_centro, "lon": lon_centro}, zoom=zoom_iniziale),
    legend=dict(
        title="Legenda",
        itemsizing='constant',
        bgcolor="rgba(0,0,0,0.5)",
        x=0.01, y=0.99
    ),
    margin={"l":0,"r":0,"t":0,"b":0}
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# TABELLA IMPIANTI
# =========================
st.subheader("📋 Impianti partecipanti")
colonne_visibili = ["comune","tipologia","totale (t)","distanza_km"]
if not df_filtrato.empty:
    st.dataframe(df_filtrato[colonne_visibili])
