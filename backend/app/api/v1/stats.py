from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LeiRecord, Lou, PipelineWatermark

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Total LEI counts, status breakdown, top jurisdictions, LOU count."""
    total = db.scalar(select(func.count()).select_from(LeiRecord)) or 0

    status_rows = db.execute(
        select(LeiRecord.entity_status, func.count().label("n"))
        .group_by(LeiRecord.entity_status)
        .order_by(func.count().desc())
    ).all()
    by_status = {row.entity_status or "unknown": row.n for row in status_rows}

    jurisdiction_rows = db.execute(text("""
        SELECT
            SPLIT_PART(jurisdiction, '-', 1) AS country,
            COUNT(*) AS n
        FROM lei_records
        WHERE jurisdiction IS NOT NULL
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 10
    """)).all()
    top_jurisdictions = [{"jurisdiction": r.country, "count": r.n} for r in jurisdiction_rows]

    lous_count = db.scalar(select(func.count()).select_from(Lou)) or 0

    last_watermark = db.execute(
        select(PipelineWatermark.file_name, PipelineWatermark.applied_at)
        .order_by(PipelineWatermark.applied_at.desc())
        .limit(1)
    ).first()

    return {
        "total_leis": total,
        "by_status": by_status,
        "top_jurisdictions": top_jurisdictions,
        "lous_count": lous_count,
        "last_pipeline_run": {
            "file": last_watermark.file_name if last_watermark else None,
            "applied_at": last_watermark.applied_at.isoformat() if last_watermark else None,
        },
    }


@router.get("/growth")
def get_growth(db: Session = Depends(get_db)):
    """
    Monthly cumulative LEI registrations derived from initial_registration_date.
    Returns one data point per month from 2012 to today.
    """
    rows = db.execute(text("""
        SELECT
            DATE_TRUNC('month', initial_registration_date)::date AS month,
            COUNT(*) AS new_leis
        FROM lei_records
        WHERE initial_registration_date IS NOT NULL
          AND initial_registration_date >= '2012-01-01'
        GROUP BY 1
        ORDER BY 1
    """)).all()

    cumulative = 0
    result = []
    for row in rows:
        cumulative += row.new_leis
        result.append({
            "month": row.month.isoformat(),
            "new_leis": int(row.new_leis),
            "cumulative": cumulative,
        })
    return result


@router.get("/jurisdictions")
def get_jurisdictions(db: Session = Depends(get_db)):
    """Full jurisdiction breakdown, active LEIs only."""
    rows = db.execute(text("""
        SELECT
            SPLIT_PART(jurisdiction, '-', 1) AS country,
            COUNT(*) AS n
        FROM lei_records
        WHERE jurisdiction IS NOT NULL
          AND entity_status = 'ACTIVE'
        GROUP BY 1
        ORDER BY 2 DESC
        LIMIT 30
    """)).all()
    total = sum(r.n for r in rows)
    return [
        {
            "jurisdiction": r.country,
            "count": r.n,
            "share": round(r.n / total * 100, 2) if total else 0,
        }
        for r in rows
    ]
