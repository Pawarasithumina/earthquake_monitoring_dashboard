import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

WORKER_EXPORT_URL = (
    "https://earthquake-monitoring-system."
    "pawarasithumina24.workers.dev/api/warehouse-export"
)
PAGE_SIZE = 1000
MAX_GLOBE_POINTS = 1800

st.set_page_config(
    page_title="Seismic Intelligence | Global Monitor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root {
      --bg:#07111f; --panel:#0d1b2b; --line:rgba(133,178,211,.16);
      --cyan:#55d6e8; --muted:#91a7ba; --text:#eaf4fb;
    }
    html,body,[class*="css"]{font-family:'Manrope',sans-serif}
    .stApp{background:radial-gradient(ellipse at 12% 0%,rgba(29,107,151,.18),transparent 34%),radial-gradient(ellipse at 92% 8%,rgba(37,77,135,.15),transparent 30%),var(--bg);color:var(--text)}
    [data-testid="stHeader"]{background:rgba(7,17,31,.72)}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,#0b1a2a,#081421);border-right:1px solid var(--line)}
    [data-testid="stSidebar"] *{color:#d9e8f3}
    .block-container{padding-top:1.6rem;padding-bottom:3rem;max-width:1500px}
    h1,h2,h3{color:var(--text)!important;letter-spacing:-.035em}
    p,label,.stCaption{color:var(--muted)}
    [data-testid="stMetric"]{background:linear-gradient(145deg,rgba(17,39,59,.96),rgba(10,27,43,.96));border:1px solid var(--line);border-radius:16px;padding:18px 20px;box-shadow:0 12px 32px rgba(0,0,0,.16);animation:riseIn .65s ease both;transition:transform .22s,border-color .22s,box-shadow .22s}
    [data-testid="stMetric"]:hover{transform:translateY(-4px);border-color:rgba(85,214,232,.48);box-shadow:0 16px 36px rgba(0,0,0,.24),0 0 22px rgba(85,214,232,.08)}
    [data-testid="stMetricLabel"]{color:#91a7ba!important;font-size:.78rem}
    [data-testid="stMetricValue"]{color:#f1f8fc!important;font-weight:800}
    div[data-testid="stPlotlyChart"]{background:rgba(13,27,43,.74);border:1px solid var(--line);border-radius:16px;padding:8px;transition:border-color .2s}
    div[data-testid="stPlotlyChart"]:hover{border-color:rgba(85,214,232,.35)}
    div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:14px;overflow:hidden}
    .hero{position:relative;overflow:hidden;padding:27px 30px 25px;margin-bottom:22px;border:1px solid rgba(85,214,232,.23);border-radius:20px;background:linear-gradient(115deg,rgba(15,43,64,.98),rgba(9,25,42,.96) 58%,rgba(19,39,65,.95));box-shadow:0 18px 55px rgba(0,0,0,.2);animation:riseIn .55s ease both}
    .hero:after{content:"";position:absolute;width:280px;height:280px;right:3%;top:-180px;border-radius:50%;border:1px solid rgba(85,214,232,.25);box-shadow:0 0 0 25px rgba(85,214,232,.025),0 0 0 55px rgba(85,214,232,.02)}
    .eyebrow,.section-kicker,.footnote{font-family:'DM Mono',monospace}
    .eyebrow{color:var(--cyan);font-size:11px;letter-spacing:.2em;text-transform:uppercase}
    .hero-title{color:#f2f8fc;font-size:clamp(27px,4vw,43px);font-weight:800;letter-spacing:-.055em;margin:7px 0 5px}
    .hero-sub{color:#a7bdce;font-size:14px;max-width:700px}
    .status-pill{display:inline-flex;align-items:center;gap:8px;border:1px solid rgba(81,211,165,.3);background:rgba(38,158,119,.11);border-radius:999px;padding:7px 11px;color:#8ce5c1;font:500 10px 'DM Mono',monospace;letter-spacing:.08em}
    .status-dot{width:7px;height:7px;border-radius:50%;background:#5de0ad;box-shadow:0 0 0 0 rgba(93,224,173,.65);animation:pulse 1.8s infinite}
    .section-kicker{color:var(--cyan);font-size:10px;letter-spacing:.16em;text-transform:uppercase;margin-bottom:3px}
    .section-title{color:#eaf4fb;font-size:19px;font-weight:750;margin-bottom:10px}
    .footnote{color:#71899d;font-size:11px}
    .stButton>button,.stDownloadButton>button{border:1px solid rgba(85,214,232,.38);background:rgba(31,101,125,.2);color:#dffaff;border-radius:10px;font-weight:700;transition:all .2s}
    .stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--cyan);background:rgba(31,139,163,.28);color:white;transform:translateY(-2px)}
    .stTabs [data-baseweb="tab-list"]{gap:8px;border-bottom:1px solid var(--line)}
    .stTabs [data-baseweb="tab"]{background:rgba(13,27,43,.7);border-radius:9px 9px 0 0;color:#9bb1c3;padding:10px 16px}
    .stTabs [aria-selected="true"]{color:var(--cyan)!important}
    @keyframes riseIn{from{opacity:0;transform:translateY(13px)}to{opacity:1;transform:translateY(0)}}
    @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(93,224,173,.55)}70%{box-shadow:0 0 0 8px rgba(93,224,173,0)}100%{box-shadow:0 0 0 0 rgba(93,224,173,0)}}
    @media(max-width:700px){.block-container{padding-left:1rem;padding-right:1rem}.hero{padding:22px 19px}}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300, show_spinner="Connecting to the seismic data network...")
def load_earthquake_data(secret: str) -> pd.DataFrame:
    headers = {"Authorization": f"Bearer {secret}"}
    rows, offset, expected_total = [], 0, None
    while True:
        response = requests.get(
            WORKER_EXPORT_URL, headers=headers,
            params={"limit": PAGE_SIZE, "offset": offset}, timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(payload.get("message", "Cloudflare export failed."))
        total = int(payload["total_records"])
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise RuntimeError("D1 record count changed during download. Refresh and try again.")
        batch = payload.get("records", [])
        if len(batch) != int(payload.get("returned_records", -1)):
            raise RuntimeError("The API returned an inconsistent record count.")
        rows.extend(batch)
        offset += len(batch)
        if not payload.get("has_more", False):
            break
        if not batch:
            raise RuntimeError("The API stopped before all records were downloaded.")
    if len(rows) != expected_total:
        raise RuntimeError(f"Expected {expected_total} records but received {len(rows)}.")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["event_time"] = pd.to_datetime(df["event_time"], utc=True, errors="coerce")
    for column in ["magnitude", "depth_km", "latitude", "longitude"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if "ingestion_time" in df.columns:
        df["ingestion_time"] = pd.to_datetime(df["ingestion_time"], utc=True, errors="coerce")
    df = df.dropna(subset=["event_time", "latitude", "longitude"])
    df = df[df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)]
    return df.sort_values("event_time", ascending=False).reset_index(drop=True)


def section_heading(kicker: str, title: str):
    st.markdown(
        f'<div class="section-kicker">{kicker}</div><div class="section-title">{title}</div>',
        unsafe_allow_html=True,
    )


def make_3d_globe(data: pd.DataFrame) -> go.Figure:
    # Navigable 3D sphere. Drag to rotate; scroll to zoom.
    u = np.radians(np.arange(0, 361, 6))
    v = np.radians(np.arange(-90, 91, 6))
    uu, vv = np.meshgrid(u, v)
    x, y, z = np.cos(vv) * np.cos(uu), np.cos(vv) * np.sin(uu), np.sin(vv)
    fig = go.Figure()
    fig.add_trace(go.Surface(
        x=x, y=y, z=z, surfacecolor=z,
        colorscale=[[0,"#10263b"],[.48,"#17415c"],[.52,"#1d5670"],[1,"#10263b"]],
        cmin=-1, cmax=1, opacity=.9, showscale=False, hoverinfo="skip",
        lighting=dict(ambient=.72,diffuse=.55,specular=.25,roughness=.85),
        lightposition=dict(x=100,y=150,z=200), name="Earth",
    ))
    for longitude in range(0, 360, 30):
        lon = math.radians(longitude)
        lats = np.radians(np.arange(-90, 91, 3))
        fig.add_trace(go.Scatter3d(
            x=np.cos(lats)*math.cos(lon)*1.003,
            y=np.cos(lats)*math.sin(lon)*1.003,
            z=np.sin(lats)*1.003, mode="lines",
            line=dict(color="rgba(103,190,215,.22)",width=1),
            hoverinfo="skip",showlegend=False,
        ))
    for latitude in range(-60, 90, 30):
        lat = math.radians(latitude)
        lons = np.radians(np.arange(0, 361, 3))
        fig.add_trace(go.Scatter3d(
            x=np.cos(lat)*np.cos(lons)*1.004,
            y=np.cos(lat)*np.sin(lons)*1.004,
            z=np.full(len(lons),math.sin(lat))*1.004, mode="lines",
            line=dict(color="rgba(103,190,215,.20)",width=1),
            hoverinfo="skip",showlegend=False,
        ))
    points = data.dropna(subset=["latitude","longitude"]).copy()
    if len(points) > MAX_GLOBE_POINTS:
        points = points.nlargest(MAX_GLOBE_POINTS,"magnitude")
    lat, lon = np.radians(points["latitude"].to_numpy()), np.radians(points["longitude"].to_numpy())
    depth = points["depth_km"].fillna(0).clip(0,700).to_numpy()
    radius = 1.012 - depth/700*.13
    mags = points["magnitude"].fillna(0).to_numpy()
    fig.add_trace(go.Scatter3d(
        x=radius*np.cos(lat)*np.cos(lon),
        y=radius*np.cos(lat)*np.sin(lon),
        z=radius*np.sin(lat), mode="markers",
        marker=dict(
            size=[max(3,min(10,3+max(float(m),0)*1.1)) for m in mags],
            color=mags,colorscale=[[0,"#54d6e8"],[.45,"#f4bd65"],[1,"#ff5c68"]],
            cmin=0,cmax=max(7,float(max(mags)) if len(mags) else 7),
            opacity=.94,line=dict(color="rgba(255,255,255,.55)",width=.5),
            colorbar=dict(title="Magnitude",tickfont=dict(color="#b9ccda")),
        ),
        customdata=points[["place","magnitude","depth_km","event_time"]].astype(str).to_numpy(),
        hovertemplate="<b>%{customdata[0]}</b><br>Magnitude: %{customdata[1]}<br>Depth: %{customdata[2]} km<br>Time: %{customdata[3]}<extra></extra>",
        name="Earthquake events",
    ))
    fig.update_layout(
        template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0,r=0,t=5,b=0),height=610,showlegend=False,
        scene=dict(
            bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False,range=[-1.35,1.35]),
            yaxis=dict(visible=False,range=[-1.35,1.35]),
            zaxis=dict(visible=False,range=[-1.35,1.35]),
            aspectmode="cube",camera=dict(eye=dict(x=1.65,y=1.65,z=1.05)),
        ),
        transition=dict(duration=450,easing="cubic-in-out"),
    )
    return fig


def make_activity_chart(data: pd.DataFrame) -> go.Figure:
    daily = data.assign(event_date=data["event_time"].dt.date).groupby("event_date").size().reset_index(name="events")
    fig = px.area(daily,x="event_date",y="events",labels={"event_date":"Date (UTC)","events":"Earthquake events"})
    fig.update_traces(line=dict(color="#55d6e8",width=2.5),fillcolor="rgba(85,214,232,.12)",
                      hovertemplate="%{x|%d %b %Y}<br>%{y:,} events<extra></extra>")
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=12,r=12,t=18,b=12),height=320,transition=dict(duration=450),
                      xaxis=dict(showgrid=False,color="#8fa8ba"),
                      yaxis=dict(gridcolor="rgba(143,168,186,.12)",color="#8fa8ba"))
    return fig


def main():
    st.markdown(
        """
        <div class="hero">
          <div class="eyebrow">GLOBAL SEISMIC OBSERVATORY · DATA INTELLIGENCE</div>
          <div class="hero-title">SEISMIC INTELLIGENCE</div>
          <div class="hero-sub">Explore global earthquake activity through interactive geospatial views and analytical signals.</div>
          <div style="margin-top:17px"><span class="status-pill"><span class="status-dot"></span> DATA NETWORK CONNECTED</span></div>
        </div>
        """, unsafe_allow_html=True,
    )
    try:
        secret = st.secrets["CLOUDFLARE_EXPORT_SECRET"]
    except (KeyError, FileNotFoundError):
        st.error("Dashboard configuration is incomplete. Add CLOUDFLARE_EXPORT_SECRET in Streamlit app Secrets.")
        st.info("The secret must match the Cloudflare Worker WAREHOUSE_EXPORT_SECRET.")
        st.stop()
    try:
        df = load_earthquake_data(secret)
    except requests.RequestException as exc:
        st.error(f"Could not connect to the Cloudflare data API: {exc}")
        st.stop()
    except Exception as exc:
        st.error(f"Could not load earthquake data: {exc}")
        st.stop()
    if df.empty:
        st.warning("No earthquake records are currently available.")
        st.stop()

    st.sidebar.markdown("## ◈ CONTROL PANEL")
    st.sidebar.caption("FILTER THE SEISMIC DATASET")
    min_date,max_date = df["event_time"].min().date(),df["event_time"].max().date()
    selected_dates = st.sidebar.date_input("Event date range",value=(min_date,max_date),min_value=min_date,max_value=max_date)
    if isinstance(selected_dates,tuple) and len(selected_dates)==2:
        start_date,end_date = selected_dates
    else:
        start_date=end_date=selected_dates
    mags = df["magnitude"].dropna()
    min_mag=float(mags.min()) if not mags.empty else 0.0
    max_mag=float(mags.max()) if not mags.empty else 10.0
    if min_mag==max_mag: max_mag=min_mag+.1
    magnitude_range=st.sidebar.slider("Magnitude range",min_value=min_mag,max_value=max_mag,value=(min_mag,max_mag),step=.1)
    location_query=st.sidebar.text_input("Location search",placeholder="Japan, Alaska, Chile...")
    st.sidebar.divider()
    if st.sidebar.button("↻  Refresh earthquake data",use_container_width=True):
        load_earthquake_data.clear()
        st.rerun()
    st.sidebar.markdown('<div class="footnote">SOURCE: USGS · STORAGE: CLOUDFLARE D1<br>CACHE WINDOW: 5 MINUTES</div>',unsafe_allow_html=True)

    filtered=df[
        (df["event_time"].dt.date>=start_date)&(df["event_time"].dt.date<=end_date)
        &(df["magnitude"].isna()|df["magnitude"].between(magnitude_range[0],magnitude_range[1]))
    ].copy()
    if location_query.strip():
        filtered=filtered[filtered["place"].fillna("").str.contains(location_query.strip(),case=False,regex=False)]
    known=filtered["magnitude"].dropna()
    total=len(filtered)
    avg=float(known.mean()) if not known.empty else 0
    maximum=float(known.max()) if not known.empty else 0
    latest=filtered["event_time"].max() if total else None
    ingested=df["ingestion_time"].max() if "ingestion_time" in df.columns and df["ingestion_time"].notna().any() else None

    section_heading("LIVE DATA SNAPSHOT","Global seismic overview")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("EARTHQUAKE EVENTS",f"{total:,}")
    c2.metric("AVERAGE MAGNITUDE",f"{avg:.2f}")
    c3.metric("MAXIMUM MAGNITUDE",f"{maximum:.1f}")
    c4.metric("LATEST EVENT · UTC",latest.strftime("%d %b %H:%M") if latest is not None else "—")
    st.caption(f"Showing {total:,} of {len(df):,} stored events · "+(f"Latest ingestion: {ingested.strftime('%d %b %Y %H:%M UTC')}" if ingested is not None else "Ingestion timestamp unavailable"))

    st.divider()
    section_heading("GEOSPATIAL EXPLORATION","Earthquake activity around the planet")
    globe_tab,map_tab=st.tabs(["◉  3D EARTH GLOBE","◎  GLOBAL EVENT MAP"])
    with globe_tab:
        st.caption("Drag to rotate · Scroll to zoom · Hover over an event for details")
        if not filtered.empty:
            st.plotly_chart(make_3d_globe(filtered),use_container_width=True,config={"displayModeBar":True,"scrollZoom":True})
            st.caption("Markers use actual earthquake coordinates. Colour represents magnitude; position relative to the globe approximates depth.")
        else: st.info("No events match the selected filters.")
    with map_tab:
        map_data=filtered.dropna(subset=["latitude","longitude"]).copy()
        if not map_data.empty:
            map_data["map_size"]=map_data["magnitude"].fillna(0).clip(.1,7)
            map_data=map_data.nlargest(3000,"map_size")
            # Use Plotly's built-in Natural Earth geography rather than external map tiles.
            # This guarantees visible continents, country borders and island coastlines.
            map_fig=px.scatter_geo(
                map_data,lat="latitude",lon="longitude",color="magnitude",size="map_size",
                hover_name="place",
                hover_data={"event_time":True,"depth_km":True,"event_id":True,
                            "latitude":":.3f","longitude":":.3f","map_size":False},
                color_continuous_scale=["#55d6e8","#f4bd65","#ff5c68"],
                projection="natural earth",height=570,
            )
            map_fig.update_geos(
                showland=True,landcolor="#183247",
                showocean=True,oceancolor="#071725",
                showcountries=True,countrycolor="rgba(137,180,205,.48)",
                showcoastlines=True,coastlinecolor="#65a9c2",
                showlakes=True,lakecolor="#0b2031",
                showrivers=False,
                bgcolor="rgba(0,0,0,0)",
                showframe=False,
                lataxis_showgrid=True,lataxis_gridcolor="rgba(122,166,190,.12)",
                lonaxis_showgrid=True,lonaxis_gridcolor="rgba(122,166,190,.12)",
            )
            map_fig.update_layout(
                template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=0,r=0,t=0,b=0),
                coloraxis_colorbar=dict(title="Magnitude",tickfont=dict(color="#b9ccda")),
            )
            st.plotly_chart(map_fig,use_container_width=True)
            st.caption("Map displays up to 3,000 filtered events, prioritising larger magnitudes.")
        else: st.info("No locations match the selected filters.")

    st.divider()
    section_heading("ANALYTICS","Patterns and magnitude signals")
    left,right=st.columns(2)
    with left:
        st.markdown("**Daily earthquake activity**")
        if not filtered.empty: st.plotly_chart(make_activity_chart(filtered),use_container_width=True)
        else: st.info("No events match the selected filters.")
    with right:
        st.markdown("**Magnitude distribution**")
        if not known.empty:
            hist=px.histogram(filtered.dropna(subset=["magnitude"]),x="magnitude",nbins=28,
                              labels={"magnitude":"Magnitude","count":"Events"},color_discrete_sequence=["#55d6e8"])
            hist.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                               margin=dict(l=12,r=12,t=18,b=12),height=320,transition=dict(duration=450),
                               xaxis=dict(showgrid=False,color="#8fa8ba"),yaxis=dict(gridcolor="rgba(143,168,186,.12)",color="#8fa8ba"))
            hist.update_traces(marker_line_color="#a7f0f5",marker_line_width=.6)
            st.plotly_chart(hist,use_container_width=True)
        else: st.info("No magnitude values are available for these filters.")

    st.divider()
    section_heading("EVENT INTELLIGENCE","Recent earthquake records")
    columns=["event_time","magnitude","place","depth_km","latitude","longitude","event_url"]
    recent=filtered[columns].head(100).copy()
    recent["event_time"]=recent["event_time"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    st.dataframe(recent,use_container_width=True,hide_index=True,column_config={
        "event_time":st.column_config.TextColumn("Event time"),
        "event_url":st.column_config.LinkColumn("USGS event"),
        "magnitude":st.column_config.NumberColumn("Magnitude",format="%.1f"),
        "depth_km":st.column_config.NumberColumn("Depth (km)",format="%.2f"),
        "latitude":st.column_config.NumberColumn("Latitude",format="%.4f"),
        "longitude":st.column_config.NumberColumn("Longitude",format="%.4f"),
    })
    st.download_button("↓  Export filtered records as CSV",data=filtered.to_csv(index=False).encode("utf-8"),
                       file_name="earthquake_events_filtered.csv",mime="text/csv")
    st.markdown(
        '<div style="margin-top:34px;padding-top:16px;border-top:1px solid rgba(133,178,211,.16)">'
        '<div class="footnote">SEISMIC INTELLIGENCE · DATA SOURCE: USGS EARTHQUAKE API · READ-ONLY DATA ACCESS: CLOUDFLARE WORKER / D1</div>'
        '<div style="color:#71899d;font-size:11px;margin-top:6px">Built for earthquake data exploration and cloud data engineering. BigQuery is maintained separately as the analytical warehouse.</div></div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
