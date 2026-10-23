"""SQLite persistence with workspace-scoped data access."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parents[1] / "kavached.db"


def connect() -> sqlite3.Connection:
    """Open a row-aware database connection and ensure the schema exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    init_db(connection)
    return connection


def init_db(connection: sqlite3.Connection | None = None) -> None:
    """Create all application tables when they do not yet exist."""
    own_connection = connection is None
    db = connection or sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS workspaces (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, class_code TEXT UNIQUE NOT NULL,
            owner_user_id TEXT, created_on TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY, role TEXT NOT NULL CHECK(role IN ('teacher','student')),
            workspace_id TEXT NOT NULL, roll_no TEXT, name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, password_hash TEXT, salt TEXT,
            auth_provider TEXT DEFAULT 'password', failed_attempts INTEGER DEFAULT 0,
            locked_until TEXT, created_on TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, roll_no TEXT NOT NULL,
            name TEXT NOT NULL, section TEXT DEFAULT 'A',
            UNIQUE(workspace_id, roll_no)
        );
        CREATE TABLE IF NOT EXISTS subject_records (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, roll_no TEXT NOT NULL,
            subject TEXT NOT NULL, classes_held INTEGER DEFAULT 0,
            classes_attended INTEGER DEFAULT 0, assignments_total INTEGER DEFAULT 0,
            assignments_submitted INTEGER DEFAULT 0, ct_marks REAL DEFAULT 0,
            ct_max REAL DEFAULT 100, project_done INTEGER DEFAULT 1,
            UNIQUE(workspace_id, roll_no, subject)
        );
        CREATE TABLE IF NOT EXISTS attendance_history (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, roll_no TEXT NOT NULL,
            week INTEGER NOT NULL, attendance_pct REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS risk_history (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, roll_no TEXT NOT NULL,
            week INTEGER NOT NULL, score INTEGER NOT NULL, level TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS remarks (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, roll_no TEXT NOT NULL,
            remark TEXT NOT NULL, sentiment TEXT DEFAULT 'neutral',
            created_on TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS interventions (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, roll_no TEXT NOT NULL,
            action TEXT NOT NULL, status TEXT DEFAULT 'Planned',
            created_on TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, filename TEXT NOT NULL,
            content TEXT NOT NULL, uploaded_on TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chat_history (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, user_id TEXT NOT NULL,
            role TEXT NOT NULL, message TEXT NOT NULL, created_on TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chat_feedback (
            id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, user_id TEXT NOT NULL,
            question TEXT NOT NULL, rating INTEGER NOT NULL, created_on TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    db.commit()
    if own_connection:
        db.close()


def query(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    """Run a parameterized read query and return plain dictionaries."""
    with connect() as db:
        return [dict(row) for row in db.execute(sql, params).fetchall()]


def execute(sql: str, params: tuple[Any, ...] = ()) -> int:
    """Run one parameterized write and return its affected row count."""
    with connect() as db:
        cursor = db.execute(sql, params)
        db.commit()
        return cursor.rowcount


def new_id() -> str:
    """Return a unique identifier for a database row."""
    return str(uuid4())


def seed_demo() -> None:
    """Create the demo workspace and representative student records once."""
    from core.auth import hash_password

    with connect() as db:
        if db.execute("SELECT 1 FROM workspaces WHERE class_code = 'KVCH-DEMO'").fetchone():
            return
        workspace_id = new_id()
        teacher_id = new_id()
        db.execute(
            "INSERT INTO workspaces(id,name,class_code,owner_user_id) VALUES(?,?,?,?)",
            (workspace_id, "KavachED Demo College", "KVCH-DEMO", teacher_id),
        )
        teacher_hash, teacher_salt = hash_password("KavachDemo@26")
        db.execute(
            "INSERT INTO users(id,role,workspace_id,name,email,password_hash,salt) VALUES(?,?,?,?,?,?,?)",
            (teacher_id, "teacher", workspace_id, "Demo Teacher", "teacher.demo@kavached.app", teacher_hash, teacher_salt),
        )
        names = [
            "Aarav Sharma", "Ananya Patel", "Vivaan Singh", "Diya Iyer", "Aditya Kumar",
            "Ishita Reddy", "Arjun Nair", "Saanvi Gupta", "Reyansh Shah", "Aadhya Mehta",
            "Krishna Das", "Myra Joshi", "Kabir Verma", "Kiara Rao", "Atharv Jain",
            "Pari Malhotra", "Rudra Bose", "Navya Pillai", "Dhruv Kulkarni", "Sara Khan",
            "Yash Chawla", "Riya Menon", "Dev Mishra", "Tara Sinha", "Om Desai",
            "Anvi Kapoor", "Neil Thomas", "Mira Bhat", "Shaurya Roy", "Zoya Ali",
        ]
        subjects = ["Mathematics", "Physics", "Chemistry", "Programming", "English"]
        for index, name in enumerate(names):
            roll = f"CS{21001 + index}"
            section = "A" if index < 15 else "B"
            db.execute(
                "INSERT INTO students(id,workspace_id,roll_no,name,section) VALUES(?,?,?,?,?)",
                (new_id(), workspace_id, roll, name, section),
            )
            for subject_index, subject in enumerate(subjects):
                held = 40
                total = 8
                maximum = 50
                if index < 6:
                    attendance, submitted, marks, project_done = 20 + subject_index % 4, 2, 12, 0
                elif index < 17:
                    attendance = 29
                    submitted = 7 if subject_index == 0 else 8
                    marks, project_done = 25, 1
                else:
                    attendance, submitted, marks, project_done = 36, 8, 36, 1
                db.execute(
                    """INSERT INTO subject_records
                    (id,workspace_id,roll_no,subject,classes_held,classes_attended,
                     assignments_total,assignments_submitted,ct_marks,ct_max,project_done)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (new_id(), workspace_id, roll, subject, held, attendance, total, submitted, marks, maximum, project_done),
                )
            overall = max(48, min(98, 68 + ((index * 13) % 31)))
            for week in range(1, 9):
                delta = ((index % 5) - 2) * (week - 4) * 0.8
                pct = max(45, min(100, overall + delta))
                db.execute(
                    "INSERT INTO attendance_history(id,workspace_id,roll_no,week,attendance_pct) VALUES(?,?,?,?,?)",
                    (new_id(), workspace_id, roll, week, pct),
                )
                risk_score = 2 + (index % 6) + (2 if index == 13 and week > 5 else 0)
                risk_level = "High" if risk_score >= 6 else ("Medium" if risk_score >= 3 else "Low")
                db.execute(
                    "INSERT INTO risk_history(id,workspace_id,roll_no,week,score,level) VALUES(?,?,?,?,?,?)",
                    (new_id(), workspace_id, roll, week, risk_score, risk_level),
                )
        student_hash, student_salt = hash_password("KavachDemo@26")
        db.execute(
            "INSERT INTO users(id,role,workspace_id,roll_no,name,email,password_hash,salt) VALUES(?,?,?,?,?,?,?,?)",
            (new_id(), "student", workspace_id, "CS21014", "Demo Student", "student.demo@kavached.app", student_hash, student_salt),
        )
        db.execute(
            "INSERT INTO remarks(id,workspace_id,roll_no,remark,sentiment) VALUES(?,?,?,?,?)",
            (new_id(), workspace_id, "CS21014", "Aarav participates well but should build a consistent attendance routine.", "positive"),
        )
        for roll, action, status in [
            ("CS21014", "Weekly mentor check-in and attendance plan", "In progress"),
            ("CS21008", "Offer a programming practice session", "Planned"),
            ("CS21003", "Celebrate improved assignment completion", "Done"),
        ]:
            db.execute(
                "INSERT INTO interventions(id,workspace_id,roll_no,action,status) VALUES(?,?,?,?,?)",
                (new_id(), workspace_id, roll, action, status),
            )
        db.execute(
            "INSERT INTO documents(id,workspace_id,filename,content) VALUES(?,?,?,?)",
            (new_id(), workspace_id, "attendance_policy.txt", "Students should maintain at least 75% attendance in each subject. Students below this requirement should speak with their class mentor early. Approved leave may require supporting documentation."),
        )
        db.execute(
            "INSERT INTO documents(id,workspace_id,filename,content) VALUES(?,?,?,?)",
            (new_id(), workspace_id, "exam_rules.txt", "Continuous assessment contributes to the final course evaluation. Submit assignments by the announced deadline and contact the instructor promptly if you need academic support."),
        )
        db.commit()
