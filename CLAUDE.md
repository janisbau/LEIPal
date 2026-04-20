# LEIPal — Project Memory

## What This Is
A web platform for LEI (Legal Entity Identifier) analytics. Target features:
- Daily LEI statistics & trends with graphs
- LOU (Local Operating Unit) statistics for competitor analysis
- Market predictions, company profiles, public info

The user **is an LOU themselves** — so LOU-level competitor analysis is a priority feature.

## Tech Stack
| Layer | Choice |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Frontend | Next.js (React) — Phase 2, not started yet |
| Database | PostgreSQL 16 (Docker) |
| Data processing | Polars (fast CSV parsing for 10M+ rows) |
| DB migrations | Alembic |
| Package manager | Poetry |
| Hosting | Local for now → AWS later (RDS-compatible setup) |

## Data Sources
- **Primary**: GLEIF Golden Copy — full LEI dataset, updated 3× per day
  - API base: `https://leidata.gleif.org/api/v1`
  - Full file list: `GET /concatenated-files/lei2`
  - Delta file list: `GET /concatenated-files/lei2delta`
  - Each entry has: `id`, `content_date`, `file` (download URL), `filesize`, `record_count`
  - Files are ZIP archives containing a single **XML** file (LEI-CDF v3.1 format)
  - XML namespace: `{http://www.gleif.org/data/schema/leidata/2016}` (auto-detected)
  - Alternative CSV endpoint: `https://goldencopy.gleif.org/api/v2/golden-copies/publishes/lei2/YYYYMMDD-0000.csv` (redirects via 302)
- **Future**: GLEIF website scraping for additional public info
- **Future**: Level 2 data (ownership/relationship chains) — not in Phase 1

## Key Decisions Made
- **Full load strategy**: Download once, then apply delta files for updates. Don't re-download full file daily.
- **Delta tracking**: `pipeline_watermark` table records every applied file by name — prevents double-applying.
- **LOU table**: Synthesised from `lei_records.managing_lou` — GLEIF doesn't publish a separate LOU list in Level 1. LOU's own LEI record contains its name/jurisdiction.
- **Bulk loading**: PostgreSQL `COPY` command for initial full load (much faster than INSERT). Delta files use `ON CONFLICT DO UPDATE` upsert.
- **No scheduled automation yet**: Delta runs are manual for now (`python -m app.pipeline.download --mode delta` + load). Will automate in a later phase.
- **Docker for local Postgres**: pgAdmin included at http://localhost:5050 (admin@leipal.local / admin).

## Database Schema
### `lei_records` — one row per LEI
- `lei` (PK), `legal_name`, `jurisdiction`, `entity_status`, `entity_category`
- `managing_lou`, `registration_status`
- `initial_registration_date`, `last_update_date`, `next_renewal_date`
- `created_at`, `updated_at`
- Indexes on: `managing_lou`, `jurisdiction`, `entity_status`, `initial_registration_date`

### `lous` — synthesised LOU table
- `lou_lei` (PK), `lou_name`, `country`, `website`, `status`
- Populated/refreshed after every full load or delta apply

### `pipeline_watermark` — tracks applied files
- `file_name` (unique), `applied_at`, `record_count`

## Project Structure
```
LEIPal/
├── CLAUDE.md                  ← this file
├── README.md                  ← setup instructions
├── docker-compose.yml         ← PostgreSQL + pgAdmin
├── .env.example               ← copy to .env
└── backend/
    ├── pyproject.toml         ← Poetry deps
    ├── alembic.ini
    ├── alembic/versions/0001_initial_schema.py
    └── app/
        ├── main.py            ← FastAPI entry point
        ├── config.py          ← Settings from .env
        ├── database.py        ← SQLAlchemy session
        ├── models.py          ← ORM models
        ├── api/v1/stats.py    ← GET /api/v1/stats/summary
        └── pipeline/
            ├── download.py    ← GLEIF downloader
            ├── parse.py       ← Polars CSV parser
            └── load.py        ← Bulk loader + delta upsert
```

## Current Status
### Phase 1: Data Pipeline ✅ COMPLETE
- [x] Project scaffolded
- [x] Docker + PostgreSQL running
- [x] DB migrations applied
- [x] Download script working (fixed GLEIF API response structure)
- [x] Full golden copy downloaded → `data/full/lei2_full_40438.zip` (contains `20260302-gleif-concatenated-file-lei2.xml`)
- [x] Parser rewritten for streaming XML (iterparse, auto-detects namespace, no RAM spike)
- [x] Loaded into PostgreSQL — 3,163,412 LEIs, 40 LOUs, ~8 min parse + ~2 min load
- [x] Verified via GET /api/v1/stats/summary

**Known data quirks:**
- GLEIF source data contains duplicate LEI codes → handled via staging table + DISTINCT ON
- 8,537 records have NULL entity_status
- Top jurisdictions: IN, IT, DE, GB, ES, NL, FR, US-DE, SE, CN

### Phase 2: Frontend Dashboard (not started)
- Next.js app in `frontend/`
- Charts for total LEIs, growth over time, breakdown by jurisdiction/LOU
- LOU competitor view

### Phase 3: Advanced Features (not started)
- Level 2 data (ownership chains)
- Market predictions
- Company profile pages
- Automated delta scheduling

## Open Questions for Later
1. **Which LOU are you?** — needed to build a "you vs. competitors" targeted view
2. **What competitor metrics matter most?** — e.g. new registrations/month, market share by jurisdiction, renewal rate
3. **Public or private site?** — affects auth, SEO, and hosting decisions
4. **AWS deployment** — when ready, likely EC2 + RDS PostgreSQL + S3 for raw files

## Running the Project
```powershell
# Start DB
docker-compose up -d

# Backend (from /backend)
poetry run uvicorn app.main:app --reload

# Download latest full file
poetry run python -m app.pipeline.download --mode full

# Load into DB
poetry run python -m app.pipeline.load --mode full --file ./data/full/<file>.zip

# Apply deltas
poetry run python -m app.pipeline.download --mode delta
poetry run python -m app.pipeline.load --mode delta --file ./data/deltas/<file>.zip

# Check data
curl http://localhost:8000/api/v1/stats/summary
```
