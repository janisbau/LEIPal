from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
import httpx

from app.database import get_db
from app.models import LeiRecord, Lou

router = APIRouter(prefix="/search", tags=["search"])

GLEIF_API = "https://api.gleif.org/api/v1"


@router.get("")
def search_leis(
    q: str = Query(..., min_length=2, description="Search by LEI code or legal name"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search lei_records by LEI code (exact prefix) or legal name (ilike)."""
    q = q.strip()

    rows = db.execute(text("""
        SELECT
            r.lei,
            r.legal_name,
            r.jurisdiction,
            r.entity_status,
            r.entity_category,
            r.managing_lou,
            r.registration_status,
            l.lou_name AS managing_lou_name
        FROM lei_records r
        LEFT JOIN lous l ON l.lou_lei = r.managing_lou
        WHERE r.lei ILIKE :lei_prefix
           OR r.legal_name ILIKE :name_pattern
        ORDER BY length(r.lei), r.legal_name
        LIMIT :lim
    """), {"lei_prefix": f"{q}%", "name_pattern": f"%{q}%", "lim": limit}).all()

    return [
        {
            "lei": r.lei,
            "legal_name": r.legal_name,
            "jurisdiction": r.jurisdiction,
            "entity_status": r.entity_status,
            "entity_category": r.entity_category,
            "managing_lou": r.managing_lou,
            "managing_lou_name": r.managing_lou_name,
            "registration_status": r.registration_status,
        }
        for r in rows
    ]


def _fmt_address(addr: dict) -> dict | None:
    """Normalise a GLEIF address block into a flat dict."""
    if not addr:
        return None
    lines = addr.get("addressLines", []) or []
    return {
        "lines": [l["value"] if isinstance(l, dict) else str(l) for l in lines if l],
        "city": addr.get("city"),
        "region": addr.get("region"),
        "country": addr.get("country"),
        "postal_code": addr.get("postalCode"),
    }


@router.get("/lei/{lei}")
def get_lei(lei: str, db: Session = Depends(get_db)):
    """
    Full LEI record: combines our local DB (search base) with live GLEIF API
    data for addresses, legal form, other names, and registration details.
    """
    import traceback

    lei = lei.upper()
    record = db.get(LeiRecord, lei)
    if not record:
        raise HTTPException(status_code=404, detail="LEI not found")

    # Fetch full detail from GLEIF public API first
    gleif_entity: dict = {}
    gleif_reg: dict = {}
    try:
        resp = httpx.get(f"{GLEIF_API}/lei-records/{lei}", timeout=8)
        if resp.status_code == 200:
            raw = resp.json()
            data = (raw.get("data") or {}).get("attributes") or {}
            gleif_entity = data.get("entity") or {}
            gleif_reg = data.get("registration") or {}
    except Exception:
        traceback.print_exc()  # visible in uvicorn terminal

    # Use GLEIF API managing LOU if available (more reliable than our DB field)
    managing_lou_lei = gleif_reg.get("managingLou") or record.managing_lou
    lou = db.get(Lou, managing_lou_lei) if managing_lou_lei else None

    try:
        legal_addr = _fmt_address(gleif_entity.get("legalAddress"))
        hq_addr = _fmt_address(gleif_entity.get("headquartersAddress"))

        other_names = [
            n["name"] for n in (gleif_entity.get("otherNames") or [])
            if isinstance(n, dict) and n.get("name")
        ]

        legal_form_raw = gleif_entity.get("legalForm") or {}
        legal_form_other = legal_form_raw.get("other") if isinstance(legal_form_raw, dict) else None

        registered_as = gleif_entity.get("registeredAs")
        corroboration = gleif_reg.get("corroborationLevel")
        validated_at_raw = gleif_reg.get("validatedAt")
        validated_at = validated_at_raw.get("id") if isinstance(validated_at_raw, dict) else None

    except Exception:
        traceback.print_exc()
        legal_addr = hq_addr = None
        other_names = []
        legal_form_other = registered_as = corroboration = validated_at = None

    return {
        "lei": record.lei,
        "legal_name": record.legal_name,
        "other_names": other_names,
        "jurisdiction": record.jurisdiction,
        "entity_status": record.entity_status,
        "entity_category": record.entity_category,
        "legal_form": legal_form_other,
        "registered_as": registered_as,
        "registration_status": record.registration_status,
        "managing_lou": managing_lou_lei,
        "managing_lou_name": lou.lou_name if lou else None,
        "legal_address": legal_addr,
        "hq_address": hq_addr,
        "initial_registration_date": record.initial_registration_date.isoformat() if record.initial_registration_date else None,
        "last_update_date": record.last_update_date.isoformat() if record.last_update_date else None,
        "next_renewal_date": record.next_renewal_date.isoformat() if record.next_renewal_date else None,
        "corroboration_level": corroboration,
        "validated_at": validated_at,
    }
