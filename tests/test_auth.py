import pytest

from core import db
from core.auth import login, register_student, register_teacher, valid_password
from core.risk import assess_student


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    yield


def test_teacher_student_registration_and_authentication(isolated_db):
    teacher, code = register_teacher("Teacher Example", "teacher@example.com", "Sample College", "StrongPass9")
    assert login("teacher@example.com", "StrongPass9", "teacher")["id"] == teacher["id"]
    student = register_student("Student Example", "student@example.com", "cs1", code, "StrongPass9")
    assert login("CS1", "StrongPass9", "student")["id"] == student["id"]
    assert db.query("SELECT roll_no FROM students WHERE workspace_id=?", (teacher["workspace_id"],))[0]["roll_no"] == "CS1"


def test_student_rejects_unknown_class_code(isolated_db):
    with pytest.raises(ValueError, match="Class code not found"):
        register_student("New Student", "new@example.com", "r1", "UNKNOWN", "StrongPass9")


def test_five_failed_attempts_lock_account(isolated_db):
    register_teacher("Teacher", "locked@example.com", "College", "StrongPass9")
    for _ in range(5):
        assert login("locked@example.com", "wrongpass8", "teacher") is None
    user = db.query("SELECT failed_attempts,locked_until FROM users WHERE email=?", ("locked@example.com",))[0]
    assert user["failed_attempts"] == 5
    assert user["locked_until"]
    assert login("locked@example.com", "StrongPass9", "teacher") is None


def test_password_rules():
    assert valid_password("Abcdefg1")
    assert not valid_password("short1")
    assert not valid_password("onlyletters")


def test_demo_seed_is_idempotent_and_has_balanced_risk_levels(isolated_db):
    db.seed_demo()
    db.seed_demo()
    workspace_id = db.query("SELECT id FROM workspaces WHERE class_code='KVCH-DEMO'")[0]["id"]
    students = db.query("SELECT roll_no FROM students WHERE workspace_id=?", (workspace_id,))
    assert len(students) == 30
    distribution = {"High": 0, "Medium": 0, "Low": 0}
    for student in students:
        records = db.query(
            "SELECT * FROM subject_records WHERE workspace_id=? AND roll_no=?",
            (workspace_id, student["roll_no"]),
        )
        distribution[assess_student(records)["level"]] += 1
    assert distribution == {"High": 6, "Medium": 11, "Low": 13}
