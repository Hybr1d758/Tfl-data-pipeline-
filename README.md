# TfL Data Pipeline

<<<<<<< HEAD
A real-time data engineering playground that extracts Transport for London (TfL) arrivals, enriches them with contextual metadata, and stages analytics-ready datasets for DuckDB/Postgres.

## Highlights
- Built resilient ingestion against TfL’s Unified API with retries, JSON validation, and credential hygiene.
- Automated enrichment marries arrivals with line and stop metadata, then normalises the payload for downstream stores.
- Schema-focused pytest suite guards transformations while GitHub-ready CLI tooling accelerates local iteration.

## My Role
- Designed the arrivals enrichment layer (`etl/enrich_arrivals.py`) including in-memory stop point caching to reduce API chatter.
- Authored the cleaning pipeline (`etl/transform_clean.py`) with column normalisation, type coercion, deduplication, and validation heuristics.
- Embedded schema regression tests and documentation so the project is CI-ready and easy to onboard.

## Tech Stack
| Domain        | Tools & Libraries                                     |
|---------------|--------------------------------------------------------|
| Language      | Python 3.11                                            |
| Data & ETL    | pandas, requests, boto3, DuckDB                        |
| Testing       | pytest                                                 |
| Cloud/Infra   | AWS S3 (staging), Docker (infra/), GitHub Actions-ready|
| Tooling       | Virtualenv, gzip, CLI utilities                        |
=======
## Overview
Data engineering playground for Transport for London arrivals data. The goal is to automate extraction from the TfL Unified API, transform the payload into curated tables, and load it into a warehouse-ready store (Postgres).
<img width="1536" height="1024" alt="ChatGPT Image Oct 10, 2025 at 12_25_55 AM" src="https://github.com/user-attachments/assets/0a136f18-6e75-45bc-9845-44bc90b8e3f0" />

>>>>>>> cb185cf6e71b4cbf2b6bdbc87f20f19687b9f22d

## Repository Structure
- `etl/` – Python modules for extract/transform/load steps
  - `extract_tfl.py` – Core API clients and HTTP session utilities
  - `enrich_arrivals.py` – Decorates arrivals with line & stop metadata (cached lookups)
  - `transform_clean.py` – Cleans/validates arrivals and exposes a CLI
  - `pipeline.py` – Orchestrates extraction → enrichment → cleaning in one command
- `tests/` – pytest coverage for ETL logic and schema fixtures
- `infra/` – Docker configuration for Postgres and supporting services
- `docs/` – Diagrams and architecture notes for stakeholders
- `.env.example` – Bootstrap template for required credentials
- `requirements.txt` – Pinned Python dependencies for reproducibility

## Quick Start
### 1. Prerequisites
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env  # fill in TfL + AWS credentials
```

### 2. Run the pipeline
```bash
# pull arrivals for a stop point (requires TFL_APP_ID/TFL_APP_KEY)
python -m etl.pipeline 940GZZLUEBY --line-modes tube --line-service-types Regular

# inspect the enriched JSON / cleaned CSV outputs (flags optional)
python -m etl.pipeline 940GZZLUEBY \
  --output-json data/enriched.json \
  --output data/arrivals-clean.csv
```

### 3. Explore enrichment & cleaning modules directly
```bash
# standalone extraction (raw API payload)
python -m etl.extract_tfl --stop-point 2420900042

# run cleaning pipeline against a local payload
python -m etl.transform_clean --input data/arrivals.json --output data/arrivals-clean.csv
```

### 4. Tests
```bash
pytest -q                          # full suite
pytest tests/test_transform_clean.py -q  # schema-focused checks
pytest tests/test_orchestrator.py -q     # orchestration checks
```

### 5. Batch orchestration
```bash
# run multiple stops via CLI (outputs saved under data/arrivals/)
python -m etl.orchestrator \
  --stop-point 940GZZLUEBY \
  --stop-point 940GZZLUSTN \
  --output-dir data/arrivals \
  --line-modes tube
```

### 6. Docker (optional)
```bash
# build image
docker build -t tfl-data-pipeline:latest .

# run the default pipeline command inside the container
docker run --rm \
  -e TFL_APP_ID=your-app-id \
  -e TFL_APP_KEY=your-app-key \
  tfl-data-pipeline:latest

# override the command to run batch orchestration instead
docker run --rm \
  -e TFL_APP_ID=your-app-id \
  -e TFL_APP_KEY=your-app-key \
  tfl-data-pipeline:latest \
  python -m etl.orchestrator --stop-point 940GZZLUEBY --output-dir /tmp/arrivals

# docker compose (runs orchestrator and writes to ./data)
docker compose up --build
```

## Testing & Quality
- Schema tests cover column renames, type coercion, missing timestamps, mixed modes, and validation failures.
- `enrich_arrivals_with_metadata` caches stop point lookups to avoid redundant API calls when processing large batches.
- Pipelines exit gracefully when credentials are missing, making CI runs predictable.
- GitHub Actions workflow (`.github/workflows/ci.yml`) provisions Python 3.11, installs dependencies, and runs `pytest -q` on push/PR.
- Orchestrator CLI (`etl/orchestrator.py`) batches multiple stops, persists outputs, and is covered by unit tests.

## Artefacts & Exploration
- Use `etl/upload_tfl.py` to gzip and stage route metadata snapshots in S3 for DuckDB analytics.
- Architecture diagrams and schema notes live under `docs/` for quick onboarding conversations.

## Roadmap
- [x] Enrich arrivals with line & station metadata before loading.
- [x] Harden data validation with schema tests and fixtures.
- [ ] Implement CI workflow (GitHub Actions) for linting/tests.
- [ ] Extend Docker Compose with analytics notebooks for ad-hoc exploration.

<<<<<<< HEAD
## Lessons Learned
- Credential management, retry/backoff, and JSON validation are mandatory when dealing with public transit APIs.
- High-volume responses benefit from client-side filtering plus cached metadata lookups to stay performant.
- Schema-focused tests provide fast feedback when iterating on transformations.

## Contact
Interested in data engineering conversations or potential collaborations? Reach out via LinkedIn or email (add your preferred contact) – I’m happy to discuss scaling this pipeline or tailoring it for production analytics.
=======
## License
Distributed under the terms of the `LICENSE` file.
>>>>>>> cb185cf6e71b4cbf2b6bdbc87f20f19687b9f22d
