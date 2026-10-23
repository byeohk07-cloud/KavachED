"""Account registration, password hashing, and login protection."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from core import db

ITERATIONS = 120_000


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """Hash a password with a per-user random salt."""
    salt_value = salt or secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_value), ITERATIONS).hex()
    return hashed, salt_value


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Compare a password hash without leaking timing information."""
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, password_hash)


def register_teacher(name: str, email: str, college: str, password: str | None,
                     auth_provider: str = "password") -> tuple[dict, str]:
    """Create a new teacher and an isolated workspace."""
    code = "KV" + secrets.token_hex(3).upper()
    workspace_id, user_id = db.new_id(), db.new_id()
    password_hash, salt = hash_password(password) if password else (None, None)
    with db.connect() as connection:
        connection.execute(
            "INSERT INTO workspaces(id,name,class_code,owner_user_id) VALUES(?,?,?,?)",
            (workspace_id, college.strip(), code, user_id),
        )
        connection.execute(
            """INSERT INTO users(id,role,workspace_id,name,email,password_hash,salt,auth_provider)
            VALUES(?,?,?,?,?,?,?,?)""",
            (user_id, "teacher", workspace_id, name.strip(), email.strip().lower(), password_hash, salt, auth_provider),
        )
        connection.commit()
    return {"id": user_id, "role": "teacher", "workspace_id": workspace_id, "name": name.strip(), "email": email.strip().lower()}, code


def register_student(name: str, email: str, roll_no: str, class_code: str, password: str | None,
                     auth_provider: str = "password") -> dict:
    """Join a student to the workspace that owns the supplied class code."""
    workspaces = db.query("SELECT id FROM workspaces WHERE class_code = ?", (class_code.strip().upper(),))
    if not workspaces:
        raise ValueError("Class code not found. Ask your teacher.")
    workspace_id = workspaces[0]["id"]
    roll = roll_no.strip().upper()
    password_hash, salt = hash_password(password) if password else (None, None)
    user_id = db.new_id()
    with db.connect() as connection:
        roster = connection.execute(
            "SELECT id FROM students WHERE workspace_id=? AND roll_no=?", (workspace_id, roll)
        ).fetchone()
        if not roster:
            connection.execute(
                "INSERT INTO students(id,workspace_id,roll_no,name,section) VALUES(?,?,?,?,?)",
                (db.new_id(), workspace_id, roll, name.strip(), "A"),
            )
        connection.execute(
            """INSERT INTO users(id,role,workspace_id,roll_no,name,email,password_hash,salt,auth_provider)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (user_id, "student", workspace_id, roll, name.strip(), email.strip().lower(), password_hash, salt, auth_provider),
        )
        connection.commit()
    return {"id": user_id, "role": "student", "workspace_id": workspace_id, "roll_no": roll, "name": name.strip(), "email": email.strip().lower()}


def login(identifier: str, password: str, role: str) -> dict | None:
    """Authenticate a user while enforcing a five-attempt temporary lockout."""
    email = identifier.strip().lower()
    if role == "student":
        matches = db.query(
            "SELECT * FROM users WHERE role=? AND (lower(email)=? OR upper(roll_no)=?)",
            (role, email, identifier.strip().upper()),
        )
    else:
        matches = db.query("SELECT * FROM users WHERE role=? AND lower(email)=?", (role, email))
    if not matches:
        hash_password(password, "0" * 32)
        return None
    user = matches[0]
    now = datetime.now(timezone.utc)
    if user["locked_until"]:
        locked_until = datetime.fromisoformat(user["locked_until"])
        if locked_until > now:
            return None
        db.execute("UPDATE users SET failed_attempts=0,locked_until=NULL WHERE id=?", (user["id"],))
    if user["password_hash"] and verify_password(password, user["password_hash"], user["salt"]):
        db.execute("UPDATE users SET failed_attempts=0,locked_until=NULL WHERE id=?", (user["id"],))
        return {key: user[key] for key in ("id", "role", "workspace_id", "roll_no", "name", "email")}
    failed = int(user["failed_attempts"] or 0) + 1
    locked = (now + timedelta(minutes=5)).isoformat() if failed >= 5 else None
    db.execute("UPDATE users SET failed_attempts=?,locked_until=? WHERE id=?", (failed, locked, user["id"]))
    return None


def valid_password(password: str) -> bool:
    """Check the required minimum length, letter, and digit."""
    return len(password) >= 8 and any(char.isalpha() for char in password) and any(char.isdigit() for char in password)
