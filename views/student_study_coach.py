"""Student Study Coach content, fallbacks, and rendering."""

from __future__ import annotations

import csv
import html
import io
import json
import re
from typing import Any

import streamlit as st

from core.ai import answer_with_context
from ui.components import hero

_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_STUDY_HOURS = (2, 1.5, 1.5, 1, 1, 0.5)
_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?%?")
_DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097f]")
_TIME_OF_DAY_PATTERN = re.compile(r"\b(?:morning|afternoon|evening|night|subah|dopahar|shaam|raat)\b", re.IGNORECASE)


def _percentage(numerator: float, denominator: float) -> float:
    return numerator / denominator * 100 if denominator else 0.0


def _format_metric(row: dict[str, Any], kind: str) -> tuple[str, float]:
    if kind == "attendance":
        numerator, denominator = row["classes_attended"], row["classes_held"]
        return f"{numerator}/{denominator} classes ({_percentage(numerator, denominator):.0f}%)", _percentage(numerator, denominator)
    if kind == "assignments":
        numerator, denominator = row["assignments_submitted"], row["assignments_total"]
        return f"{numerator}/{denominator} assignments ({_percentage(numerator, denominator):.0f}%)", _percentage(numerator, denominator)
    numerator, denominator = row["ct_marks"], row["ct_max"]
    return f"{numerator:.0f}/{denominator:.0f} ({_percentage(numerator, denominator):.0f}%)", _percentage(numerator, denominator)


def _signals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    signals = []
    for row in records:
        for kind in ("attendance", "assignments", "ct"):
            value, percentage = _format_metric(row, kind)
            label = {"attendance": "attendance", "assignments": "assignments", "ct": "class test"}[kind]
            signals.append(
                {
                    "subject": row["subject"],
                    "kind": kind,
                    "label": label,
                    "metric": value,
                    "percentage": percentage,
                }
            )
    return signals


def _reason(signal: dict[str, Any], strength: bool, language: str) -> str:
    label, metric = signal["label"], signal["metric"]
    if language == "Hinglish":
        if strength:
            return f"{metric} ka record dikhata hai ki {label} yahan ek steady signal hai; is habit ko continue karna helpful rahega."
        if signal["kind"] == "assignments":
            return f"{metric} ka matlab hai ki is subject mein assignment completion par dhyan dena zaroori hai."
        if signal["kind"] == "attendance":
            return f"{metric} regular classes attend karne ki zaroorat dikhata hai, taaki class ka flow bana rahe."
        return f"{metric} batata hai ki class-test ke topics ko dobara revise karna useful hoga."
    if strength:
        return f"The recorded {label} result is a steady signal here; keeping this habit consistent can support continued progress."
    if signal["kind"] == "assignments":
        return f"This recorded result shows that assignment completion in this subject needs attention."
    if signal["kind"] == "attendance":
        return f"This recorded result makes regular class attendance an important next step for continuity."
    return f"This recorded class-test result makes another focused revision useful."


def _task(row: dict[str, Any], language: str) -> str:
    assignments, total = row["assignments_submitted"], row["assignments_total"]
    attendance, held = row["classes_attended"], row["classes_held"]
    ct, maximum = row["ct_marks"], row["ct_max"]
    if total and assignments < total:
        if language == "Hinglish":
            return f"{row['subject']} ka pending assignment complete karo; abhi {assignments}/{total} submit hua hai."
        return f"Complete the pending {row['subject']} assignment; the record currently shows {assignments}/{total} submitted."
    if held and attendance / held < 0.75:
        if language == "Hinglish":
            return f"{row['subject']} ke missed-class notes revise karo; attendance abhi {attendance}/{held} classes hai."
        return f"Review notes for missed {row['subject']} classes; attendance currently stands at {attendance}/{held} classes."
    if language == "Hinglish":
        return f"{row['subject']} ke class-test topics dobara practice karo; recorded score {ct:.0f}/{maximum:.0f} hai."
    return f"Rework the {row['subject']} class-test topics; the recorded score is {ct:.0f}/{maximum:.0f}."


