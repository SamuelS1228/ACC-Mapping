import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Cluster Site Mapper",
    layout="wide",
    initial_sidebar_state="expanded",
)

REQUIRED_COLUMNS = [
    "Store Number",
    "City",
    "State",
    "lat",
    "lng",
    "Cluster",
]

DEFAULT_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#76b7b2",
]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for col in df.columns:
        cleaned = str(col).strip().lower()
        if cleaned == "store number":
            rename_map[col] = "Store Number"
        elif cleaned == "city":
            rename_map[col] = "City"
        elif cleaned == "state":
            rename_map[col] = "State"
        elif cleaned == "lat":
            rename_map[col] = "lat"
        elif cleaned == "lng":
            rename_map[col] = "lng"
        elif cleaned == "cluster":
            rename_map[col] = "Cluster"
    return df.rename(columns=rename_map)


def validate_columns(df: pd.DataFrame):
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    suffix = uploaded_file.name.lower()

    if suffix.endswith(".xlsx") or suffix.endswith(".xls"):
        df = pd.read_excel(uploaded_file)
    elif suffix.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        raise ValueError("Unsupported file type. Please upload .xlsx, .xls, or .csv")

    df = normalize_columns(df)

    missing = validate_columns(df)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    df = df[REQUIRED_COLUMNS].copy()

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lng"] = pd.to_numeric(df["lng"], errors="coerce")
    df["Store Number"] = df["Store Number"].astype(str).str.strip()
    df["City"] = df["City"].astype(str).str.strip()
    df["State"] = df["State"].astype(str).str.strip()
    df["Cluster"] = df["Cluster"].astype(str).str.strip()

    df = df.dropna(subset=["lat", "lng"])
    df = df[df["Cluster"] != ""]

    return df


def build_color_map(clusters):
    color_map = {}
    for i, cluster in enumerate(clusters):
        color_map[cluster] = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]
    return color_map


st.title("Cluster Site Mapper")
st.caption(
    "Upload a site file, filter the clusters to display, and customize cluster colors for slide-ready screenshots."
)

with st.sidebar:
    st.header("Controls")

    uploaded_file = st.file_uploader(
        "Upload site file",
        type=["xlsx", "xls", "csv"],
        help="Required columns: Store Number, City, State, lat, lng, Cluster",
    )

    point_size = st.slider("Point size", min_value=8, max_value=28, value=14, step=1)
    map_height = st.slider("Map height", min_value=500, max_value=1200, value=760, step=20)
    show_title = st.toggle("Show title on chart", value=True)

if not uploaded_file:
    st.info("Upload your Excel file to generate the map.")
    st.markdown(
        """
        **Expected columns**
        - Store Number
        - City
        - State
        - lat
        - lng
        - Cluster
        """
    )
    st.stop()

try:
    df = read_uploaded_file(uploaded_file)
except Exception as e:
    st.error(str(e))
    st.stop()

all_clusters = sorted(df["Cluster"].dropna().astype(str).unique().tolist())

with st.sidebar:
    selected_clusters = st.multiselect(
        "Clusters to map",
        options=all_clusters,
        default=all_clusters,
    )

    st.subheader("Cluster colors")
    base_colors = build_color_map(all_clusters)
    cluster_colors = {}

    for cluster in all_clusters:
        cluster_colors[cluster] = st.color_picker(
            f"{cluster}",
            value=base_colors[cluster],
            key=f"color_{cluster}",
        )

filtered = df[df["Cluster"].isin(selected_clusters)].copy()

if filtered.empty:
    st.warning("No sites match the selected cluster filter.")
    st.stop()

fig = px.scatter_mapbox(
    filtered,
    lat="lat",
    lon="lng",
    color="Cluster",
    color_discrete_map=cluster_colors,
    hover_name="Store Number",
    hover_data={
        "City": True,
        "State": True,
        "Cluster": True,
        "lat": ":.4f",
        "lng": ":.4f",
    },
    zoom=3,
    height=map_height,
)

fig.update_traces(
    marker={
        "size": point_size,
        "opacity": 0.9,
    }
)

fig.update_layout(
    mapbox_style="carto-positron",
    margin={"l": 10, "r": 10, "t": 60 if show_title else 10, "b": 10},
    paper_bgcolor="white",
    plot_bgcolor="white",
    legend=dict(
        title="Cluster",
        orientation="h",
        yanchor="bottom",
        y=0.01,
        xanchor="left",
        x=0.01,
        bgcolor="rgba(255,255,255,0.85)",
    ),
)

if show_title:
    fig.update_layout(
        title={
            "text": "Site Map by Cluster",
            "x": 0.01,
            "xanchor": "left",
        }
    )

st.plotly_chart(fig, use_container_width=True)

col1, col2, col3 = st.columns(3)
col1.metric("Sites shown", f"{len(filtered):,}")
col2.metric("Clusters shown", f"{filtered['Cluster'].nunique():,}")
col3.metric("Total uploaded", f"{len(df):,}")

with st.expander("Preview filtered data"):
    st.dataframe(filtered, use_container_width=True, hide_index=True)

csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download filtered data as CSV",
    data=csv_bytes,
    file_name="filtered_cluster_sites.csv",
    mime="text/csv",
)
