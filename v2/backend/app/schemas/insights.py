from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

InsightKind = Literal["cycle_length", "period_duration", "symptom_frequency", "symptom_days", "guidance"]


class Insight(BaseModel):
    """A single descriptive statement derived only from stored records.

    `basis` explains exactly which numbers produced the statement so the UI and
    the viva can show how the insight was calculated.
    """

    kind: InsightKind
    title: str
    statement: str
    basis: str
    records_used: int
    source_url: str | None = None
    source_label: str | None = None


class CycleStats(BaseModel):
    logged_periods: int
    completed_cycles: int
    cycle_lengths_days: list[int]
    average_cycle_length: float | None
    median_cycle_length: float | None
    shortest_cycle: int | None
    longest_cycle: int | None
    average_period_duration: float | None
    periods_with_duration: int
    last_period_start: date | None
    days_since_last_period_start: int | None


class DataRequirement(BaseModel):
    """Tells the UI what is still needed before a statistic can be shown."""

    metric: str
    message: str


class InsightsResponse(BaseModel):
    stats: CycleStats
    insights: list[Insight]
    requirements: list[DataRequirement]
    generated_from: str = "Your stored records only. Nothing here is a diagnosis."
