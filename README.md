# LEIPal

LEI analytics platform — market stats, growth trends, and LOU competitor analysis.

## Phase 1: Data Pipeline

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for PostgreSQL)
- [Python 3.12+](https://www.python.org/)
- [Poetry](https://python-poetry.org/docs/#installation)

### Setup

```bash
# 1. Copy env file and set your passwords if desired
cp .env.example .env

# 2. Start PostgreSQL + pgAdmin
docker-compose up -d

# 3. Install Python dependencies
cd backend
poetry install

# 4. Run DB migrations
poetry run alembic upgrade head

# 5. Download the full GLEIF golden copy (~4-5 GB, takes a while)
poetry run python -m app.pipeline.download --mode full

# 6. Load the downloaded file into PostgreSQL (~10-30 min)
poetry run python -m app.pipeline.load --mode full --file ./data/full/<downloaded_file>.zip

# 7. Verify the load
poetry run uvicorn app.main:app --reload
# Then open: http://localhost:8000/api/v1/stats/summary
```

### Applying Delta Updates

GLEIF publishes delta files 3× per day. To apply the latest:

```bash
# Download deltas for today
poetry run python -m app.pipeline.download --mode delta

# Apply each downloaded delta
poetry run python -m app.pipeline.load --mode delta --file ./data/deltas/<delta_file>.zip
```

### Services

| Service | URL | Credentials |
|---|---|---|
| FastAPI docs | http://localhost:8000/docs | — |
| pgAdmin | http://localhost:5050 | admin@leipal.local / admin |

### Project Structure

```
LEIPal/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── models.py         # SQLAlchemy ORM
│   │   ├── database.py       # DB session
│   │   ├── config.py         # Settings (env vars)
│   │   ├── api/v1/
│   │   │   └── stats.py      # /api/v1/stats/summary endpoint
│   │   └── pipeline/
│   │       ├── download.py   # GLEIF file downloader
│   │       ├── parse.py      # Polars CSV parser
│   │       └── load.py       # PostgreSQL bulk loader + delta upsert
│   ├── alembic/              # DB migrations
│   └── pyproject.toml
├── docker-compose.yml
├── .env.example
└── .gitignore
```
