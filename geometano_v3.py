import streamlit as st
from PIL import Image
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from math import radians, cos, sin, asin
import time
import unicodedata

# =========================
# CONFIG
# =========================
st.set_page_config(layout="wide")

# =========================
# HEADER CON LOGO
# =========================
col1, col2 = st.columns([0.9, 0.1])

with col1:
    st.title("🌱 Bioenerys Srl - Simulatore gara")

with col2:
    try:
        logo = Image.open("BIOENERYS.png")
        st.image(logo, width=120)
    except:
        pass

# =========================
# SESSION STATE
# =========================
if "offerte_custom" not in st.session_state:
    st.session_state.offerte_custom = {}

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

def normalize_cols(df):
    df.columns = (
        df.columns
        .str.lower()
        .str.replace(" ", "_")
        .map(lambda x: unicodedata.normalize('NFKD', str(x)).encode('ascii', errors='ignore').decode('utf-8'))
    )
    return df

# penalità realistica
def calcola_penalita(distanza, raggio, penale_km, tipo):
    km_fuori = max(0, distanza - raggio)

    if tipo == "Lineare":
        return km_fuori * penale_km

    elif tipo == "Scaglioni":
        if km_fuori <= 20:
            return km_fuori * penale_km
        elif km_fuori <= 50:
            return (20 * penale_km) + (km_fuori - 20) * penale_km * 1.5
        else:
            return (
                (20 * penale_km)
                + (30 * penale_km * 1.5)
                + (km_fuori - 50) * penale_km * 2
            )

# =========================
# LOAD DATI
# =========================
@st.cache_data
def load_data():
    df = pd.read_excel("impianti_geocodificati.xlsx")
    df = normalize_cols(df)
    df["totale_(t)"] = pd.to_numeric(df["totale_(t)"], errors='coerce').fillna(1)
    df["latitudine"] = pd.to_numeric(df["latitudine"], errors='coerce')
    df["longitudine"] = pd.to_numeric(df["longitudine"], errors='coerce')
    df["flag"] = True
    return df

if st.button("🔄 Aggiorna database impianti"):
    st.cache_data.clear()

df = load_data()

@st.cache_data
def load_comuni():
    df_comuni = pd.read_csv("comuni.csv")
    df_comuni["nome"] = df_comuni["name"].str.lower().str.strip()
    return df_comuni

df_comuni = load_comuni()
lista_comuni = df_comuni["nome"].sort_values().unique()

# =========================
# SIDEBAR
# =========================
st.sidebar.header("⚙️ Parametri")

comune_sel = st.sidebar.selectbox("📍 Comune", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa base (€)", value=100.0)

tipo_distanza = st.sidebar.selectbox(
    "📐 Metodo distanza",
    ["Linea retta", "Stimata stradale (+30%)"]
)

st.sidebar.subheader("🚛 Logistica")

costo_km_ton = st.sidebar.number_input("Costo trasporto €/ton/km", value=0.12)

tipo_penale = st.sidebar.selectbox(
    "⚖️ Penalità",
    ["Lineare", "Scaglioni"]
)

penale_km = st.sidebar.number_input("Penalità €/km", value=0.5)

tipologie = df["tipologia"].dropna().unique()
tipologie_sel = st.sidebar.multiselect("🏭 Tipologie", tipologie, default=list(tipologie))

df["label"] = (
    df["comune"] + " (" + df["provincia"].fillna("") + ")"
    + " - " + df["societa"].fillna("N/D")
)

extra_sel = st.sidebar.multiselect("➕ Impianti extra", df["label"].unique())

# =========================
# CENTRO
# =========================
row = df_comuni[df_comuni["nome"] == comune_sel].iloc[0]
lat_centro = row["lat"]
lon_centro = row["lng"]

# =========================
# DISTANZA
# =========================
def calcola_distanza(r):
    base = haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"])

    if tipo_distanza == "Stimata stradale (+30%)":
        return base * 1.3

    return base

df["distanza_km"] = df.apply(calcola_distanza, axis=1).round(1)

# =========================
# FILTRO
# =========================
df_filtrato = df[
    (df["tipologia"].isin(tipologie_sel)) &
    (df["distanza_km"] <= raggio_km)
]

if extra_sel:
    df_extra = df[df["label"].isin(extra_sel)]
    df_filtrato = pd.concat([df_filtrato, df_extra])

df_filtrato = df_filtrato.drop_duplicates()

# =========================
# OFFERTA
# =========================
offerte = []
for _, r in df_filtrato.iterrows():
    key = r["label"]
    offerte.append(st.session_state.offerte_custom.get(key, tariffa_base))

df_filtrato["offerta"] = offerte

# =========================
# TABELLA
# =========================
st.subheader("📋 Impianti partecipanti")

df_table = df_filtrato[[
    "flag","label","tipologia","totale_(t)","distanza_km","offerta"
]].rename(columns={
    "flag":"Seleziona",
    "label":"Impianto",
    "tipologia":"Tipologia",
    "totale_(t)":"Quantità",
    "distanza_km":"Distanza",
    "offerta":"Offerta (€)"
})

st.markdown("💡 **La colonna Offerta (€) è modificabile**")

edited = st.data_editor(
    df_table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Seleziona": st.column_config.CheckboxColumn(),
        "Offerta (€)": st.column_config.NumberColumn(
            min_value=0,
            help="Inserisci la tua offerta"
        ),
    },
    disabled=["Impianto","Tipologia","Quantità","Distanza"]
)

