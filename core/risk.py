"""Explainable student risk scoring and attendance planning."""

from __future__ import annotations

import math
from typing import Any


def _percent(numerator: float, denominator: float) -> float:
    """Return a safe percentage when no records have been entered."""
    return numerator / denominator * 100 if denominator else 0.0


def assess_student(records: list[dict[str, Any]], remarks: list[dict[str, Any]] | None = None,
                   history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Calculate risk, evidence, weakest subject, intervention, and trend."""
    held = sum(int(row.get("classes_held", 0)) for row in records)
    attended = sum(int(row.get("classes_attended", 0)) for row in records)
    total_assignments = sum(int(row.get("assignments_total", 0)) for row in records)
    submitted = sum(int(row.get("assignments_submitted", 0)) for row in records)
    ct_max = sum(float(row.get("ct_max", 0)) for row in records)
    ct_marks = sum(float(row.get("ct_marks", 0)) for row in records)
    attendance = _percent(attended, held)
    assignments = _percent(submitted, total_assignments)
    ct = _percent(ct_marks, ct_max)
    pending_projects = sum(not bool(row.get("project_done", 1)) for row in records)
    score, reasons = 0, []
    if held and attendance < 65:
        score += 3
        reasons.append(f"Attendance {attendance:.0f}%, well below the 75% requirement")
    elif held and attendance < 75:
        score += 2
        reasons.append(f"Attendance {attendance:.0f}%, below the 75% requirement")
    elif held and attendance < 80:
        score += 1
        reasons.append(f"Attendance {attendance:.0f}%, close to the minimum")
    missing = max(0, total_assignments - submitted)
    if missing >= 3:
        score += 2
        reasons.append(f"{missing} assignments are still missing")
    elif missing:
        score += 1
        reasons.append(f"{missing} assignment(s) are still missing")
    if ct_max and ct < 40:
        score += 3
        reasons.append(f"Continuous assessment average is {ct:.0f}%")
    elif ct_max and ct < 60:
        score += 1
        reasons.append(f"Continuous assessment average is {ct:.0f}%")
    if pending_projects:
        score += min(2, pending_projects)
        reasons.append(f"{pending_projects} project(s) are not yet complete")
    if remarks and remarks[0].get("sentiment") == "negative":
        score += 1
        reasons.append("Latest teacher note indicates the student may need support")
    level = "High" if score >= 6 else "Medium" if score >= 3 else "Low"
    if not reasons:
        reasons.append("Current indicators are on track")
    weakest = min(records, key=lambda row: _percent(row.get("ct_marks", 0), row.get("ct_max", 0)) + _percent(row.get("classes_attended", 0), row.get("classes_held", 0)))["subject"] if records else "Not available"
    intervention = {
        "High": "Arrange a one-to-one meeting, extra classes, and a parent/guardian update.",
        "Medium": "Send a supportive check-in, connect a mentor, and offer a remedial class.",
        "Low": "Keep monitoring progress and encourage the student to maintain good habits.",
    }[level]
    trend = "Stable"
    if history and len(history) >= 2:
        ordered = sorted(history, key=lambda item: item.get("week", 0))
        change = float(ordered[-1].get("score", 0)) - float(ordered[-2].get("score", 0))
        trend = "Declining" if change > 0 else "Improving" if change < 0 else "Stable"
    return {
        "score": score, "level": level, "reasons": reasons, "attendance": attendance,
        "assignments": assignments, "ct_average": ct, "pending_projects": pending_projects,
        "weakest_subject": weakest, "intervention": intervention, "trend": trend,
    }


def leave_calculator(attended: int, held: int, required: float = 75.0) -> dict[str, int | float | bool]:
    """Calculate safe future absences or classes needed to recover."""
    if held < 0 or attended < 0 or attended > held or not 0 < required <= 100:
        raise ValueError("Attendance values and required percentage are invalid.")
    current = attended / held * 100 if held else 100.0
    can_miss = max(0, math.floor(attended / (required / 100) - held))
    needed = max(0, math.ceil((required * held - attended * 100) / (100 - required))) if current < required and required < 100 else 0
    return {"current": current, "classes_can_miss": can_miss if current >= required else 0, "classes_needed": needed, "below_requirement": current < required}


def what_if(attended: int, held: int, next_classes: int = 0, ct_marks: float = 0,
            ct_max: float = 100, next_ct_score: float | None = None) -> dict[str, Any]:
    """Compare attendance and assessment percentages before and after a scenario."""
    if min(attended, held, next_classes) < 0 or attended > held or ct_max <= 0:
        raise ValueError("Scenario values are invalid.")
    before_attendance = _percent(attended, held)
    after_attendance = _percent(attended + next_classes, held + next_classes)
    before_ct = _percent(ct_marks, ct_max)
    if next_ct_score is not None and not 0 <= next_ct_score <= 100:
        raise ValueError("Assessment score must be between 0 and 100.")
    after_ct = (before_ct + next_ct_score) / 2 if next_ct_score is not None else before_ct

    def level(attendance: float, assessment: float) -> str:
        """Return the overall risk band from attendance and assessment signals."""
        score = 3 if attendance < 65 else 2 if attendance < 75 else 1 if attendance < 80 else 0
        score += 3 if assessment < 40 else 1 if assessment < 60 else 0
        return "High" if score >= 6 else "Medium" if score >= 3 else "Low"

    return {
        "before_attendance": before_attendance, "after_attendance": after_attendance,
        "before_ct": before_ct, "after_ct": after_ct,
        "before_risk": level(before_attendance, before_ct),
        "after_risk": level(after_attendance, after_ct),
    }
