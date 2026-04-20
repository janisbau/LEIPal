# LEIPal — Project Memory

## What This Is
A web platform for LEI (Legal Entity Identifier) analytics aimed at two audiences:
1. **General public** — market stats, growth trends, jurisdiction breakdowns
2. **The owner (an LOU)** — competitor analysis against other LOUs

Target features (from the original brief):
- Daily LEI statistics & growth trends with graphs
- LOU statistics for competitor analysis
- Market predictions
- Company profiles
- Public info pages

The user **is an LOU themselves** — LOU-level competitor analysis is a high-priority feature.

---

## Tech Stack
| Layer | Choice | Notes |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Running on port 8000 |
| Frontend | Next.js (React) | Phase 2 — not started yet |
| Database | PostgreSQL 16 (Docker) | Port 5432 locally |
| Data processing | Polars | Fast streaming XML parser |
| DB migrations | Alembic | |
| Package manager | Poetry | Run all commands with `poetry run …` |
| Hosting | Local → AWS later | RDS-compatible schema |

---

## Data Sources
### GLEIF Golden Copy (primary)
- **Full files**: `GET https://leidata.gleif.org/api/v1/concatenated-files/lei2`
  - Returns JSON list; each entry has `id`, `content_date`, `file` (ZIP download URL), `filesize`, `record_count`
  - ZIP contains one XML file in LEI-CDF v3.1 format
  - ~500 MB compressed, ~3.2M records, takes ~10 min to parse + load

- **Delta files**: `GET https://goldencopy.gleif.org/api/v2/golden-copies/publishes/lei2/latest.xml?delta=<type>`
  - Follows a 302 redirect to the actual file
  - Filename from resolved URL includes timestamp — used as watermark key
  - Delta types: `IntraDay` (8h), `LastDay` (24h), `LastWeek` (7d — **our default**), `LastMonth` (31d)
  - ~1-15 MB, applies in seconds

### Future data sources
- GLEIF Level 2 data (ownership/relationship chains)
- GLEIF website scraping for additional public info

---

## Key Decisions Made
- **Full load strategy**: Download full file once, then apply weekly deltas. Don't re-download full file.
- **Default delta**: `LastWeek` — safe if computer isn't opened daily. Override with `--delta-type`.
- **Delta tracking**: `pipeline_watermark` table records every applied file by name — prevents double-applying.
- **LOU table**: Synthesised from `lei_records.managing_lou` — GLEIF doesn't publish a separate LOU list in Level 1. Each LOU also has its own LEI record containing name/jurisdiction.
- **Bulk loading**: PostgreSQL `COPY` via staging table for full load (deduplicates source data with `DISTINCT ON`). Deltas use batched `ON CONFLICT DO UPDATE` upsert.
- **Duplicate LEIs**: GLEIF source data contains duplicate LEI codes — handled via staging table + `DISTINCT ON (lei) ORDER BY last_update_date DESC`.
- **Docker for local Postgres**: pgAdmin at http://localhost:5050 (admin@leipal.local / admin).

---

## Database Schema

### `lei_records` — one row per LEI (3,163,412 rows loaded)
```
lei                        TEXT  PRIMARY KEY
legal_name                 TEXT
jurisdiction               TEXT   -- e.g. "GB", "US-DE"
entity_status              TEXT   -- ACTIVE (2.9M), INACTIVE (227k), NULL (8.5k)
entity_category            TEXT   -- GENERAL, BRANCH, FUND, etc.
managing_lou               TEXT   -- LEI of the LOU that manages this record
registration_status        TEXT   -- ISSUED, LAPSED, PENDING_TRANSFER, etc.
initial_registration_date  DATE
last_update_date           DATE
next_renewal_date          DATE
created_at                 TIMESTAMP
updated_at                 TIMESTAMP
```
Indexes: `managing_lou`, `jurisdiction`, `entity_status`, `initial_registration_date`

### `lous` — synthesised LOU table (40 LOUs)
```
lou_lei   TEXT  PRIMARY KEY   -- LEI of the LOU
lou_name  TEXT
country   TEXT
website   TEXT
status    TEXT
```
Refreshed automatically after every full load or delta apply.

