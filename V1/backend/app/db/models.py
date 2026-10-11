from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Account shell. In local mode a single seeded user exists; JWT auth is a later phase."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String(80), default="Friend")
    preferred_language: Mapped[str] = mapped_column(String(12), default="en")
    # Consent flag for the (future) personalised-assistant feature. Defaults to off.
    consent_personalisation: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    periods: Mapped[list["PeriodRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    symptoms: Mapped[list["SymptomRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class PeriodRecord(Base):
    __tablename__ = "period_records"
    __table_args__ = (Index("ix_period_user_start", "user_id", "start_date"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # light | medium | heavy | spotting  (optional; users are never forced to record flow)
    flow: Mapped[str | None] = mapped_column(String(16), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="periods")


class SymptomRecord(Base):
    __tablename__ = "symptom_records"
    __table_args__ = (Index("ix_symptom_user_date", "user_id", "record_date"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    symptom: Mapped[str] = mapped_column(String(40), nullable=False)
    # 1 (mild) .. 3 (severe); optional because not every symptom has a meaningful severity
    severity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="symptoms")


class KnowledgeSource(Base):
    """Registry of ingested knowledge sources (mirrors the YAML manifest after ingestion).

    Chunks themselves live in Qdrant; this table lets the API expose what the
    assistant can cite and records extraction outcomes for auditability.
    """

    __tablename__ = "knowledge_sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    publisher: Mapped[str] = mapped_column(String(120), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(40), nullable=False)
    topic: Mapped[str] = mapped_column(String(60), nullable=False)
    language: Mapped[str] = mapped_column(String(12), default="en")
    published_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    updated_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    accessed_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    license_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # indexed | failed | pending
    status_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