def _fallback(
    action: str,
    language: str,
    records: list[dict[str, Any]],
    assessment: dict[str, Any],
) -> dict[str, Any]:
    signals = _signals(records)
    strongest = [
        max((item for item in signals if item["kind"] == kind), key=lambda item: (item["percentage"], item["subject"]))
        for kind in ("assignments", "ct")
    ]
    weakest = [
        min((item for item in signals if item["kind"] == kind), key=lambda item: (item["percentage"], item["subject"]))
        for kind in ("assignments", "attendance", "ct")
    ]
    weakest_first = sorted(
        records,
        key=lambda row: (
            -sum(100 - signal["percentage"] for signal in signals if signal["subject"] == row["subject"]),
            row["subject"],
        ),
    )
    attendance = f"{assessment['attendance']:.0f}%"
    assignments = f"{assessment['assignments']:.0f}%"
    ct_average = f"{assessment['ct_average']:.0f}%"
    first_signal = weakest[0]
    first_row = next(row for row in records if row["subject"] == first_signal["subject"])
    assignment_signal = min(
        (signal for signal in signals if signal["kind"] == "assignments"),
        key=lambda item: (item["percentage"], item["subject"]),
    )
    ct_signal = min(
        (signal for signal in signals if signal["kind"] == "ct"),
        key=lambda item: (item["percentage"], item["subject"]),
    )
    attendance_signal = min(
        (signal for signal in signals if signal["kind"] == "attendance"),
        key=lambda item: (item["percentage"], item["subject"]),
    )
    assignment_row = next(row for row in records if row["subject"] == assignment_signal["subject"])
    has_pending_assignment = assignment_row["assignments_submitted"] < assignment_row["assignments_total"]

    if language == "Hinglish":
        summary = [
            f"Overview ke current records mein attendance {attendance}, assignments {assignments}, aur CT average {ct_average} hai.",
            f"{first_signal['subject']} pehle focus maangta hai kyunki iska recorded {first_signal['label']} result {first_signal['metric']} hai.",
            f"Sabse strong recorded signal {strongest[0]['subject']} ka {strongest[0]['label']} hai: {strongest[0]['metric']}; is consistency ko continue rakho.",
        ]
        focus_first = (
            f"Pehle {first_signal['subject']} par kaam karo: {first_signal['metric']} ko dekhte hue "
            f"{_task(first_row, language)} Phir overall attendance {attendance} ko support karne ke liye regular classes attend karo."
        )
        tips = [
            {
                "title": "Attendance ko steady rakho",
                "sentences": [
                    f"Is hafte scheduled classes attend karo; Overview mein tumhari attendance {attendance} hai.",
                    f"{attendance_signal['subject']} ka record {attendance_signal['metric']} dikhata hai ki regular class se continuity banegi.",
                ],
            },
            {
                "title": "Assignments complete karo",
                "sentences": [
                    f"{assignment_signal['subject']} se start karo; abhi {assignment_signal['metric']} recorded hai.",
                    "Pending submission ko finish karne se subject ka assignment record complete ho sakta hai."
                    if has_pending_assignment
                    else "Har assigned submission waqt par karke is subject ka completion record maintain karo.",
                ],
            },
            {
                "title": "Class tests se seekho",
                "sentences": [
                    f"{ct_signal['subject']} ke class test ka recorded score {ct_signal['metric']} hai.",
                    "Galat hue concepts par dobara practice karo, taaki agle test ke liye samajh clear ho.",
                ],
            },
            {
                "title": "Revision ko regular banao",
                "sentences": [
                    f"{weakest[0]['subject']} mein {weakest[0]['metric']} ek focused revision session ko useful banata hai.",
                    "Notes band karke key ideas recall karo, phir apne class-test questions se understanding check karo.",
                ],
            },
            {
                "title": "Teacher se jaldi poochho",
                "sentences": [
                    f"{ct_signal['subject']} ke {ct_signal['metric']} wale class test mein jo topic unclear tha, uske baare mein teacher se poochho.",
                    "Specific doubt share karne se teacher tumhe sahi explanation ya practice de paayenge.",
                ],
            },
            {
                "title": "Time ko plan karke use karo",
                "sentences": [
                    f"Monday ko {weakest_first[0]['subject']} ke liye { _STUDY_HOURS[0] } hours rakho; iska recorded {weakest[0]['label']} result {weakest[0]['metric']} hai.",
                    "Short focused sessions rakho aur Sunday ko padhai se break lo.",
                ],
            },
        ]
        plan_logic = [
            f"Sabse pehle un subjects ko rakha hai jahan recorded gaps zyada hain; {weakest_first[0]['subject']} ka {first_signal['metric']} ise pehle laata hai.",
            "Lambe sessions shuru mein hain, jab focus fresh hota hai; baad ke sessions baaki subjects ko cover karte hain.",
            "Saturday ka session chhota hai aur Sunday poora rest day hai, bina study hours ke.",
            f"Is plan mein total {sum(_STUDY_HOURS)} weekly study hours hain, taaki padhai aur recovery dono balance rahein.",
        ]
    else:
        summary = [
            f"Your current Overview shows attendance at {attendance}, assignment completion at {assignments}, and CT average at {ct_average}.",
            f"{first_signal['subject']} needs the first focus because its recorded {first_signal['label']} result is {first_signal['metric']}.",
            f"The strongest recorded signal is {strongest[0]['subject']} {strongest[0]['label']}: {strongest[0]['metric']}; keep that consistency going.",
        ]
        focus_first = (
            f"Start with {first_signal['subject']}: its {first_signal['metric']} makes it the clearest first step. "
            f"{_task(first_row, language)} Then attend regularly to support the overall attendance result of {attendance}."
        )
        tips = [
            {
                "title": "Keep attendance steady",
                "sentences": [
                    f"Attend your scheduled classes this week; your Overview attendance is {attendance}.",
                    f"{attendance_signal['subject']} is recorded at {attendance_signal['metric']}, so regular attendance can help maintain continuity.",
                ],
            },
            {
                "title": "Finish pending assignments",
                "sentences": [
                    f"Start with {assignment_signal['subject']}, where the record currently shows {assignment_signal['metric']}.",
                    "Completing the pending submission can bring that subject's assignment record up to date."
                    if has_pending_assignment
                    else "Submit assigned work on time to maintain this subject's recorded completion.",
                ],
            },
            {
                "title": "Learn from class tests",
                "sentences": [
                    f"The recorded class-test score in {ct_signal['subject']} is {ct_signal['metric']}.",
                    "Review the concepts behind missed questions and practise them again before the next test.",
                ],
            },
            {
                "title": "Make revision regular",
                "sentences": [
                    f"The {weakest[0]['metric']} result in {weakest[0]['subject']} makes a focused revision session useful.",
                    "Recall key ideas without looking at your notes, then check your understanding against class-test topics.",
                ],
            },
            {
                "title": "Ask your teacher early",
                "sentences": [
                    f"Ask about any unclear topic from the {ct_signal['subject']} class test recorded at {ct_signal['metric']}.",
                    "Sharing the specific doubt helps your teacher point you to the right explanation or practice.",
                ],
            },
            {
                "title": "Plan your time",
                "sentences": [
                    f"Reserve {_STUDY_HOURS[0]} hours on Monday for {weakest_first[0]['subject']}; its recorded {weakest[0]['label']} result is {weakest[0]['metric']}.",
                    "Use focused sessions and keep Sunday free from study.",
                ],
            },
        ]
        plan_logic = [
            f"The subjects with the largest recorded gaps come first; {weakest_first[0]['subject']} leads because its result is {first_signal['metric']}.",
            "Longer sessions are placed earlier, when focus is fresh, and later sessions spread practice across the remaining subjects.",
            "Saturday is a shorter consolidation session, and Sunday is a full rest day with no study hours.",
            f"The plan totals {sum(_STUDY_HOURS)} study hours for the week while leaving room for recovery.",
        ]

    if action == "Analyze strengths and weaknesses":
        return {
            "summary": summary,
            "strengths": [
                {"subject": item["subject"], "metric": item["metric"], "reason": _reason(item, True, language)}
                for item in strongest
            ],
            "weaknesses": [
                {"subject": item["subject"], "metric": item["metric"], "reason": _reason(item, False, language)}
                for item in weakest
            ],
            "focus_first": focus_first,
        }
    if action == "Tips to improve":
        return {"tips": tips}

    days = []
    for index, day in enumerate(_DAYS):
        if day == "Sun":
            subject = "Rest"
            hours = "Rest"
            task = "Full rest day; no study planned." if language == "English" else "Poora rest day; padhai plan nahi hai."
        else:
            row = weakest_first[(index) % len(weakest_first)]
            subject = row["subject"]
            hours = _STUDY_HOURS[index]
            task = _task(row, language)
        days.append({"day": day, "subject": subject, "hours": hours, "task": task})
    return {
        "days": days,
        "logic": plan_logic,
        "total_hours": sum(_STUDY_HOURS),
    }