### `pipeline_watermark` — tracks applied files
```
id            SERIAL  PRIMARY KEY
file_name     TEXT    UNIQUE      -- e.g. "20260420-1600-gleif-goldencopy-lei2-last-week.xml.zip"
applied_at    TIMESTAMP
record_count  INTEGER
```

---

## Known Data Facts
- Top jurisdictions: IN (330k), IT (241k), DE (239k), GB (218k), ES (183k), NL (183k), FR (172k), US-DE (132k), SE (112k), CN (107k)
- 40 LOUs globally
- 92% of LEIs are ACTIVE

---

## Project Structure
```
LEIPal/
├── CLAUDE.md                        ← this file
├── README.md                        ← setup instructions
├── docker-compose.yml               ← PostgreSQL 16 + pgAdmin
├── .env.example                     ← copy to .env before first run
├── .gitignore                       ← excludes data/, .env, .claude/settings.local.json
└── backend/
    ├── pyproject.toml               ← Poetry deps (FastAPI, Polars, psycopg3, Alembic, httpx, tqdm)
    ├── alembic.ini
    ├── alembic/
    │   └── versions/0001_initial_schema.py
    └── app/
        ├── main.py                  ← FastAPI app, mounts routers
        ├── config.py                ← Settings loaded from .env
        ├── database.py              ← SQLAlchemy engine + SessionLocal
        ├── models.py                ← ORM: LeiRecord, Lou, PipelineWatermark
        ├── api/v1/
        │   └── stats.py             ← GET /api/v1/stats/summary
        └── pipeline/
            ├── download.py          ← Downloads full + delta ZIPs from GLEIF
            ├── parse.py             ← Streaming XML parser (iterparse, namespace auto-detect)
            └── load.py              ← COPY full load + batched upsert for deltas
```

---

## Current Status
### ✅ Phase 1: Full Data Pipeline — COMPLETE
- PostgreSQL running in Docker
- 3,163,412 LEIs loaded from GLEIF golden copy XML
- Delta updates working (LastWeek default, ~7k records, seconds to apply)
- Verification endpoint: `GET /api/v1/stats/summary`
- All committed to GitHub: https://github.com/janisbau/LEIPal

### 🔜 Phase 2: Frontend Dashboard — NEXT
Stack: Next.js (React) in `frontend/` directory

**Planned pages/views:**
1. **Overview dashboard** — total LEIs, active/inactive split, growth chart over time, top jurisdictions
2. **LOU explorer** — table of all 40 LOUs with key stats (total LEIs managed, active %, country)
3. **LOU detail** — competitor deep-dive: registrations over time, jurisdiction breakdown, renewal rate
4. **Jurisdiction view** — drill into a country/region

**API endpoints needed before/during frontend build:**
- `GET /api/v1/lous` — list all LOUs with stats
- `GET /api/v1/lous/{lei}` — single LOU detail
- `GET /api/v1/stats/growth` — LEI counts over time (by month/year)
- `GET /api/v1/stats/jurisdictions` — full jurisdiction breakdown

### Phase 3: Advanced Features (future)
- Level 2 data (ownership chains)
- Market predictions
- Company profile pages
- Automated delta scheduling (AWS EventBridge or cron)
- AWS deployment (EC2 + RDS + S3)

---

## Open Questions (to resolve early in Phase 2)
1. **Which LOU are you?** — provide your LEI so we can build a "you vs. competitors" view
2. **What competitor metrics matter most?** — new registrations/month, market share by jurisdiction, renewal rate, lapsed LEI %?
3. **Public or private site?** — affects auth, SEO, hosting decisions
4. **Branding** — any design preferences for the frontend?

---

## How to Start the Project (after relaunch)

```powershell
# 1. Start the database
cd C:\Users\jbauv\LEIPal
docker-compose up -d

# 2. Start the API (in a separate terminal)
cd C:\Users\jbauv\LEIPal\backend
poetry run uvicorn app.main:app --reload

# 3. Verify data is there
# Open: http://localhost:8000/api/v1/stats/summary
# Should show 3.16M LEIs, 40 LOUs

# 4. Apply weekly delta update (run once a week or so)
poetry run python -m app.pipeline.download --mode delta
poetry run python -m app.pipeline.load --mode delta --file .\data\deltas\<filename>.zip
```

**pgAdmin** (DB browser): http://localhost:5050 — login: `admin@leipal.local` / `admin`
**FastAPI docs**: http://localhost:8000/docs
