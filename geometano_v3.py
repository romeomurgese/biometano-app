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
