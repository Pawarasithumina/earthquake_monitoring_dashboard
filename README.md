# Earthquake Monitoring Dashboard

An interactive Streamlit dashboard for exploring earthquake events collected from the USGS Earthquake API.

## Architecture

- **USGS Earthquake API** — public earthquake event source.
- **Cloudflare Worker** — cloud-side ingestion and protected read-only data API.
- **Cloudflare D1** — structured earthquake records.
- **Google BigQuery** — analytical warehouse populated by GitHub Actions.
- **Streamlit Community Cloud** — dashboard hosting.

The dashboard reads records from the Cloudflare Worker `/api/warehouse-export` endpoint. It does not run extraction or data processing on a local machine.

## Features

- Event count, average magnitude, maximum magnitude and latest event metrics
- Date, magnitude and location filters
- Daily earthquake activity chart
- Magnitude distribution
- Interactive event map
- Recent event table with USGS links
- CSV download of filtered records

## Run on Streamlit Community Cloud

1. Deploy this repository using [Streamlit Community Cloud](https://share.streamlit.io/).
2. Set the app's main file to `app.py`.
3. In the app's **Settings → Secrets**, add:

```toml
CLOUDFLARE_EXPORT_SECRET = "your_worker_export_secret"
```

Use the same value configured as the Cloudflare Worker secret `WAREHOUSE_EXPORT_SECRET`. Never commit the secret to this repository.

## Data endpoint

The dashboard uses the protected endpoint:

`https://earthquake-monitoring-system.pawarasithumina24.workers.dev/api/warehouse-export`

The endpoint is read-only and paginated. The dashboard caches retrieved records for five minutes.

## Local development

Install dependencies with `pip install -r requirements.txt` and configure the secret using Streamlit's local secrets file. Local development is for interface testing only; the production ingestion and data processing pipeline runs in the cloud.

## Data source

[USGS Earthquake Hazards Program](https://earthquake.usgs.gov/fdsnws/event/1/)
