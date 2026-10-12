from __future__ import annotations

from datetime import date, timedelta


def test_profile_defaults_and_partial_update(client):
    res = client.get("/api/profile")
    assert res.status_code == 200
    body = res.json()
    assert body["cycle_length_days"] == 28
    assert body["period_length_days"] == 5
    assert body["onboarding_completed_at"] is None
    assert body["biometric_lock_enabled"] is False
    assert body["goals"] == []

    updated = client.put(
        "/api/profile",
        json={
            "display_name": "  Asha   Rao ",
            "age": 27,
            "cycle_length_days": 30,
            "period_length_days": 4,
            "periods_regular": "unsure",
            "period_feeling": "want_to_understand",
            "cycle_affects_sleep": "yes",
            "goals": ["track_period", "learn_cycle", "track_period"],
            "preferred_language": "hi",
            "onboarding_completed": True,
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["display_name"] == "Asha Rao"  # whitespace normalised
    assert body["goals"] == ["track_period", "learn_cycle"]  # de-duplicated, order kept
    assert body["preferred_language"] == "hi"
    assert body["onboarding_completed_at"] is not None
    assert body["onboarding_completed_at"].endswith("Z")

    # Partial update leaves other fields untouched
    partial = client.put("/api/profile", json={"age": 28}).json()
    assert partial["age"] == 28
    assert partial["display_name"] == "Asha Rao"
    assert partial["cycle_length_days"] == 30

    # Persisted: a fresh GET returns the same data
    again = client.get("/api/profile").json()
    assert again == partial


def test_profile_validation(client):
    assert client.put("/api/profile", json={"cycle_length_days": 5}).status_code == 422
    assert client.put("/api/profile", json={"period_length_days": 0}).status_code == 422
    assert client.put("/api/profile", json={"goals": ["win_lottery"]}).status_code == 422
    assert client.put("/api/profile", json={"period_feeling": "meh"}).status_code == 422
    assert client.put("/api/profile", json={"display_name": "   "}).status_code == 422
    assert client.put("/api/profile", json={"preferred_language": "fr"}).status_code == 422


def test_additive_migration_keeps_existing_rows(tmp_path):
    """A database created before the profile/lock columns existed must upgrade in place."""
    import sqlite3

    from sqlalchemy import create_engine

    from app.db.init_db import _sync_missing_columns
    from app.db.session import Base

    db_file = tmp_path / "old.db"
    conn = sqlite3.connect(db_file)
    conn.executescript(
        """
        CREATE TABLE users (
            id VARCHAR(32) PRIMARY KEY, display_name VARCHAR(80), preferred_language VARCHAR(12),
            consent_personalisation BOOLEAN, created_at DATETIME, updated_at DATETIME
        );
        INSERT INTO users VALUES ('u1', 'Keep Me', 'en', 0, '2026-01-01', '2026-01-01');
        """
    )
    conn.commit()
    conn.close()

    engine = create_engine(f"sqlite:///{db_file}", future=True)
    Base.metadata.create_all(bind=engine)  # creates missing *tables* only
    _sync_missing_columns(engine)

    conn = sqlite3.connect(db_file)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    assert {"cycle_length_days", "period_length_days", "biometric_lock_enabled", "onboarding_completed_at", "goals"} <= cols
    row = conn.execute("SELECT display_name, cycle_length_days, period_length_days, biometric_lock_enabled FROM users").fetchone()
    assert row == ("Keep Me", 28, 5, 0)  # row kept, server defaults applied
    assert "webauthn_credentials" in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()


def test_record_timestamps_are_utc_marked(client):
    """SQLite drops tzinfo; the API must still hand out unambiguous instants."""
    start = (date.today() - timedelta(days=3)).isoformat()
    period = client.post("/api/tracker/periods", json={"start_date": start}).json()
    assert period["created_at"].endswith("Z")
    assert period["start_date"] == start  # calendar dates stay plain YYYY-MM-DD
    symptom = client.post("/api/tracker/symptoms", json={"record_date": start, "symptom": "calm"}).json()
    assert symptom["created_at"].endswith("Z")
    assert symptom["record_date"] == start