def _same_shape_and_facts(
    candidate: Any,
    template: Any,
    language: str,
    field: str | None = None,
    subjects: tuple[str, ...] = (),
) -> bool:
    if isinstance(template, dict):
        return (
            isinstance(candidate, dict)
            and candidate.keys() == template.keys()
            and all(
                _same_shape_and_facts(candidate[key], value, language, key, subjects)
                for key, value in template.items()
            )
        )
    if isinstance(template, list):
        return (
            isinstance(candidate, list)
            and len(candidate) == len(template)
            and all(
                _same_shape_and_facts(value, expected, language, field, subjects)
                for value, expected in zip(candidate, template)
            )
        )
    if isinstance(template, (int, float)):
        return type(candidate) in (int, float) and candidate == template
    if isinstance(template, str):
        if not isinstance(candidate, str):
            return False
        if language == "Hinglish" and _DEVANAGARI_PATTERN.search(candidate):
            return False
        if field in {"subject", "metric", "day"} and candidate != template:
            return False
        if _TIME_OF_DAY_PATTERN.search(candidate) and not _TIME_OF_DAY_PATTERN.search(template):
            return False
        for subject in subjects:
            if any(
                matched != subject
                for matched in re.findall(rf"(?<!\w){re.escape(subject)}(?!\w)", candidate, re.IGNORECASE)
            ):
                return False
        return sorted(_NUMBER_PATTERN.findall(candidate)) == sorted(_NUMBER_PATTERN.findall(template))
    return candidate == template


