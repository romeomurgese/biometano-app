import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from math import radians, cos, sin, asin
import numpy as np
from io import BytesIO
from PIL import Image
import requests

st.set_page_config(layout="wide")
st.title("🌱 Simulatore gara impianti trattamento rifiuti in Italia")

# =========================
# LOGO E TITOLI
# =========================
st.markdown("### Bioenerys Srl")
# Placeholder logo
try:
    url_logo = "https://via.placeholder.com/150x50.png?text=Bioenerys+Logo"
    response = requests.get(url_logo)
    logo_img = Image.open(BytesIO(response.content))
    st.image(logo_img, width=150)
except:
    st.write("Logo non disponibile")

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
# SIDEBAR
# =========================
st.sidebar.header("⚙️ Parametri gara")
comune_sel = st.sidebar.selectbox("📍 Comune di gara", lista_comuni)
raggio_km = st.sidebar.slider("📏 Raggio impianti (km)", 1, 200, 50)
tariffa_base = st.sidebar.number_input("💰 Tariffa base gara (€)", value=0, step=10)

# Inserimento multiplo impianti extra
impianti_nomi = df["comune"].str.lower().sort_values().unique()
impianti_extra = st.sidebar.multiselect(
    "🔹 Aggiungi impianti extra (fuori raggio)", 
    options=impianti_nomi,
    default=[]
)

# Filtro tipologia impianti
tipologie_disponibili = df["tipologia"].dropna().unique()
tipologie_sel = st.sidebar.multiselect(
    "🏭 Seleziona tipologie impianto", 
    options=tipologie_disponibili,
    default=tipologie_disponibili
)

use_color_map = st.sidebar.checkbox("🎨 Color map secondo totale (t)", value=False)

# =========================
# TROVA COMUNE CENTRO
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
# CALCOLO DISTANZE E FILTRO
# =========================
df["distanza_km"] = df.apply(
    lambda r: haversine(lat_centro, lon_centro, r["latitudine"], r["longitudine"]), axis=1
).round(1)

df_filtrato = df[df["distanza_km"] <= raggio_km]

# Aggiungi impianti extra
if impianti_extra:
    imp_sel = df[df["comune"].str.lower().isin(impianti_extra)]
    df_filtrato = pd.concat([df_filtrato, imp_sel]).drop_duplicates().reset_index(drop=True)

# Filtro tipologie
df_filtrato = df_filtrato[df_filtrato["tipologia"].isin(tipologie_sel)]

# Flag attivi per rimuovere impianti
if "flag" not in df_filtrato.columns:
    df_filtrato["flag"] = True

# =========================
# MAPPA
# =========================
st.subheader("📍 Mappa impianti e raggio di gara")
lat_circle, lon_circle = circle_coords(lat_centro, lon_centro, raggio_km)

fig = go.Figure()
# Cerchio raggio
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
    text=[comune_sel],
    textposition="top right",
    name="Comune di gara"
))

# Punti impianti filtrati
df_finale = df_filtrato[df_filtrato["flag"] == True].copy()
if not df_finale.empty:
    hover_cols = [c for c in ["tipologia","totale (t)","distanza_km"] if c in df_finale.columns]
    
    if use_color_map:
        fig_imp = px.scatter_mapbox(
            df_finale,
            lat="latitudine",
            lon="longitudine",
            size="totale (t)",
            color="totale (t)",
            hover_name="comune",
            hover_data=hover_cols,
            size_max=40,
            color_continuous_scale="YlOrRd"
        )
    else:
        fig_imp = px.scatter_mapbox(
            df_finale,
            lat="latitudine",
            lon="longitudine",
            hover_name="comune",
            hover_data=hover_cols
        )
        fig_imp.update_traces(marker=dict(size=10, color="black"))
    
    for trace in fig_imp.data:
        fig.add_trace(trace)

fig.update_layout(
    mapbox_style="open-street-map",
    mapbox=dict(center=dict(lat=lat_centro, lon=lon_centro), zoom=6),
    legend=dict(title="Legenda", yanchor="top", y=0.99, xanchor="left", x=0.01,
                bgcolor="rgba(50,50,50,0.7)", font=dict(color="white"))
)
st.plotly_chart(fig, use_container_width=True)

# =========================
# TABELLA INTERATTIVA CON FLAG E TARIFFA
# =========================
st.subheader("📋 Impianti partecipanti")

if not df_finale.empty:
    rows = []
    for idx in df_finale.index:
        col1, col2 = st.columns([0.2,0.8])
        with col1:
            flag = st.checkbox(f"", value=True, key=f"chk_{idx}")
        with col2:
            tariffa = st.number_input(
                f"{df_finale.loc[idx,'comune']} - {df_finale.loc[idx,'tipologia']}",
                value=float(tariffa_base),
                step=1.0,
                key=f"tar_{idx}"
            )
        if flag:
            row = df_finale.loc[idx].to_dict()
            row["tariffa (€)"] = tariffa
            rows.append(row)
    df_mostra = pd.DataFrame(rows)
    if not df_mostra.empty:
        st.dataframe(df_mostra[["comune","tipologia","totale (t)","distanza_km","tariffa (€)"]])
    else:
        st.write("⚠️ Nessun impianto selezionato")
else:
    st.write("⚠️ Nessun impianto disponibile")
