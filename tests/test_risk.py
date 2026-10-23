from core.risk import assess_student, leave_calculator, what_if


def test_high_risk_has_plain_language_reasons():
    result = assess_student([{
        "subject": "Maths", "classes_held": 20, "classes_attended": 12,
        "assignments_total": 5, "assignments_submitted": 1,
        "ct_marks": 15, "ct_max": 50, "project_done": 0,
    }])
    assert result["level"] == "High"
    assert result["score"] >= 6
    assert result["reasons"]
    assert result["weakest_subject"] == "Maths"


def test_low_risk_and_empty_records_are_safe():
    assert assess_student([])["level"] == "Low"
    result = assess_student([{
        "subject": "English", "classes_held": 20, "classes_attended": 19,
        "assignments_total": 4, "assignments_submitted": 4,
        "ct_marks": 45, "ct_max": 50, "project_done": 1,
    }])
    assert result["level"] == "Low"
    assert result["attendance"] == 95


def test_leave_calculator_handles_recovery_and_safe_absences():
    safe = leave_calculator(16, 20)
    assert safe["classes_can_miss"] == 1
    recovery = leave_calculator(12, 20)
    assert recovery["classes_needed"] == 12
    assert recovery["below_requirement"] is True


def test_what_if_improves_attendance_and_ct():
    result = what_if(50, 100, next_classes=60, ct_marks=30, ct_max=50, next_ct_score=80)
    assert result["after_attendance"] > result["before_attendance"]
    assert result["after_ct"] > result["before_ct"]
    assert result["after_risk"] != result["before_risk"]


def test_invalid_attendance_raises():
    try:
        leave_calculator(5, 4)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid attendance should be rejected")
