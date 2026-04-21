from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LeiRecord, Lou

router = APIRouter(prefix="/lous", tags=["lous"])


@router.get("")
def list_lous(db: Session = Depends(get_db)):
    """All LOUs with active LEI count and market share."""
    rows = db.execute(text("""
        SELECT
            l.lou_lei,
            l.lou_name,
            l.country,
            l.status,
            COUNT(r.lei)                                          AS total_leis,
            COUNT(CASE WHEN r.entity_status = 'ACTIVE' THEN 1 END) AS active_leis,
            COUNT(CASE WHEN r.entity_status = 'INACTIVE' THEN 1 END) AS inactive_leis
        FROM lous l
        LEFT JOIN lei_records r ON r.managing_lou = l.lou_lei
        GROUP BY l.lou_lei, l.lou_name, l.country, l.status
        ORDER BY active_leis DESC
    """)).all()

    total_active = sum(r.active_leis for r in rows) or 1
    return [
        {
            "lou_lei": r.lou_lei,
            "lou_name": r.lou_name,
            "country": r.country,
            "status": r.status,
            "total_leis": int(r.total_leis),
            "active_leis": int(r.active_leis),
            "inactive_leis": int(r.inactive_leis),
            "market_share": round(r.active_leis / total_active * 100, 2),
        }
        for r in rows
    ]


@router.get("/{lou_lei}")
def get_lou(lou_lei: str, db: Session = Depends(get_db)):
    """Single LOU detail with jurisdiction breakdown."""
    lou = db.get(Lou, lou_lei)
    if not lou:
        raise HTTPException(status_code=404, detail="LOU not found")

    stats = db.execute(text("""
        SELECT
            COUNT(*)                                              AS total_leis,
            COUNT(CASE WHEN entity_status = 'ACTIVE' THEN 1 END) AS active_leis,
            COUNT(CASE WHEN entity_status = 'INACTIVE' THEN 1 END) AS inactive_leis,
            MIN(initial_registration_date)                        AS first_registration,
            MAX(initial_registration_date)                        AS last_registration
        FROM lei_records
        WHERE managing_lou = :lei
    """), {"lei": lou_lei}).first()

    jurisdictions = db.execute(text("""
        SELECT jurisdiction, COUNT(*) AS n
        FROM lei_records
        WHERE managing_lou = :lei AND jurisdiction IS NOT NULL
        GROUP BY jurisdiction
        ORDER BY n DESC
        LIMIT 10
    """), {"lei": lou_lei}).all()

    return {
        "lou_lei": lou.lou_lei,
        "lou_name": lou.lou_name,
        "country": lou.country,
        "status": lou.status,
        "total_leis": int(stats.total_leis),
        "active_leis": int(stats.active_leis),
        "inactive_leis": int(stats.inactive_leis),
        "first_registration": stats.first_registration.isoformat() if stats.first_registration else None,
        "last_registration": stats.last_registration.isoformat() if stats.last_registration else None,
        "top_jurisdictions": [
            {"jurisdiction": r.jurisdiction, "count": int(r.n)} for r in jurisdictions
        ],
    }
