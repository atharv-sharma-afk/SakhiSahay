"""Descriptive insights computed from a user's own stored records.

Rules of this module:
- Every statement is a plain description of recorded data; nothing is a diagnosis.
- Insights are only emitted when the records support them (minimum thresholds below).
- "Guidance" insights quote general thresholds from a cited public source and are
  phrased as information, not as an assessment of the user.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from statistics import mean, median

from app.db import models
from app.schemas.insights import CycleStats, DataRequirement, Insight, InsightsResponse
from app.schemas.tracker import SYMPTOM_CATALOGUE

MIN_CYCLES_FOR_LENGTH = 2  # cycles, i.e. 3 logged period starts
MIN_PERIODS_FOR_DURATION = 2
MIN_CYCLES_FOR_SYMPTOM_FREQ = 3
RECENT_WINDOW_DAYS = 90

# NHS: "Regular cycles that are longer or shorter than 28 days, from 21 to 35 days, are normal."
# and "A period usually lasts 2 to 7 days". Used for general guidance text only.
NHS_PERIOD_PROBLEMS_URL = "https://www.nhs.uk/conditions/periods/period-problems/"
NHS_IRREGULAR_URL = "https://www.nhs.uk/symptoms/irregular-periods/"
NHS_HEAVY_URL = "https://www.nhs.uk/conditions/heavy-periods/"

SYMPTOM_LABELS = {s["key"]: s["label"] for s in SYMPTOM_CATALOGUE}


def _cycle_lengths(starts: list[date]) -> list[int]:
    ordered = sorted(starts)
    return [(b - a).days for a, b in zip(ordered, ordered[1:])]


def compute_stats(periods: list[models.PeriodRecord], today: date | None = None) -> CycleStats:
    today = today or date.today()
    starts = [p.start_date for p in periods]
    lengths = _cycle_lengths(starts)
    durations = [(p.end_date - p.start_date).days + 1 for p in periods if p.end_date is not None]
    last_start = max(starts) if starts else None
    return CycleStats(
        logged_periods=len(periods),
        completed_cycles=len(lengths),
        cycle_lengths_days=lengths,
        average_cycle_length=round(mean(lengths), 1) if lengths else None,
        median_cycle_length=float(median(lengths)) if lengths else None,
        shortest_cycle=min(lengths) if lengths else None,
        longest_cycle=max(lengths) if lengths else None,
        average_period_duration=round(mean(durations), 1) if durations else None,
        periods_with_duration=len(durations),
        last_period_start=last_start,
        days_since_last_period_start=(today - last_start).days if last_start else None,
    )


def _cycle_windows(starts: list[date]) -> list[tuple[date, date]]:
    """Half-open windows [start_i, start_{i+1}) for each completed cycle, newest last."""
    ordered = sorted(starts)
    return [(a, b) for a, b in zip(ordered, ordered[1:])]


def build_insights(
    periods: list[models.PeriodRecord],
    symptoms: list[models.SymptomRecord],
    today: date | None = None,
) -> InsightsResponse:
    today = today or date.today()
    stats = compute_stats(periods, today)
    insights: list[Insight] = []
    requirements: list[DataRequirement] = []
    starts = [p.start_date for p in periods]

    # ---- cycle length -----------------------------------------------------
    if stats.completed_cycles >= MIN_CYCLES_FOR_LENGTH:
        lengths = stats.cycle_lengths_days
        spread = (stats.longest_cycle or 0) - (stats.shortest_cycle or 0)
        if spread <= 3:
            variability = "have been fairly consistent"
        elif spread <= 7:
            variability = "have varied moderately"
        else:
            variability = "have varied noticeably"
        if stats.shortest_cycle == stats.longest_cycle:
            range_text = f"cycle length was {stats.shortest_cycle} days every time"
        else:
            range_text = (
                f"cycle length ranged from {stats.shortest_cycle} to {stats.longest_cycle} days "
                f"(median {stats.median_cycle_length:g})"
            )
        insights.append(
            Insight(
                kind="cycle_length",
                title="Your recorded cycle lengths",
                statement=f"Across {stats.completed_cycles} completed cycles you logged, {range_text}. Your cycles {variability}.",
                basis=(
                    "Cycle length = days between consecutive logged period start dates: "
                    + ", ".join(str(n) for n in lengths)
                    + "."
                ),
                records_used=stats.logged_periods,
            )
        )
        outside = [n for n in lengths if n < 21 or n > 35]
        if outside:
            insights.append(
                Insight(
                    kind="guidance",
                    title="General guidance on cycle length",
                    statement=(
                        f"{len(outside)} of your {len(lengths)} recorded cycle lengths fall outside 21-35 days. "
                        "NHS describes a cycle as irregular when the gap between periods is less than 21 or more "
                        "than 35 days, and suggests speaking to a GP if periods are irregular or your usual pattern "
                        "changes. This is general information, not an assessment of you."
                    ),
                    basis=f"Recorded cycle lengths outside 21-35 days: {', '.join(str(n) for n in outside)}.",
                    records_used=stats.logged_periods,
                    source_url=NHS_IRREGULAR_URL,
                    source_label="NHS - Irregular periods",
                )
            )
    else:
        needed = MIN_CYCLES_FOR_LENGTH + 1 - stats.logged_periods
        requirements.append(
            DataRequirement(
                metric="cycle_length",
                message=(
                    f"Log {needed} more period start date{'s' if needed != 1 else ''} to see your cycle-length summary "
                    f"(needs {MIN_CYCLES_FOR_LENGTH + 1} logged periods)."
                ),
            )
        )

    # ---- period duration ----------------------------------------------------
    if stats.periods_with_duration >= MIN_PERIODS_FOR_DURATION:
        durations = [(p.end_date - p.start_date).days + 1 for p in periods if p.end_date]
        if min(durations) == max(durations):
            duration_text = f"bleeding lasted {min(durations)} days each time"
        else:
            duration_text = f"bleeding lasted {min(durations)} to {max(durations)} days (average {stats.average_period_duration:g})"
        insights.append(
            Insight(
                kind="period_duration",
                title="How long your periods lasted",
                statement=f"For the {stats.periods_with_duration} periods where you logged an end date, {duration_text}.",
                basis="Duration = end date - start date + 1 for each period with an end date: "
                + ", ".join(str(d) for d in durations)
                + ".",
                records_used=stats.periods_with_duration,
            )
        )
        long_periods = [d for d in durations if d > 7]
        if long_periods:
            insights.append(
                Insight(
                    kind="guidance",
                    title="General guidance on period length",
                    statement=(
                        f"{len(long_periods)} of your logged periods lasted more than 7 days. NHS notes that periods "
                        "usually last 2 to 7 days and lists periods lasting longer than 7 days among the reasons to see "
                        "a GP. This is general information, not an assessment of you."
                    ),
                    basis=f"Logged durations over 7 days: {', '.join(str(d) for d in long_periods)}.",
                    records_used=stats.periods_with_duration,
                    source_url=NHS_HEAVY_URL,
                    source_label="NHS - Heavy periods",
                )
            )
    else:
        requirements.append(
            DataRequirement(
                metric="period_duration",
                message=f"Add an end date to at least {MIN_PERIODS_FOR_DURATION} periods to see how long they usually last.",
            )
        )

    # ---- symptom frequency per logged cycle ---------------------------------
    windows = _cycle_windows(starts)
    if len(windows) >= MIN_CYCLES_FOR_SYMPTOM_FREQ and symptoms:
        recent_windows = windows[-5:]
        per_symptom: Counter[str] = Counter()
        for symptom_key in {s.symptom for s in symptoms}:
            dates = {s.record_date for s in symptoms if s.symptom == symptom_key}
            hits = sum(1 for (a, b) in recent_windows if any(a <= d < b for d in dates))
            per_symptom[symptom_key] = hits
        top_key, top_hits = per_symptom.most_common(1)[0]
        if top_hits >= 2:
            label = SYMPTOM_LABELS.get(top_key, top_key)
            insights.append(
                Insight(
                    kind="symptom_frequency",
                    title=f"{label} across your logged cycles",
                    statement=f"You logged {label.lower()} in {top_hits} of your last {len(recent_windows)} cycles.",
                    basis=(
                        "A cycle counts if at least one entry for this symptom falls between that cycle's period "
                        "start date and the next period start date."
                    ),
                    records_used=len(symptoms),
                )
            )
    elif symptoms and len(windows) < MIN_CYCLES_FOR_SYMPTOM_FREQ:
        requirements.append(
            DataRequirement(
                metric="symptom_frequency",
                message=(
                    f"Symptom-per-cycle patterns appear once {MIN_CYCLES_FOR_SYMPTOM_FREQ + 1} period start dates are logged."
                ),
            )
        )

    # ---- symptom days in recent window -------------------------------------
    window_start = today - timedelta(days=RECENT_WINDOW_DAYS)
    recent = [s for s in symptoms if s.record_date >= window_start]
    if recent:
        days_by_symptom: dict[str, set[date]] = {}
        for s in recent:
            days_by_symptom.setdefault(s.symptom, set()).add(s.record_date)
        key, days = max(days_by_symptom.items(), key=lambda kv: len(kv[1]))
        if len(days) >= 3:
            label = SYMPTOM_LABELS.get(key, key)
            severe_days = len({s.record_date for s in recent if s.symptom == key and (s.severity or 0) >= 3})
            severity_note = f" {severe_days} of those days were marked severe." if severe_days else ""
            insights.append(
                Insight(
                    kind="symptom_days",
                    title=f"{label} in the last {RECENT_WINDOW_DAYS} days",
                    statement=f"You logged {label.lower()} on {len(days)} different days in the last {RECENT_WINDOW_DAYS} days.{severity_note}",
                    basis=f"Distinct dates with a '{label}' entry since {window_start.isoformat()}.",
                    records_used=len(recent),
                )
            )
    if not symptoms:
        requirements.append(
            DataRequirement(metric="symptoms", message="Log symptoms on a few days to see which ones recur for you.")
        )

    return InsightsResponse(stats=stats, insights=insights, requirements=requirements)
