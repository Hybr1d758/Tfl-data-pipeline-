# TfL Data Pipeline

## Overview
Data engineering playground for Transport for London arrivals data. The goal is to automate extraction from the TfL Unified API, transform the payload into curated tables, and load it into a warehouse-ready store (Postgres).

## Repository Structure
- `etl/` – Python modules for extract/transform/load steps
- `tests/` – pytest coverage for ETL logic and fixtures for sample API payloads
- `infra/` – Docker configuration to spin up local dependencies such as Postgres
- `docs/` – Architecture diagram and schema notes for downstream consumption
- `.env.example` – Template for environment variables (TfL API keys, DB credentials)
- `requirements.txt` – Python dependencies pinned for reproducibility

## Local Setup
1. Clone the repository and switch into the project folder.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies and keep `pip` up to date:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Populate a `.env` using `.env.example` as a guide. Export `TFL_APP_ID`, `TFL_APP_KEY`, and Postgres connection details before running scripts.

## Development Workflow
```bash
# activate environment
source .venv/bin/activate

# run extraction module (example stop point)
python -m etl.extract_tfl --stop-point 2420900042

# run tests
pytest -q

# commit & push
git add <files>
git commit -m "feat: describe change"
git push
```

## Challenges & Resolutions (running log)
- **Credential handling**: Initial extractor embedded credentials in the URL and reused a single key. We refactored to source `app_id`/`app_key` from environment variables and pass them securely via query parameters.
- **Network reliability**: Original API calls had no retries and minimal error handling. We introduced a shared `requests.Session` with retry/backoff, explicit logging, and JSON validation to make extraction resilient.
- **Environment isolation**: To prevent dependency drift, we standardized on a `.venv` virtual environment with dependencies pinned in `requirements.txt`, and ensured the virtual environment stays out of git.

## Roadmap
- Enrich arrivals with metadata (routes, lines, station info) before loading.
- Harden data validation in `transform_clean.py` with schema tests.
- Implement automated CI checks (lint, tests) prior to deployment.
- Expand Docker Compose setup to include analytics notebooks for ad hoc exploration.

## License
Distributed under the terms of the `LICENSE` file.