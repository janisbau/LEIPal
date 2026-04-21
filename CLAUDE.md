# LEIPal — Project Memory

## What This Is
A **neutral commercial market intelligence platform** for the LEI ecosystem — think Bloomberg Terminal for LEI data. Not tied to any single LOU's perspective.

**Business model**: SaaS product. Some data free/public, deep analytics behind a paywall. Revenue from subscriptions, not internal use.

**Target audiences:**
- Other LOUs wanting market intelligence
- Compliance teams at financial institutions
- Regulators and researchers
- Anyone needing LEI lookup/verification

**Target features:**
- Overview dashboard — total LEIs, active/inactive, growth trends, top jurisdictions
- LOU Explorer — neutral market intelligence on all 40 LOUs (market share, growth, pricing)
- Company Search — search/lookup any of 3.16M LEIs by name or code
- LEI Detail — full record view, entity info, managing LOU, registration history
- Jurisdictions — LEI density by country, growth corridors
- Future: pricing scraper (LOU websites), DQ scores (GLEIF), historical snapshots, auth/paywall

**The owner is an LOU themselves but LEIPal is built as a neutral product — no single LOU's perspective is favoured.**

---

## Tech Stack
| Layer | Choice | Notes |
|---|---|---|
| Backend | Python 3.12 + FastAPI | Running on port 8000 |
| Frontend | Next.js 16 (React) | Running on port 3000 (`npm run dev`) |
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
├── backend/
│   ├── pyproject.toml               ← Poetry deps (FastAPI, Polars, psycopg3, Alembic, httpx, tqdm)
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/0001_initial_schema.py
│   └── app/
│       ├── main.py                  ← FastAPI app, mounts routers + CORS
│       ├── config.py                ← Settings loaded from .env
│       ├── database.py              ← SQLAlchemy engine + SessionLocal
│       ├── models.py                ← ORM: LeiRecord, Lou, PipelineWatermark
│       ├── api/v1/
│       │   ├── stats.py             ← /stats/summary, /stats/growth, /stats/jurisdictions
│       │   ├── lous.py              ← /lous, /lous/{lei}
│       │   └── search.py            ← /search, /search/lei/{lei} (+ GLEIF API enrichment)
│       └── pipeline/
│           ├── download.py          ← Downloads full + delta ZIPs from GLEIF
│           ├── parse.py             ← Streaming XML parser (iterparse, namespace auto-detect)
│           └── load.py              ← COPY full load + batched upsert for deltas
└── frontend/
    ├── next.config.ts               ← API rewrite proxy → localhost:8000
    ├── package.json                 ← Next.js 16, Recharts, lucide-react, clsx, i18n-iso-countries
    ├── app/
    │   ├── layout.tsx               ← Root layout with Sidebar
    │   ├── page.tsx                 ← Redirects / → /overview
    │   ├── globals.css              ← Tailwind v4 @theme colours
    │   ├── overview/page.tsx
    │   ├── lous/page.tsx
    │   ├── lous/[lei]/page.tsx
    │   ├── search/page.tsx          ← Client component (live search)
    │   ├── lei/[lei]/page.tsx
    │   └── jurisdictions/page.tsx
    ├── components/
    │   ├── sidebar.tsx              ← Fixed sidebar with nav + active state
    │   ├── stat-card.tsx            ← Reusable metric card
    │   └── growth-chart.tsx         ← Recharts AreaChart (client component)
    └── lib/
        ├── api.ts                   ← fetch helpers for all backend endpoints
        └── jurisdictions.ts         ← jurisdictionName() using i18n-iso-countries
