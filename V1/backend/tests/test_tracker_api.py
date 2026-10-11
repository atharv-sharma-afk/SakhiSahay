from __future__ import annotations

from datetime import date, timedelta


def _d(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


def test_health_endpoint_reports_capabilities(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["llm"]["configured"] is False
    assert "index_ready" in body["knowledge"]


def test_period_crud_roundtrip(client):
    created = client.post("/api/tracker/periods", json={"start_date": _d(40), "end_date": _d(36), "flow": "medium"})
    assert created.status_code == 201, created.text
    period = created.json()
    assert period["flow"] == "medium"

    listed = client.get("/api/tracker/periods").json()
    assert [p["id"] for p in listed] == [period["id"]]

    updated = client.put(
        f"/api/tracker/periods/{period['id']}",
        json={"start_date": _d(40), "end_date": _d(35), "flow": "heavy", "notes": "  felt tired  "},
    )
    assert updated.status_code == 200
    assert updated.json()["end_date"] == _d(35)
    assert updated.json()["notes"] == "felt tired"

    deleted = client.delete(f"/api/tracker/periods/{period['id']}")
    assert deleted.status_code == 204
    assert client.get("/api/tracker/periods").json() == []
    assert client.delete(f"/api/tracker/periods/{period['id']}").status_code == 404


def test_period_validation_rules(client):
    bad_range = client.post("/api/tracker/periods", json={"start_date": _d(10), "end_date": _d(12)})
    assert bad_range.status_code == 422
    assert any("end_date" in e["field"] or "end_date" in e["message"] for e in bad_range.json()["errors"])

    future = client.post("/api/tracker/periods", json={"start_date": (date.today() + timedelta(days=1)).isoformat()})
    assert future.status_code == 422

    too_long = client.post("/api/tracker/periods", json={"start_date": _d(60), "end_date": _d(20)})
    assert too_long.status_code == 422

    bad_flow = client.post("/api/tracker/periods", json={"start_date": _d(5), "flow": "torrential"})
    assert bad_flow.status_code == 422


def test_overlapping_periods_rejected(client):
    assert client.post("/api/tracker/periods", json={"start_date": _d(30), "end_date": _d(26)}).status_code == 201
    overlap = client.post("/api/tracker/periods", json={"start_date": _d(27), "end_date": _d(24)})
    assert overlap.status_code == 409
    adjacent = client.post("/api/tracker/periods", json={"start_date": _d(25), "end_date": _d(22)})
    assert adjacent.status_code == 201


def test_open_period_can_be_closed_later(client):
    created = client.post("/api/tracker/periods", json={"start_date": _d(3)})
    assert created.status_code == 201
    assert created.json()["end_date"] is None
    summary = client.get("/api/tracker/summary").json()
    assert summary["current_period_open"] is True
    closed = client.put(f"/api/tracker/periods/{created.json()['id']}", json={"start_date": _d(3), "end_date": _d(0)})
    assert closed.status_code == 200
    assert client.get("/api/tracker/summary").json()["current_period_open"] is False


def test_symptom_crud_and_catalogue(client):
    catalogue = client.get("/api/tracker/symptom-catalogue").json()
    keys = {item["key"] for item in catalogue}
    assert {"cramps", "fatigue", "headache", "bloating", "mood_changes"} <= keys

    unknown = client.post("/api/tracker/symptoms", json={"record_date": _d(1), "symptom": "dragon_breath"})
    assert unknown.status_code == 422

    created = client.post("/api/tracker/symptoms", json={"record_date": _d(1), "symptom": "Cramps", "severity": 2})
    assert created.status_code == 201
    assert created.json()["symptom"] == "cramps"

    too_severe = client.post("/api/tracker/symptoms", json={"record_date": _d(1), "symptom": "cramps", "severity": 9})
    assert too_severe.status_code == 422

    sid = created.json()["id"]
    updated = client.put(f"/api/tracker/symptoms/{sid}", json={"record_date": _d(1), "symptom": "cramps", "severity": 3})
    assert updated.json()["severity"] == 3
    assert client.delete(f"/api/tracker/symptoms/{sid}").status_code == 204
    assert client.get("/api/tracker/symptoms").json() == []


def test_records_are_isolated_per_user(client, second_user):
    mine = client.post("/api/tracker/periods", json={"start_date": _d(20), "end_date": _d(16)}).json()
    other_headers = {"X-User-Id": second_user}

    assert client.get("/api/tracker/periods", headers=other_headers).json() == []
    assert client.delete(f"/api/tracker/periods/{mine['id']}", headers=other_headers).status_code == 404
    assert client.put(
        f"/api/tracker/periods/{mine['id']}", json={"start_date": _d(20)}, headers=other_headers
    ).status_code == 404

    theirs = client.post("/api/tracker/periods", json={"start_date": _d(20), "end_date": _d(16)}, headers=other_headers)
    assert theirs.status_code == 201  # same dates do not collide across users
    assert len(client.get("/api/tracker/periods").json()) == 1

    assert client.get("/api/tracker/periods", headers={"X-User-Id": "nope"}).status_code == 404


def test_delete_all_user_data(client):
    client.post("/api/tracker/periods", json={"start_date": _d(20)})
    client.post("/api/tracker/symptoms", json={"record_date": _d(2), "symptom": "fatigue"})
    res = client.delete("/api/tracker/all")
    assert res.json() == {"periods_deleted": 1, "symptoms_deleted": 1}
    assert client.get("/api/tracker/summary").json()["period_count"] == 0


def test_chat_returns_503_when_index_missing(client):
    res = client.post("/api/chat", json={"question": "What is a normal cycle length?"})
    assert res.status_code == 503
    assert "ingest" in res.json()["detail"]


def test_chat_validates_question_length(client):
    assert client.post("/api/chat", json={"question": "hi"}).status_code == 422


def test_doctor_directory_is_clearly_demo(client):
    body = client.get("/api/doctors").json()
    assert "Demonstration only" in body["notice"]
    assert all(d["is_demo"] for d in body["doctors"])
