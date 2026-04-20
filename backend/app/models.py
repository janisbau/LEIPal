from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LeiRecord(Base):
    __tablename__ = "lei_records"

    lei: Mapped[str] = mapped_column(String(20), primary_key=True)
    legal_name: Mapped[str | None] = mapped_column(Text)
    jurisdiction: Mapped[str | None] = mapped_column(String(10))  # e.g. "GB", "US-DE"
    entity_status: Mapped[str | None] = mapped_column(String(30))  # ACTIVE, INACTIVE, …
    entity_category: Mapped[str | None] = mapped_column(String(30))  # GENERAL, BRANCH, FUND
    managing_lou: Mapped[str | None] = mapped_column(String(20))
    registration_status: Mapped[str | None] = mapped_column(String(30))
    initial_registration_date: Mapped[date | None] = mapped_column(Date)
    last_update_date: Mapped[date | None] = mapped_column(Date)
    next_renewal_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Lou(Base):
    __tablename__ = "lous"

    lou_lei: Mapped[str] = mapped_column(String(20), primary_key=True)
    lou_name: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(5))
    website: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(30))


class PipelineWatermark(Base):
    __tablename__ = "pipeline_watermark"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_name: Mapped[str] = mapped_column(Text, unique=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    record_count: Mapped[int | None] = mapped_column(Integer)