def _parse_ai_content(raw: str, template: dict[str, Any], language: str) -> dict[str, Any] | None:
    content = raw.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE)
    try:
        candidate = json.loads(content)
    except json.JSONDecodeError:
        return None
    def collect_subjects(value: Any) -> set[str]:
        if isinstance(value, dict):
            found = set()
            for key, child in value.items():
                if key == "subject" and isinstance(child, str) and child != "Rest":
                    found.add(child)
                else:
                    found.update(collect_subjects(child))
            return found
        if isinstance(value, list):
            found = set()
            for child in value:
                found.update(collect_subjects(child))
            return found
        return set()

    subjects = tuple(collect_subjects(template))
    if not _same_shape_and_facts(candidate, template, language, subjects=subjects):
        return None
    if "summary" in candidate:
        if not 2 <= len(candidate["summary"]) <= 3:
            return None
        if not 2 <= len(candidate["strengths"]) <= 3 or not 2 <= len(candidate["weaknesses"]) <= 3:
            return None
    if "tips" in candidate and (
        not 5 <= len(candidate["tips"]) <= 6
        or any(not 2 <= len(tip["sentences"]) <= 3 for tip in candidate["tips"])
    ):
        return None
    if "days" in candidate:
        if [day["day"] for day in candidate["days"]] != list(_DAYS):
            return None
        if not 3 <= len(candidate["logic"]) <= 4:
            return None
        if any(not 0.5 <= day["hours"] <= 2 for day in candidate["days"][:-1]):
            return None
        if candidate["days"][-1]["subject"] != "Rest" or candidate["days"][-1]["hours"] != "Rest":
            return None
        if sum(day["hours"] for day in candidate["days"][:-1]) != candidate["total_hours"]:
            return None
    return candidate


def _cache_key(
    user: dict[str, Any],
    student: dict[str, Any],
    records: list[dict[str, Any]],
    assessment: dict[str, Any],
    action: str,
    language: str,
) -> tuple[Any, ...]:
    values = tuple(
        tuple(
            row[field]
            for field in (
                "subject",
                "classes_attended",
                "classes_held",
                "assignments_submitted",
                "assignments_total",
                "ct_marks",
                "ct_max",
            )
        )
        for row in records
    )
    return (
        user["workspace_id"],
        student["roll_no"],
        action,
        language,
        values,
        assessment["attendance"],
        assessment["assignments"],
        assessment["ct_average"],
    )


def _render_analysis(content: dict[str, Any], language: str) -> None:
    with st.container(border=True):
        st.markdown("**Summary**")
        for sentence in content["summary"]:
            st.markdown(sentence)
    left, right = st.columns(2)
    with left:
        st.markdown('<div class="coach-side coach-strength"><strong>Strengths</strong></div>', unsafe_allow_html=True)
        for item in content["strengths"]:
            st.markdown(f"**{html.escape(item['subject'])} · {html.escape(item['metric'])}**")
            st.markdown(item["reason"])
    with right:
        st.markdown('<div class="coach-side coach-weakness"><strong>Weaknesses</strong></div>', unsafe_allow_html=True)
        for item in content["weaknesses"]:
            st.markdown(f"**{html.escape(item['subject'])} · {html.escape(item['metric'])}**")
            st.markdown(item["reason"])
    st.markdown(f"**{'Pehle yahan focus karo' if language == 'Hinglish' else 'Focus first'}**")
    st.markdown(content["focus_first"])


def _render_tips(content: dict[str, Any]) -> None:
    for tip in content["tips"]:
        st.markdown(f"**{html.escape(tip['title'])}**")
        for sentence in tip["sentences"]:
            st.markdown(sentence)