# salva stato
for _, r in edited.iterrows():
    st.session_state.offerte_custom[r["Impianto"]] = r["Offerta (€)"]

df_filtrato["flag"] = edited["Seleziona"].values
df_filtrato["offerta"] = edited["Offerta (€)"].values

# =========================
# MAPPA
# =========================
st.subheader("📍 Mappa")

df_mappa = df_filtrato[df_filtrato["flag"]]

lat_circle, lon_circle = circle_coords(lat_centro, lon_centro, raggio_km)

fig = go.Figure()

fig.add_trace(go.Scattermapbox(
    lat=lat_circle,
    lon=lon_circle,
    mode='lines',
    fill='toself'
))

fig.add_trace(go.Scattermapbox(
    lat=[lat_centro],
    lon=[lon_centro],
    mode='markers',
    marker=dict(size=14, color='red'),
))

fig.add_trace(go.Scattermapbox(
    lat=df_mappa["latitudine"],
    lon=df_mappa["longitudine"],
    mode='markers+text',
    text=df_mappa["label"],
    marker=dict(size=10, color='black'),
))

fig.update_layout(
    mapbox_style="open-street-map",
    mapbox=dict(center=dict(lat=lat_centro, lon=lon_centro), zoom=6),
    height=700
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# SIMULA
# =========================
if st.button("🚀 Simula gara"):

    df_finale = df_filtrato[df_filtrato["flag"]].copy()

    df_finale["km_fuori"] = (df_finale["distanza_km"] - raggio_km).clip(lower=0)

    df_finale["penalita"] = df_finale.apply(
        lambda r: calcola_penalita(
            r["distanza_km"],
            raggio_km,
            penale_km,
            tipo_penale
        ),
        axis=1
    )

    df_finale["costo_trasporto"] = (
        df_finale["distanza_km"] * costo_km_ton * df_finale["totale_(t)"]
    )

    df_finale["valore_netto"] = (
        df_finale["offerta"]
        - df_finale["costo_trasporto"]
        - df_finale["penalita"]
    )

    df_finale = df_finale.sort_values("valore_netto", ascending=False)
    df_finale["ranking"] = range(1, len(df_finale)+1)

    # KPI
    best = df_finale.iloc[0]
    worst = df_finale.iloc[-1]

    col1, col2, col3 = st.columns(3)
    col1.metric("🥇 Miglior valore", f"{best['valore_netto']:.1f} €")
    col2.metric("🚛 Trasporto medio", f"{df_finale['costo_trasporto'].mean():.1f} €")
    col3.metric("Δ Spread", f"{best['valore_netto'] - worst['valore_netto']:.1f} €")

    # Tabella
    st.subheader("🏆 Risultato gara")

    st.dataframe(
        df_finale[[
            "ranking","label","offerta","costo_trasporto","penalita","valore_netto"
        ]].rename(columns={
            "ranking":"Posizione",
            "label":"Impianto",
            "offerta":"Offerta (€)",
            "costo_trasporto":"Trasporto (€)",
            "penalita":"Penalità (€)",
            "valore_netto":"Valore netto (€)"
        }),
        use_container_width=True,
        hide_index=True
    )

    # Grafico
    fig_bar = px.bar(df_finale, x="label", y="valore_netto")
    st.plotly_chart(fig_bar, use_container_width=True)
