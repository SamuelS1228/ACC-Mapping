import io
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="ACC Cluster Map",
    page_icon="📍",
    layout="wide",
)

st.markdown("""
<style>
    #MainMenu, footer {visibility: hidden;}
    .block-container {padding-top: 1.2rem; padding-bottom: 0.5rem;}
    .map-title {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 1.5rem; font-weight: 700; color: #1a1a2e; margin-bottom: 2px;
    }
    .map-subtitle {font-size: 0.85rem; color: #666; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

DEFAULT_COLORS = [
    "#E63946", "#2196F3", "#4CAF50", "#FF9800", "#9C27B0",
    "#00BCD4", "#FF5722", "#607D8B", "#8BC34A", "#F06292",
    "#795548", "#3F51B5", "#FFC107",
]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📂 Upload Data")
    uploaded = st.file_uploader("Upload Excel file (.xlsx)", type=["xlsx", "xls"])

# ── Load data (no caching to avoid hashing issues) ────────────────────────────
def load_data(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    df.columns = df.columns.str.strip()
    df["Cluster"] = df["Cluster"].astype(str).str.strip()
    df = df.dropna(subset=["lat", "lng"])
    return df

if uploaded is None:
    st.markdown('<div class="map-title">ACC Cluster Map</div>', unsafe_allow_html=True)
    st.info("👈 Upload your Excel file in the sidebar to get started.")
    st.stop()

# Read bytes once, store in session state so we don't re-read on every widget interaction
file_key = uploaded.name + str(uploaded.size)
if "df" not in st.session_state or st.session_state.get("file_key") != file_key:
    st.session_state.df = load_data(uploaded.read())
    st.session_state.file_key = file_key

df = st.session_state.df
clusters_all = sorted(df["Cluster"].unique().tolist())

# ── Sidebar controls (after data loaded) ─────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("## 🔍 Filter Clusters")
    selected_clusters = st.multiselect(
        "Clusters to display",
        options=clusters_all,
        default=clusters_all,
    )

    st.markdown("---")
    st.markdown("## 🎨 Cluster Colors")
    cluster_colors = {}
    for i, cluster in enumerate(clusters_all):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(
                f"<div style='font-size:0.75rem; padding-top:7px; "
                f"overflow:hidden; text-overflow:ellipsis; white-space:nowrap; "
                f"max-width:160px;' title='{cluster}'>{cluster}</div>",
                unsafe_allow_html=True,
            )
        with col2:
            cluster_colors[cluster] = st.color_picker(
                label="c",
                value=DEFAULT_COLORS[i % len(DEFAULT_COLORS)],
                key=f"clr_{i}",
                label_visibility="collapsed",
            )

    st.markdown("---")
    st.markdown("## ⚙️ Map Settings")
    point_radius = st.slider("Point radius (m)", 3000, 30000, 8000, step=1000)
    point_opacity = st.slider("Opacity", 0.1, 1.0, 0.85, step=0.05)

# ── Filter ────────────────────────────────────────────────────────────────────
df_filtered = df[df["Cluster"].isin(selected_clusters)].copy() if selected_clusters else pd.DataFrame()

if df_filtered.empty:
    st.warning("No data to display — select at least one cluster in the sidebar.")
    st.stop()

# ── Build Folium map ──────────────────────────────────────────────────────────
center_lat = df_filtered["lat"].mean()
center_lng = df_filtered["lng"].mean()

m = folium.Map(
    location=[center_lat, center_lng],
    zoom_start=4,
    tiles="CartoDB positron",
    prefer_canvas=True,
)

# Remove folium branding for cleaner screenshots
m.get_root().html.add_child(folium.Element("""
<style>
  .leaflet-control-attribution { display: none !important; }
  .leaflet-bar a { color: #333 !important; }
</style>
"""))

for _, row in df_filtered.iterrows():
    color = cluster_colors.get(row["Cluster"], "#888888")
    folium.CircleMarker(
        location=[row["lat"], row["lng"]],
        radius=7,
        color="white",
        weight=1,
        fill=True,
        fill_color=color,
        fill_opacity=point_opacity,
        tooltip=folium.Tooltip(
            f"<b>Store #{int(row['Store Number'])}</b><br>"
            f"{row['City']}, {row['State']}<br>"
            f"<span style='color:#555'>{row['Cluster']}</span>",
            sticky=False,
        ),
    ).add_to(m)

# ── Legend HTML (injected into map) ──────────────────────────────────────────
legend_items = "".join([
    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
    f'<div style="width:13px;height:13px;border-radius:50%;background:{cluster_colors[c]};'
    f'border:1px solid #ccc;flex-shrink:0;"></div>'
    f'<span style="font-size:12px;color:#333;line-height:1.3">{c}</span>'
    f'</div>'
    for c in selected_clusters
])

legend_html = f"""
<div style="
    position: fixed; bottom: 30px; left: 30px; z-index: 9999;
    background: rgba(255,255,255,0.96);
    border: 1px solid #ddd; border-radius: 8px;
    padding: 14px 18px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.12);
    max-width: 280px;
    font-family: 'Helvetica Neue', Arial, sans-serif;
">
  <div style="font-weight:700;font-size:13px;color:#1a1a2e;margin-bottom:10px;">Clusters</div>
  {legend_items}
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# ── Render ────────────────────────────────────────────────────────────────────
st.markdown('<div class="map-title">ACC Store Cluster Map</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="map-subtitle">{len(df_filtered):,} stores &nbsp;·&nbsp; '
    f'{len(selected_clusters)} cluster(s) shown</div>',
    unsafe_allow_html=True,
)

st_folium(m, use_container_width=True, height=660, returned_objects=[])
