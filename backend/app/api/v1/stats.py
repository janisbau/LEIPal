from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LeiRecord, Lou, PipelineWatermark

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """
    Quick sanity-check endpoint: total LEI counts, status breakdown,
    top jurisdictions, and LOU count. Confirms the pipeline loaded data correctly.
    """
    total = db.scalar(select(func.count()).select_from(LeiRecord)) or 0

    status_rows = db.execute(
        select(LeiRecord.entity_status, func.count().label("n"))
        .group_by(LeiRecord.entity_status)
        .order_by(func.count().desc())
    ).all()
    by_status = {row.entity_status or "unknown": row.n for row in status_rows}

    jurisdiction_rows = db.execute(
        select(LeiRecord.jurisdiction, func.count().label("n"))
        .where(LeiRecord.jurisdiction.isnot(None))
        .group_by(LeiRecord.jurisdiction)
        .order_by(func.count().desc())
        .limit(10)
    ).all()
    top_jurisdictions = [{"jurisdiction": r.jurisdiction, "count": r.n} for r in jurisdiction_rows]

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
