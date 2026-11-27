import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

WORKER_EXPORT_URL = (
    "https://earthquake-monitoring-system."
    "pawarasithumina24.workers.dev/api/warehouse-export"
)
PAGE_SIZE = 1000

st.set_page_config(
    page_title="Earthquake Monitoring Dashboard",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=300, show_spinner="Loading earthquake records from Cloudflare D1...")
def load_earthquake_data(secret: str) -> pd.DataFrame:
    headers = {"Authorization": f"Bearer {secret}"}
    rows = []
    offset = 0
    expected_total = None

    while True:
        response = requests.get(
            WORKER_EXPORT_URL,
            headers=headers,
            params={"limit": PAGE_SIZE, "offset": offset},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("status") != "success":
            raise RuntimeError(payload.get("message", "Cloudflare export failed."))

        total = int(payload["total_records"])
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise RuntimeError(
                "The D1 record count changed during download. Please refresh and try again."
            )

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
        raise RuntimeError(
            f"Expected {expected_total} records but received {len(rows)}."
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["event_time"] = pd.to_datetime(df["event_time"], utc=True, errors="coerce")
    df["magnitude"] = pd.to_numeric(df["magnitude"], errors="coerce")
    df["depth_km"] = pd.to_numeric(df["depth_km"], errors="coerce")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["event_time", "latitude", "longitude"])
    df = df[
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
    ]
    return df.sort_values("event_time", ascending=False).reset_index(drop=True)


def main():
    st.title("🌍 Earthquake Monitoring Dashboard")
    st.caption(
        "Near-real-time earthquake event exploration powered by USGS data, "
        "Cloudflare D1 and a BigQuery analytical warehouse."
    )

    try:
        secret = st.secrets["CLOUDFLARE_EXPORT_SECRET"]
    except (KeyError, FileNotFoundError):
        st.error(
            "Dashboard configuration is incomplete. Add "
            "`CLOUDFLARE_EXPORT_SECRET` in the Streamlit app's Secrets settings."
        )
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

    min_date = df["event_time"].min().date()
    max_date = df["event_time"].max().date()

    st.sidebar.header("Filters")
    selected_dates = st.sidebar.date_input(
        "Event date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    else:
        start_date = end_date = selected_dates

    magnitude_values = df["magnitude"].dropna()
    if magnitude_values.empty:
        min_mag, max_mag = 0.0, 10.0
    else:
        min_mag = float(magnitude_values.min())
        max_mag = float(magnitude_values.max())

    if min_mag == max_mag:
        max_mag = min_mag + 0.1

    magnitude_range = st.sidebar.slider(
        "Magnitude range",
        min_value=float(min_mag),
        max_value=float(max_mag),
        value=(float(min_mag), float(max_mag)),
        step=0.1,
    )

    location_query = st.sidebar.text_input(
        "Search location",
        placeholder="e.g. Japan, Alaska, Chile",
    )

    filtered = df[
        (df["event_time"].dt.date >= start_date)
        & (df["event_time"].dt.date <= end_date)
        & (
            df["magnitude"].isna()
            | df["magnitude"].between(
                magnitude_range[0], magnitude_range[1]
            )
        )
    ].copy()

    if location_query.strip():
        filtered = filtered[
            filtered["place"].fillna("").str.contains(
                location_query.strip(), case=False, regex=False
            )
        ]

    st.sidebar.caption(f"Showing {len(filtered):,} of {len(df):,} records.")
    if st.sidebar.button("Refresh data"):
        load_earthquake_data.clear()
        st.rerun()

    known_magnitudes = filtered["magnitude"].dropna()
    total_events = len(filtered)
    average_magnitude = (
        float(known_magnitudes.mean()) if not known_magnitudes.empty else 0
    )
    maximum_magnitude = (
        float(known_magnitudes.max()) if not known_magnitudes.empty else 0
    )
    latest_event = filtered["event_time"].max() if total_events else None

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Earthquake events", f"{total_events:,}")
    col2.metric("Average magnitude", f"{average_magnitude:.2f}")
    col3.metric("Maximum magnitude", f"{maximum_magnitude:.1f}")
    col4.metric(
        "Latest event (UTC)",
        latest_event.strftime("%d %b %Y %H:%M") if latest_event is not None else "—",
    )

    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("Earthquake activity over time")
        if not filtered.empty:
            daily = (
                filtered.assign(event_date=filtered["event_time"].dt.date)
                .groupby("event_date")
                .size()
                .reset_index(name="events")
            )
            fig = px.line(
                daily,
                x="event_date",
                y="events",
                markers=True,
                labels={"event_date": "Date (UTC)", "events": "Number of events"},
            )
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No events match the selected filters.")

    with right:
        st.subheader("Magnitude distribution")
        if not known_magnitudes.empty:
            fig = px.histogram(
                filtered.dropna(subset=["magnitude"]),
                x="magnitude",
                nbins=25,
                labels={"magnitude": "Magnitude", "count": "Number of events"},
            )
            fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No magnitude values are available for these filters.")

    st.subheader("Earthquake locations")
    map_data = filtered.dropna(subset=["latitude", "longitude"]).copy()
    if not map_data.empty:
        map_data["map_size"] = (
            map_data["magnitude"].fillna(0).clip(lower=0.1).clip(upper=7)
        )
        map_data = map_data.nlargest(3000, "map_size")
        map_fig = px.scatter_map(
            map_data,
            lat="latitude",
            lon="longitude",
            color="magnitude",
            size="map_size",
            hover_name="place",
            hover_data={
                "event_time": True,
                "depth_km": True,
                "event_id": True,
                "latitude": False,
                "longitude": False,
                "map_size": False,
            },
            color_continuous_scale="YlOrRd",
            zoom=0,
            height=520,
            map_style="open-street-map",
        )
        map_fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(map_fig, use_container_width=True)
        st.caption("Map displays up to 3,000 filtered events, prioritising larger magnitudes.")
    else:
        st.info("No locations match the selected filters.")

    st.subheader("Recent earthquake events")
    display_columns = [
        "event_time",
        "magnitude",
        "place",
        "depth_km",
        "latitude",
        "longitude",
        "event_url",
    ]
    recent = filtered[display_columns].head(100).copy()
    recent["event_time"] = recent["event_time"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    st.dataframe(
        recent,
        use_container_width=True,
        hide_index=True,
        column_config={
            "event_url": st.column_config.LinkColumn("USGS event"),
            "magnitude": st.column_config.NumberColumn("Magnitude", format="%.1f"),
            "depth_km": st.column_config.NumberColumn("Depth (km)", format="%.2f"),
        },
    )

    csv_data = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered records as CSV",
        data=csv_data,
        file_name="earthquake_events_filtered.csv",
        mime="text/csv",
    )

    st.caption(
        "Data source: USGS Earthquake API. Dashboard data is read from Cloudflare D1 "
        "through a protected, read-only Worker endpoint. BigQuery is maintained "
        "separately as the analytical warehouse."
    )


if __name__ == "__main__":
    main()
