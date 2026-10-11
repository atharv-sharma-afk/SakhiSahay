from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from app.services.insights_service import build_insights, compute_stats

TODAY = date(2026, 10, 11)


@dataclass
class P:
    start_date: date
    end_date: date | None = None


@dataclass
class S:
    record_date: date
    symptom: str
    severity: int | None = None


def _periods(starts: list[int], durations: list[int | None]) -> list[P]:
    out = []
    for days_ago, duration in zip(starts, durations):
        start = TODAY - timedelta(days=days_ago)
        out.append(P(start, start + timedelta(days=duration - 1) if duration else None))
    return out


def test_no_insights_for_a_single_period():
    res = build_insights(_periods([10], [5]), [], today=TODAY)
    assert res.insights == []
    assert {r.metric for r in res.requirements} == {"cycle_length", "period_duration", "symptoms"}
    assert res.stats.completed_cycles == 0
    assert res.stats.average_cycle_length is None


def test_cycle_length_statistics_are_exact():
    periods = _periods([66, 38, 10], [5, 4, None])  # starts 66, 38, 10 days ago -> gaps 28 and 28
    stats = compute_stats(periods, today=TODAY)
    assert stats.cycle_lengths_days == [28, 28]
    assert stats.average_cycle_length == 28.0
    assert stats.periods_with_duration == 2
    assert stats.average_period_duration == 4.5
    assert stats.days_since_last_period_start == 10

    res = build_insights(periods, [], today=TODAY)
    kinds = [i.kind for i in res.insights]
    assert "cycle_length" in kinds and "period_duration" in kinds
    assert "guidance" not in kinds  # 28-day cycles do not trigger the NHS range note
    cycle = next(i for i in res.insights if i.kind == "cycle_length")
    assert "was 28 days every time" in cycle.statement
    assert "28, 28" in cycle.basis


def test_guidance_only_when_recorded_values_leave_reference_range():
    periods = _periods([90, 48, 10], [9, 5, None])  # gaps 42 and 38; one period lasted 9 days
    res = build_insights(periods, [], today=TODAY)
    guidance = [i for i in res.insights if i.kind == "guidance"]
    assert len(guidance) == 2
    assert all(g.source_url and g.source_url.startswith("https://www.nhs.uk/") for g in guidance)
    assert all("not an assessment of you" in g.statement for g in guidance)


def test_symptom_frequency_counts_cycles_not_entries():
    periods = _periods([120, 92, 64, 36, 8], [5, 5, 5, 5, None])  # 4 completed cycles
    symptoms = [
        S(TODAY - timedelta(days=118), "cramps", 2),
        S(TODAY - timedelta(days=117), "cramps", 3),  # same cycle, must not double count
        S(TODAY - timedelta(days=90), "cramps", 1),
        S(TODAY - timedelta(days=34), "cramps", 2),
        S(TODAY - timedelta(days=5), "fatigue", 1),
    ]
    res = build_insights(periods, symptoms, today=TODAY)
    freq = next(i for i in res.insights if i.kind == "symptom_frequency")
    assert freq.statement == "You logged cramps in 3 of your last 4 cycles."


def test_recent_symptom_days_requires_three_distinct_days():
    two_days = [S(TODAY - timedelta(days=1), "fatigue"), S(TODAY - timedelta(days=1), "fatigue"), S(TODAY, "fatigue")]
    assert not [i for i in build_insights([], two_days, today=TODAY).insights if i.kind == "symptom_days"]
    three_days = two_days + [S(TODAY - timedelta(days=3), "fatigue", 3)]
    insight = next(i for i in build_insights([], three_days, today=TODAY).insights if i.kind == "symptom_days")
    assert "3 different days" in insight.statement
    assert "1 of those days were marked severe" in insight.statement
