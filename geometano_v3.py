import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from math import radians, cos, sin, asin, sqrt
import numpy as np

# =========================
# HEADER + LOGO
# =========================
st.set_page_config(layout="wide")

col_logo, col_title = st.columns([1,5])
with col_logo:
    st.image("https://via.placeholder.com/200x100.png?text=Bioenerys+Srl", width=150)
with col_title:
    st.markdown("<h1 style='margin:0; padding-top:20px;'>Simulatore Gara Impianti Trattamento Rifiuti</h1>", unsafe_allow_html=True)

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
    url = "https://raw.githubusercontent.com/romeomurgese/biometano-app/main/impianti_geocodificati.xlsx"
    df = pd.read_excel(url)
    df.columns = df.columns.str.lower()
    df["totale (t)"] = pd.to_numeric(df["totale (t)"], errors="coerce").fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors="coerce")
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors="coerce")
    return df.dropna(subset=["latitudine", "longitudine"])

df = load_data()

@st.cache_data
def load_comuni():
    url = "https://raw.githubusercontent.com/romeomurgese/biometano-app/main/comuni.csv"
    dfc = pd.read_csv(url)
    dfc["nome"] = dfc["name"].str.lower().str.strip()
    return dfc

df_comuni = load_comuni()
lista_comuni = df_comuni["nome"].sort_values().unique()

# =========================
# SIDEBAR
# =========================
st.sidebar.header("⚙️ Parametri Gara")
comune_sel = st.sidebar.selectbox("📍 Comune di Gara", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio Impianti (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa Base di Gara (€)", min_value=0.0, value=100.0, step=10.0)

impianto_extra = st.sidebar.text_input(
    "🔹 Aggiungi impianto extra",
    "",
    help="Inserisci il nome di un impianto anche fuori raggio"
)

vista_colorata = st.sidebar.checkbox("🔄 Mappa colorata per Totale (t)")

# =========================
# CALCOLO COORDINATE COMUNE
# =========================
comune_sel_clean = comune_sel.strip().lower()
match = df_comuni[df_comuni["nome"] == comune_sel_clean]

if match.empty:
    st.error("❌ Comune non trovato")
    st.stop()

lat_centro = match.iloc[0]["lat"]
lon_centro = match.iloc[0]["lng"]

# =========================
# CALCOLO DISTANZE
# =========================
df["distanza_km"] = df.apply(
    lambda r: haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"]), axis=1
).round(1)

df_filtrato = df[df["distanza_km"] <= raggio_km]

if impianto_extra.strip():
    extra_sel = df[df["comune"].str.lower() == impianto_extra.strip().lower()]
    if not extra_sel.empty:
        df_filtrato = pd.concat([df_filtrato, extra_sel]).drop_duplicates()

# =========================
# DASHBOARD METRICHE
# =========================
st.subheader("📊 Statistiche Gara")
col1, col2, col3 = st.columns(3)
col1.metric("Impianti Totali", len(df_filtrato))
col2.metric("Totale (t) 🔋", f"{df_filtrato['totale (t)'].sum():,.1f}")
col3.metric("Tariffa Base (€)", f"{tariffa_base:,.2f}")

# =========================
# MAPPA
# =========================
st.subheader("📍 Mappa Impianti e Raggio Gara")
lat_circle, lon_circle = circle_coords(lat_centro, lon_centro, raggio_km)

fig = go.Figure()

# punti impianti
for _, row in df_filtrato.iterrows():
    fig.add_trace(go.Scattermapbox(
        lat=[row["latitudine"]],
        lon=[row["longitudine"]],
        mode="markers+text",
        marker=dict(size=10, color="black"),
        text=row["comune"],
        textposition="top center",
        hovertemplate="%{text}<br>Totale: %{customdata[0]} t<br>Distanza: %{customdata[1]} km",
        customdata=[[row["totale (t)"], row["distanza_km"]]],
        showlegend=False
    ))

# Raggio
fig.add_trace(go.Scattermapbox(
    lat=lat_circle,
    lon=lon_circle,
    mode="lines",
    fill="toself",
    fillcolor="rgba(0,200,0,0.1)",
    line=dict(color="green", width=2),
    name=f"Raggio {raggio_km} km"
))

# Comune di gara
fig.add_trace(go.Scattermapbox(
    lat=[lat_centro],
    lon=[lon_centro],
    mode="markers",
    marker=dict(size=14, color="red"),
    name="Comune di Gara"
))

fig.update_layout(
    mapbox_style="carto-positron",
    mapbox_center={"lat": lat_centro, "lon": lon_centro},
    mapbox_zoom=10,
    legend=dict(
        title="Legenda",
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01,
        bgcolor="rgba(0,0,0,0.5)",
        font=dict(color="white")
    ),
    margin=dict(r=0, t=0, l=0, b=0)
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# TABELLA IMPIANTI
# =========================
st.subheader("📋 Impianti Partecipanti")
col_vis = ["comune", "tipologia", "totale (t)", "distanza_km"]
if not df_filtrato.empty:
    st.dataframe(df_filtrato[col_vis])