```

---

## Current Status
### ✅ Phase 1: Full Data Pipeline — COMPLETE
- PostgreSQL running in Docker
- 3,163,412 LEIs loaded from GLEIF golden copy XML
- Delta updates working (LastWeek default, ~7k records, seconds to apply)
- Verification endpoint: `GET /api/v1/stats/summary`
- All committed to GitHub: https://github.com/janisbau/LEIPal

### ✅ Phase 2: Frontend Dashboard — COMPLETE
Stack: Next.js 16 in `frontend/` directory. Start with `npm run dev` from `frontend/`.

**Design**: Dark terminal aesthetic — navy (#0D1117) background, teal (#00D4AA) accent, card (#161B22), border (#21262D), muted (#8B949E). Tailwind v4 with `@theme` in globals.css (no tailwind.config.js).

**Pages built:**
- `/overview` — stat cards (total LEIs, active, new this month, LOUs), cumulative growth chart, top jurisdictions by country
- `/lous` — table of all 40 LOUs with active LEIs, market share bar, full country name
- `/lous/[lei]` — LOU detail: stats, top jurisdictions, "View Entity →" link to LEI record
- `/search` — live search (300ms debounce) by name or LEI, shows managing LOU name
- `/lei/[lei]` — full LEI detail enriched from GLEIF public API (addresses, legal form, dates, managing LOU)
- `/jurisdictions` — top 30 active jurisdictions with distribution bars, full country names

**API endpoints:**
- `GET /api/v1/stats/summary` — totals, by_status, top_jurisdictions (grouped by country), lous_count
- `GET /api/v1/stats/growth` — monthly cumulative from initial_registration_date
- `GET /api/v1/stats/jurisdictions` — top 30 active, grouped by country, with share %
- `GET /api/v1/lous` — all LOUs with active/total/inactive counts + market_share
- `GET /api/v1/lous/{lei}` — single LOU detail + top_jurisdictions breakdown
- `GET /api/v1/search?q=` — name/LEI search with managing LOU name joined
- `GET /api/v1/search/lei/{lei}` — full record from DB + enriched from GLEIF API

**Key implementation notes:**
- `lib/jurisdictions.ts` — `jurisdictionName()` using `i18n-iso-countries` + US/CA/AU subdivision map
- Jurisdictions grouped by country: `SPLIT_PART(jurisdiction, '-', 1)` in SQL (US-DE + US-NY → US)
- LEI detail enrichment: backend calls `https://api.gleif.org/api/v1/lei-records/{lei}`, falls back to DB if API unavailable
- Managing LOU LEI uses GLEIF API value (more reliable than our DB field)
- `next.config.ts` rewrites `/api/*` → `http://localhost:8000/api/*` for browser requests; server components use `http://localhost:8000` directly via `NEXT_PUBLIC_API_URL`

**LOU Explorer data availability:**
| Column | Status |
|---|---|
| Active LEIs, Market share | ✅ Live |
| MoM / YoY growth | ❌ Need historical snapshots |
| Issue/Renewal pricing | ❌ Need to scrape LOU websites |
| DQ score | ❌ GLEIF publishes separately |

### Phase 3: Advanced Features (future)
- Level 2 data (ownership chains)
- Market predictions
- Company profile pages
- Automated delta scheduling (AWS EventBridge or cron)
- AWS deployment (EC2 + RDS + S3)

---

## Open Questions
1. **Auth/paywall** — which features are free vs paid? When do we add login?
2. **Historical snapshots** — to show growth charts, we need to start capturing daily/weekly DB snapshots. Set this up early so data accumulates.
3. **LOU pricing scraper** — which LOU websites to scrape first?
4. **Domain/branding** — leipal.com or similar? Any logo?

---

## How to Start the Project (after relaunch)

```powershell
# 1. Start the database
cd C:\Users\jbauv\LEIPal
docker-compose up -d

# 2. Start the API (Terminal 1)
cd C:\Users\jbauv\LEIPal\backend
poetry run uvicorn app.main:app --reload

# 3. Start the frontend (Terminal 2)
cd C:\Users\jbauv\LEIPal\frontend
npm run dev

# 4. Open the app
# Frontend: http://localhost:3000
# API docs:  http://localhost:8000/docs
# pgAdmin:   http://localhost:5050  (admin@leipal.local / admin)

# 5. Apply weekly delta update (run once a week or so)
cd C:\Users\jbauv\LEIPal\backend
poetry run python -m app.pipeline.download --mode delta
poetry run python -m app.pipeline.load --mode delta --file .\data\deltas\<filename>.zip
```
