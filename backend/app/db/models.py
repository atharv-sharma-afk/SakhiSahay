from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text
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

    # ---- profile / onboarding (collected once, editable in Settings) ----------
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Baseline used for cycle-day and estimate calculations until enough real
    # cycles are logged. 28 / 5 are population medians, not assessments.
    cycle_length_days: Mapped[int] = mapped_column(Integer, default=28, server_default="28")
    period_length_days: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    periods_regular: Mapped[str | None] = mapped_column(String(12), nullable=True)  # yes | no | unsure
    period_feeling: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cycle_affects_sleep: Mapped[str | None] = mapped_column(String(12), nullable=True)  # yes | no | unsure
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list of goal keys
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ---- app lock -----------------------------------------------------------------
    # True only after a platform (Touch ID / Face ID / Windows Hello) WebAuthn
    # credential has been registered and verified server-side.
    biometric_lock_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    # Seconds the app may stay in the background before it re-locks. 0 = immediately.
    lock_timeout_seconds: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    periods: Mapped[list["PeriodRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    symptoms: Mapped[list["SymptomRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    credentials: Mapped[list["WebAuthnCredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class WebAuthnCredential(Base):
    """A public-key credential registered through the browser's WebAuthn API.

    Only the public key, credential id and signature counter are stored. No
    biometric data ever leaves the device; the OS performs Touch ID / Face ID
    and returns a signature that we verify here.
    """

    __tablename__ = "webauthn_credentials"
    __table_args__ = (Index("ix_webauthn_user", "user_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, unique=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports: Mapped[str | None] = mapped_column(String(120), nullable=True)
    device_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    backed_up: Mapped[bool] = mapped_column(Boolean, default=False)
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="credentials")


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