def _inject_coach_styles() -> None:
    st.markdown(
        """
        <style>
        .coach-side {
            padding: .8rem 1rem;
            margin: .25rem 0 .75rem;
            border: 1px solid var(--border);
            border-left-width: 4px;
            border-radius: 12px;
            background: var(--surface);
            color: var(--text);
        }
        .coach-strength { border-left-color: var(--success-text); }
        .coach-weakness { border-left-color: var(--warning); }
        .coach-plan-table {
            width: 100%;
            border-collapse: collapse;
            background: var(--surface);
            color: var(--text);
        }
        .coach-plan-table th, .coach-plan-table td {
            padding: .65rem;
            border: 1px solid var(--border);
            text-align: left;
            background: var(--surface);
            color: var(--text);
        }
        .coach-plan-table th { background: var(--surface-2); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_plan(content: dict[str, Any], language: str) -> None:
    headers = ("Day", "Subject", "Hours", "Specific Task")
    rows = "".join(
        "<tr>"
        + "".join(f"<td>{html.escape(str(day[key]))}</td>" for key in ("day", "subject", "hours", "task"))
        + "</tr>"
        for day in content["days"]
    )
    st.markdown(
        f"""
        <table class="coach-plan-table">
            <thead><tr>{"".join(f"<th>{html.escape(label)}</th>" for label in headers)}</tr></thead>
            <tbody>{rows}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
    for sentence in content["logic"]:
        st.markdown(sentence)
    hours_label = "Total weekly study hours" if language == "English" else "Hafte ke total study hours"
    st.markdown(f"**{hours_label}: {content['total_hours']}**")
    csv_file = io.StringIO()
    writer = csv.DictWriter(csv_file, fieldnames=("Day", "Subject", "Hours", "Specific Task"))
    writer.writeheader()
    for day in content["days"]:
        writer.writerow(
            {
                "Day": day["day"],
                "Subject": day["subject"],
                "Hours": day["hours"],
                "Specific Task": day["task"],
            }
        )
    st.download_button(
        "Download weekly plan",
        csv_file.getvalue(),
        "my-study-plan.csv",
        "text/csv",
    )


def render_study_coach(
    user: dict[str, Any],
    student: dict[str, Any] | None,
    records: list[dict[str, Any]],
    assessment: dict[str, Any],
) -> None:
    """Render language-specific study guidance from a student's recorded metrics."""
    _inject_coach_styles()
    hero("Study Coach", "Turn your current learning signals into a small, realistic plan.")
    if not student:
        st.info("Your student profile is not linked yet. Once your teacher connects your profile, your study guidance will appear here.")
        return
    if not records:
        st.info("There are no subject records yet, so there is nothing to catch up on. Your personalized plan will appear as soon as your teacher adds your records.")
        return

    language = st.radio("Language", ["English", "Hinglish"], horizontal=True)
    st.session_state.language = language
    action = st.radio(
        "What would help today?",
        ["Analyze strengths and weaknesses", "Tips to improve", "Weekly study plan"],
        horizontal=True,
    )
    cache_key = _cache_key(user, student, records, assessment, action, language)
    cache = st.session_state.setdefault("_study_coach_cache", {})
    if st.button("Build my plan", type="primary"):
        fallback = _fallback(action, language, records, assessment)
        context = json.dumps(
            {
                "student_records": records,
                "overview_metrics": {
                    "attendance": f"{assessment['attendance']:.0f}%",
                    "assignments": f"{assessment['assignments']:.0f}%",
                    "ct_average": f"{assessment['ct_average']:.0f}%",
                },
                "required_output": fallback,
            },
            ensure_ascii=False,
        )
        question = (
            f"Return only valid JSON. Copy required_output exactly, then rewrite only explanatory text in {language}. "
            "Keep every key, array length, subject, metric, weekday, number, and planned hour exactly unchanged. "
            "Do not add facts, figures, time-of-day references, markdown fences, or text outside the JSON."
        )
        with st.spinner("Building guidance from your records..."):
            raw, call_succeeded = answer_with_context(question, context, language)
        st.session_state["kavach_ai_online"] = call_succeeded
        ai_content = _parse_ai_content(raw, fallback, language) if call_succeeded else None
        cache[cache_key] = {
            "content": ai_content or fallback,
            "generated_by_ai": ai_content is not None,
            "ai_online": call_succeeded,
        }

    result = cache.get(cache_key)
    if not result:
        return
    st.caption(
        ("Generated by AI" if result["generated_by_ai"] else "Generated from your records (rule-based)")
        + (" · AI online" if result["ai_online"] else "")
    )
    if action == "Analyze strengths and weaknesses":
        _render_analysis(result["content"], language)
    elif action == "Tips to improve":
        _render_tips(result["content"])
    else:
        _render_plan(result["content"], language)
