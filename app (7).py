import streamlit as st
import pandas as pd
import pydeck as pdk
import json

st.set_page_config(
    page_title="ACC Cluster Map",
    page_icon="📍",
    layout="wide",
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Hide Streamlit chrome */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {padding-top: 1.5rem; padding-bottom: 1rem;}

    /* Sidebar */
    section[data-testid="stSidebar"] {background: #f7f8fa;}
    section[data-testid="stSidebar"] .stMarkdown h2 {
        font-size: 1rem; font-weight: 700; color: #1a1a2e; margin-bottom: .25rem;
    }

    /* Color swatches */
    .swatch-row {display:flex; align-items:center; gap:8px; margin-bottom:4px;}
    .swatch {width:18px;height:18px;border-radius:50%;border:1px solid #ccc;display:inline-block;}

    /* Title */
    .map-title {
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 1.4rem; font-weight: 700; color: #1a1a2e;
        margin-bottom: 0.1rem;
    }
    .map-subtitle {
        font-size: 0.85rem; color: #666; margin-bottom: 0.6rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Default palette ───────────────────────────────────────────────────────────
DEFAULT_COLORS = [
    "#E63946", "#2196F3", "#4CAF50", "#FF9800", "#9C27B0",
    "#00BCD4", "#FF5722", "#607D8B", "#8BC34A", "#F06292",
    "#795548", "#3F51B5", "#FFC107",
]

def hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📂 Upload Data")
    uploaded = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])

    st.markdown("---")
    st.markdown("## 🗺️ Map Settings")
    point_size = st.slider("Point size", 2000, 20000, 7000, step=500)
    show_labels = st.checkbox("Show store number labels", value=False)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data(file) -> pd.DataFrame:
    import io
    bytes_data = file.read()
    df = pd.read_excel(io.BytesIO(bytes_data), engine="openpyxl")
    df.columns = df.columns.str.strip()
    df["Cluster"] = df["Cluster"].astype(str).str.strip()
    df = df.dropna(subset=["lat", "lng"])
    return df

if uploaded is None:
    st.markdown('<div class="map-title">ACC Cluster Map</div>', unsafe_allow_html=True)
    st.info("👈 Upload your Excel file in the sidebar to get started.")
    st.stop()

df = load_data(uploaded)
clusters_all = sorted(df["Cluster"].unique().tolist())

# ── Cluster color pickers ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("## 🎨 Cluster Colors")

    # Select which clusters to show
    selected_clusters = st.multiselect(
        "Clusters to display",
        options=clusters_all,
        default=clusters_all,
    )

    st.markdown("**Assign colors:**")
    cluster_colors: dict[str, str] = {}
    for i, cluster in enumerate(clusters_all):
        default_hex = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(
                f"<div style='font-size:0.78rem;padding-top:6px;"
                f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                f"max-width:150px;' title='{cluster}'>{cluster}</div>",
                unsafe_allow_html=True
            )
        with col2:
            hex_val = st.color_picker(
                label="",
                value=default_hex,
                key=f"color_{cluster}",
                label_visibility="collapsed",
            )
        cluster_colors[cluster] = hex_val

# ── Filter data ───────────────────────────────────────────────────────────────
df_filtered = df[df["Cluster"].isin(selected_clusters)].copy()

if df_filtered.empty:
    st.warning("No data to display. Select at least one cluster.")
    st.stop()

# ── Build layer data ──────────────────────────────────────────────────────────
df_filtered["color"] = df_filtered["Cluster"].map(
    lambda c: hex_to_rgb(cluster_colors.get(c, "#888888"))
)

layer_data = df_filtered[["lat", "lng", "color", "Store Number", "City", "State", "Cluster"]].copy()
layer_data["color_with_alpha"] = layer_data["color"].apply(lambda c: c + [220])

scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    data=layer_data,
    get_position="[lng, lat]",
    get_fill_color="color_with_alpha",
    get_radius=point_size,
    radius_min_pixels=4,
    radius_max_pixels=30,
    pickable=True,
    stroked=True,
    get_line_color=[255, 255, 255],
    line_width_min_pixels=1,
)

layers = [scatter_layer]

if show_labels:
    text_layer = pdk.Layer(
        "TextLayer",
        data=layer_data,
        get_position="[lng, lat]",
        get_text="Store Number",
        get_size=11,
        get_color=[30, 30, 30],
        get_anchor="'middle'",
        get_alignment_baseline="'bottom'",
    )
    layers.append(text_layer)

# ── Map view ──────────────────────────────────────────────────────────────────
center_lat = df_filtered["lat"].mean()
center_lng = df_filtered["lng"].mean()

view = pdk.ViewState(
    latitude=center_lat,
    longitude=center_lng,
    zoom=3.8,
    pitch=0,
)

tooltip = {
    "html": """
        <div style="font-family:Arial,sans-serif;font-size:13px;background:#fff;
                    color:#222;padding:8px 12px;border-radius:6px;
                    box-shadow:0 2px 8px rgba(0,0,0,.15);">
            <b>Store #{Store Number}</b><br>
            {City}, {State}<br>
            <span style="color:#666">{Cluster}</span>
        </div>
    """,
    "style": {"backgroundColor": "transparent", "border": "none"},
}

deck = pdk.Deck(
    layers=layers,
    initial_view_state=view,
    tooltip=tooltip,
    map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
)

# ── Legend ────────────────────────────────────────────────────────────────────
def build_legend(selected, colors):
    items = ""
    for c in selected:
        hex_c = colors.get(c, "#888")
        items += (
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;">'
            f'<div style="width:14px;height:14px;border-radius:50%;background:{hex_c};'
            f'border:1px solid #ccc;flex-shrink:0;"></div>'
            f'<span style="font-size:0.8rem;color:#333;">{c}</span>'
            f'</div>'
        )
    return f"""
    <div style="background:#ffffffee;border:1px solid #e0e0e0;border-radius:8px;
                padding:12px 16px;display:inline-block;max-width:320px;">
        <div style="font-weight:700;font-size:0.85rem;color:#1a1a2e;margin-bottom:8px;">
            Clusters
        </div>
        {items}
    </div>
    """

# ── Render ────────────────────────────────────────────────────────────────────
st.markdown('<div class="map-title">ACC Store Cluster Map</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="map-subtitle">{len(df_filtered)} stores · {len(selected_clusters)} cluster(s) shown</div>',
    unsafe_allow_html=True,
)

map_col, legend_col = st.columns([5, 1])

with map_col:
    st.pydeck_chart(deck, use_container_width=True, height=620)

with legend_col:
    st.markdown(build_legend(selected_clusters, cluster_colors), unsafe_allow_html=True)
