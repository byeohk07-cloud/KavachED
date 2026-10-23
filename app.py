"""KavachED: AI-powered student success and early intervention platform."""

from __future__ import annotations

import base64
import html
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from pypdf.errors import PdfReadError

from core import db
from core.ai import answer_with_context
from core.auth import login, register_student, register_teacher, valid_password
from core.charts import attendance_line, risk_donut, template
from core.rag import retrieve
from core.risk import assess_student, leave_calculator, what_if
from ui.theme import inject_theme
from ui.components import hero, render_theme_toggle
from views.student_study_coach import render_study_coach as render_student_study_coach

st.set_page_config(page_title="KavachED | Student success", page_icon="assets/favicon.png", layout="wide", initial_sidebar_state="expanded")
st.session_state.setdefault("theme", "dark")
st.session_state.setdefault("user", None)
st.session_state.setdefault("selected_roll", "CS21014")
st.session_state.setdefault("theme", "dark")
inject_theme(st.session_state["theme"])
db.seed_demo()

TEACHER_PAGES = ["Overview", "Students", "Student 360", "Interventions", "Data Studio", "Knowledge Base", "Ask KavachED", "Settings"]
STUDENT_PAGES = ["My Overview", "My Subjects", "Study Coach", "What-If & Goals", "Ask KavachED", "Settings"]


def scoped_students(user: dict) -> list[dict]:
    """Load the current teacher's roster or only the student's own record."""
    if user["role"] == "student":
        return db.query("SELECT * FROM students WHERE workspace_id=? AND roll_no=?", (user["workspace_id"], user["roll_no"]))
    return db.query("SELECT * FROM students WHERE workspace_id=? ORDER BY name", (user["workspace_id"],))


def student_records(user: dict, roll: str) -> list[dict]:
    """Load subject records only within this account's workspace and access scope."""
    if user["role"] == "student" and roll != user["roll_no"]:
        return []
    return db.query(
        "SELECT * FROM subject_records WHERE workspace_id=? AND roll_no=? ORDER BY subject",
        (user["workspace_id"], roll),
    )


def student_assessment(user: dict, student: dict) -> dict:
    """Return the risk result for one authorized student."""
    roll = student["roll_no"]
    remarks = db.query(
        "SELECT * FROM remarks WHERE workspace_id=? AND roll_no=? ORDER BY created_on DESC LIMIT 1",
        (user["workspace_id"], roll),
    )
    history = db.query(
        "SELECT week,score,level FROM risk_history WHERE workspace_id=? AND roll_no=? ORDER BY week",
        (user["workspace_id"], roll),
    )
    return assess_student(student_records(user, roll), remarks, history)


def set_user(user: dict) -> None:
    """Store the authenticated user's minimal profile in the session."""
    st.session_state.user = user
    st.session_state.page = "Overview" if user["role"] == "teacher" else "My Overview"


def logout() -> None:
    """Clear the app session and the optional Streamlit OAuth session."""
    st.session_state.user = None
    if google_identity() and hasattr(st, "logout"):
        st.logout()
    st.rerun()


def google_identity() -> dict | None:
    """Return the identity established by Streamlit's configured OAuth provider."""
    if not hasattr(st, "user"):
        return None
    try:
        if not st.user.is_logged_in:
            return None
        return {"name": st.user.name or st.user.email.split("@")[0], "email": st.user.email.lower()}
    except (AttributeError, KeyError):
        return None


def google_auth_configured() -> bool:
    """Check OAuth only when a Streamlit secrets file is present."""
    secret_paths = [
        Path.cwd() / ".streamlit" / "secrets.toml",
        Path.home() / ".streamlit" / "secrets.toml",
    ]
    if not any(path.is_file() for path in secret_paths):
        return False
    try:
        auth = st.secrets.get("auth", {})
        return bool(auth.get("client_id") and auth.get("client_secret") and auth.get("redirect_uri"))
    except (AttributeError, KeyError):
        return False


def render_google_profile(identity: dict) -> None:
    """Complete a first-time Google profile without linking an existing password account."""
    existing = db.query("SELECT * FROM users WHERE lower(email)=?", (identity["email"],))
    if existing and existing[0]["auth_provider"] == "google":
        set_user({key: existing[0][key] for key in ("id", "role", "workspace_id", "roll_no", "name", "email")})
        st.rerun()
    st.subheader("Complete your profile")
    st.caption(f"Signed in as {identity['email']}. Choose how you will use KavachED.")
    role = st.radio("I am a", ["Student", "Teacher"], horizontal=True)
    with st.form("google_profile"):
        name = st.text_input("Full name", value=identity["name"])
        if role == "Student":
            roll = st.text_input("Roll number")
            code = st.text_input("Class code")
            college = ""
        else:
            college = st.text_input("College or institute name")
            roll, code = "", ""
        submit = st.form_submit_button("Finish profile", type="primary")
    if submit:
        if existing:
            st.error("This email already has a password account. Sign in with your password instead.")
            return
        try:
            if role == "Teacher":
                if not college.strip():
                    st.error("Enter your college or institute name.")
                    return
                user, code = register_teacher(name, identity["email"], college, None, "google")
                st.success(f"Workspace created. Your class code is **{code}** — share it with students.")
            else:
                if not roll.strip() or not code.strip():
                    st.error("Enter your roll number and class code.")
                    return
                user = register_student(name, identity["email"], roll, code, None, "google")
            set_user(user)
            st.rerun()
        except ValueError as error:
            st.error(str(error))


def render_landing() -> None:
    """Render the product landing page and account access forms."""
    spacer, theme_control = st.columns([10, 1])
    with theme_control:
        render_theme_toggle("landing-theme-toggle")
    left, right = st.columns([1.08, 0.92], gap="large")
    with left:
        st.markdown(
            '<div class="landing-hero"><div class="landing-brand" style="font-size:20px;font-weight:800;letter-spacing:-.03em">🛡️ <span class="landing-brand-main">Kavach</span><span class="landing-brand-accent">ED</span></div><h1>A shield for<br>every student.</h1><div class="sub">Spot risk early. Act in time.</div></div>',
            unsafe_allow_html=True,
        )
        quotes = [
            "Small steps, taken consistently, can change a whole learning journey.",
            "Every question is a doorway to a stronger understanding.",
            "Progress grows when effort has room to begin again.",
            "A steady routine can turn a difficult subject into a familiar one.",
            "Learning is built one curious moment at a time.",
            "Asking for support is a powerful part of making progress.",
        ]
        quote = quotes[int(datetime.now().timestamp() // 6) % len(quotes)]
        st.markdown(f'<div class="quote">“{quote}”</div><div class="chip-row"><span class="feature-chip">Early risk alerts</span><span class="feature-chip">AI study coach</span><span class="feature-chip">Ask your documents</span><span class="feature-chip">Teacher + student views</span></div>', unsafe_allow_html=True)
        st.caption("Built for earlier support, clearer insight, and better student outcomes.")
    with right:
        with st.container(border=True):
            st.subheader("Welcome to KavachED")
            st.caption("A calm, clear place to notice needs and support progress.")
            role = st.radio("I am a", ["Student", "Teacher"], horizontal=True, key="landing_role")
            mode = st.radio("Choose an option", ["Sign in", "Create account"], horizontal=True, key="auth_mode", label_visibility="collapsed")
            if mode == "Sign in":
                with st.form("sign_in"):
                    identifier = st.text_input("Email" if role == "Teacher" else "Email or roll number")
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)
                if submitted:
                    user = login(identifier, password, role.lower())
                    if user:
                        set_user(user)
                        st.rerun()
                    st.error("Invalid email or password. If the account is locked, try again in five minutes.")
                google_ready = google_auth_configured()
                st.markdown("<div style='text-align:center;color:var(--muted);padding:8px'>or</div>", unsafe_allow_html=True)
                google_clicked = st.button("Continue with Google", disabled=not google_ready, use_container_width=True,
                                           help="Google sign-in needs OAuth setup (see README)")
                if google_clicked:
                    st.login("google")
            else:
                with st.form("sign_up"):
                    name = st.text_input("Full name")
                    email = st.text_input("Email address")
                    roll = st.text_input("Roll number") if role == "Student" else ""
                    class_code = st.text_input("Class code") if role == "Student" else ""
                    college = st.text_input("College or institute name") if role == "Teacher" else ""
                    password = st.text_input("Password", type="password", help="At least 8 characters, including a letter and a number.")
                    confirm = st.text_input("Confirm password", type="password")
                    submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
                if submitted:
                    if not name.strip() or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()):
                        st.error("Enter your full name and a valid email address.")
                    elif not valid_password(password):
                        st.error("Use at least 8 characters with at least one letter and one number.")
                    elif password != confirm:
                        st.error("Your passwords do not match.")
                    else:
                        try:
                            if role == "Teacher":
                                if not college.strip():
                                    st.error("Enter your college or institute name.")
                                else:
                                    user, code = register_teacher(name, email, college, password)
                                    st.success(f"Your workspace is ready. Your class code is **{code}** — copy and share it with students.")
                                    set_user(user)
                                    st.rerun()
                            elif not roll.strip() or not class_code.strip():
                                st.error("Enter your roll number and class code.")
                            else:
                                set_user(register_student(name, email, roll, class_code, password))
                                st.rerun()
                        except ValueError as error:
                            st.error(str(error))
                        except sqlite3.IntegrityError:
                            st.error("An account already uses that email. Sign in instead.")
            with st.expander("Demo access"):
                st.write("**Teacher:** teacher.demo@kavached.app · **Password:** KavachDemo@26")
                st.write("**Student:** student.demo@kavached.app · **Password:** KavachDemo@26")
                st.write("**Class code:** KVCH-DEMO")
    st.caption("(c) 2026 KavachED. All rights reserved.")
    with st.expander("Privacy and terms"):
        st.caption("KavachED keeps each college workspace separate. Student records are visible only within the linked class and each student can access only their own records. Use this educational support tool alongside your institution's policies.")


def render_sidebar(user: dict) -> str:
    """Render role-aware navigation, account actions, and a compact help panel."""
    pages = TEACHER_PAGES if user["role"] == "teacher" else STUDENT_PAGES
    with st.sidebar:
        logo_data = base64.b64encode(Path("assets/logo-mark.svg").read_bytes()).decode("ascii")
        st.markdown(
            f'<div class="sidebar-brand"><img src="data:image/svg+xml;base64,{logo_data}" alt=""><div class="sidebar-brand-name">Kavach<span>ED</span></div></div><div class="sidebar-subtitle">Student Success Platform</div>',
            unsafe_allow_html=True,
        )
        current = st.session_state.get("page", pages[0])
        if current not in pages:
            current = pages[0]
        groups = [
            ("MAIN", [("Overview", "dashboard"), ("My Overview", "dashboard")]),
            ("PEOPLE", [("Students", "groups"), ("Student 360", "person_search"), ("Interventions", "checklist")]),
            ("TOOLS", [
                ("Data Studio", "upload_file"),
                ("Knowledge Base", "menu_book"),
                ("Ask KavachED", "forum"),
                ("Study Coach", "school"),
                ("What-If & Goals", "track_changes"),
                ("My Subjects", "menu_book"),
            ]),
            ("ACCOUNT", [("Settings", "settings")]),
        ]
        for section, items in groups:
            visible_items = [(name, icon) for name, icon in items if name in pages]
            if not visible_items:
                continue
            st.markdown(f'<div class="nav-section">{section}</div>', unsafe_allow_html=True)
            for name, icon in visible_items:
                key_name = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                if st.button(
                    name,
                    icon=f":material/{icon}:",
                    type="primary" if name == current else "secondary",
                    use_container_width=True,
                    key=f"nav-{key_name}",
                ):
                    st.session_state.page = name
                    st.rerun()
        page = st.session_state.get("page", current)
        if page not in pages:
            page = current
            st.session_state.page = page
        st.markdown('<div class="nav-section">KAVACHBOT</div>', unsafe_allow_html=True)
        ai_online = st.session_state.get("kavach_ai_online", False)
        status_color = "#22c55e" if ai_online else "#f5a524"
        status_text = "AI online" if ai_online else "Rule-based mode"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:7px;color:#bdc9d9;font-size:11px"><span style="width:8px;height:8px;border-radius:50%;background:{status_color};display:inline-block"></span>{status_text}</div>',
            unsafe_allow_html=True,
        )
        history = db.query(
            "SELECT role,message FROM chat_history WHERE workspace_id=? AND user_id=? ORDER BY created_on DESC LIMIT 6",
            (user["workspace_id"], user["id"]),
        )
        chat_markup = []
        has_long_reply = False
        for entry in reversed(history):
            is_user = entry["role"] == "user"
            message = entry["message"]
            if not is_user and len(message) > 220:
                message = message[:220].rstrip() + "…"
                has_long_reply = True
            avatar = "Y" if is_user else "K"
            role_class = "user" if is_user else "bot"
            chat_markup.append(
                f'<div class="chat-message {role_class}"><span class="chat-avatar">{avatar}</span><div class="chat-bubble">{html.escape(message)}</div></div>'
            )
        if has_long_reply:
            chat_markup.append('<span class="chat-read-more">Read more in Ask KavachED</span>')
        st.markdown(f'<div class="kavach-chat-area">{"".join(chat_markup)}</div>', unsafe_allow_html=True)
        if has_long_reply and st.button("Read more in Ask KavachED", key="sidebar-read-more", use_container_width=True):
            st.session_state.page = "Ask KavachED"
            st.rerun()
        suggestion_one, suggestion_two = st.columns(2, gap="small")
        quick_question = None
        with suggestion_one:
            if st.button("Attendance ideas", key="chat-suggest-attendance", use_container_width=True):
                quick_question = "How can I support students with attendance?"
        with suggestion_two:
            if st.button("Study support", key="chat-suggest-study", use_container_width=True):
                quick_question = "Suggest a study support plan for students."
        question = st.chat_input("Ask KavachBot", key="sidebar-chat-input")
        if st.button("Clear chat", icon=":material/delete_outline:", key="sidebar-clear-chat", use_container_width=True):
            db.execute(
                "DELETE FROM chat_history WHERE workspace_id=? AND user_id=?",
                (user["workspace_id"], user["id"]),
            )
            st.rerun()
        question = quick_question or question
        if question and question.strip():
            save_chat_message(user, "user", question)
            response, cited = answer_question(user, question)
            save_chat_message(user, "assistant", response)
            st.rerun()
        initials = "".join(part[0] for part in user["name"].split()[:2]).upper()
        st.markdown(
            f'<div class="sidebar-account"><div class="account-avatar">{html.escape(initials)}</div><div><div class="account-name">{html.escape(user["name"])}</div><div class="account-role">{html.escape(user["role"].title())}</div></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Log out", icon=":material/logout:", key="sidebar-logout", use_container_width=True):
            logout()
    return page


def answer_question(user: dict, question: str, document_filter: str | None = None) -> tuple[str, list[dict]]:
    """Answer from workspace documents and cite matching source chunks."""
    documents = db.query("SELECT filename,content FROM documents WHERE workspace_id=?", (user["workspace_id"],))
    matches = retrieve(question, documents, filename=document_filter)
    if not matches or matches[0]["score"] < 0.05:
        st.session_state["kavach_ai_online"] = False
        return "I could not find this in your college documents. Try a question about a policy or ask your teacher to upload a relevant document.", []
    if user["role"] == "student":
        student = next(iter(scoped_students(user)), None)
        result = student_assessment(user, student) if student else None
        data_summary = (
            f"Student attendance: {result['attendance']:.0f}%; assignments submitted: {result['assignments']:.0f}%; "
            f"continuous assessment average: {result['ct_average']:.0f}%; risk: {result['level']}."
            if result else "No student records have been added yet."
        )
    else:
        students = scoped_students(user)
        results = [student_assessment(user, student) for student in students]
        counts = {level: sum(result["level"] == level for result in results) for level in ("High", "Medium", "Low")}
        data_summary = f"Workspace students: {len(students)}; high risk: {counts['High']}; medium risk: {counts['Medium']}; low risk: {counts['Low']}."
    passages = "\n\n".join(f"[{item['filename']} · chunk {item['chunk']}]\n{item['text']}" for item in matches)
    context = f"Authorized account data:\n{data_summary}\n\nCollege document passages:\n{passages}"
    answer, used_ai = answer_with_context(question, context, st.session_state.get("language", "English"))
    st.session_state["kavach_ai_online"] = used_ai
    if not used_ai:
        answer = f"{matches[0]['text']}\n\n*AI unavailable, showing the best matching passage.*"
    return answer, matches


def save_chat_message(user: dict, role: str, message: str) -> None:
    """Persist one chat message within its user's workspace."""
    db.execute(
        "INSERT INTO chat_history(id,workspace_id,user_id,role,message) VALUES(?,?,?,?,?)",
        (db.new_id(), user["workspace_id"], user["id"], role, message),
    )


def save_chat_feedback(user: dict, question: str, rating: int) -> None:
    """Save a thumbs-up or thumbs-down rating for an answer."""
    db.execute(
        "INSERT INTO chat_feedback(id,workspace_id,user_id,question,rating) VALUES(?,?,?,?,?)",
        (db.new_id(), user["workspace_id"], user["id"], question, rating),
    )


def render_overview(user: dict) -> None:
    """Render the teacher command center or student overview."""
    teacher = user["role"] == "teacher"
    title = "Command Center" if teacher else "Your learning overview"
    hero(title, "A clearer view of progress, emerging needs, and the next helpful action.")
    students = scoped_students(user)
    if not teacher:
        if not students:
            st.info("Your teacher hasn't added your records yet. Your class is connected; ask your teacher to add subject records, then refresh this page.")
            workspace = db.query(
                """SELECT w.class_code,u.name AS teacher_name FROM workspaces w
                LEFT JOIN users u ON u.id=w.owner_user_id WHERE w.id=?""",
                (user["workspace_id"],),
            )
            if workspace:
                st.write(f"**Class code:** {workspace[0]['class_code']} · **Teacher:** {workspace[0]['teacher_name'] or 'Your class teacher'}")
            st.markdown("1. Class joined  ·  2. Roll number linked  ·  3. Waiting for your records")
            if st.button("Refresh records"): st.rerun()
            return
        student = students[0]
        records = student_records(user, student["roll_no"])
        if not records:
            st.markdown(f"### Good {'morning' if datetime.now().hour < 12 else 'afternoon'}, {html.escape(user['name'].split()[0])}")
            st.info("Your teacher hasn't added your records yet. Your roll number is linked and your progress will appear here as soon as records are available.")
            workspace = db.query(
                """SELECT w.class_code,u.name AS teacher_name FROM workspaces w
                LEFT JOIN users u ON u.id=w.owner_user_id WHERE w.id=?""",
                (user["workspace_id"],),
            )
            if workspace:
                st.write(f"**Class code:** {workspace[0]['class_code']} · **Teacher:** {workspace[0]['teacher_name'] or 'Your class teacher'}")
            st.markdown("1. Class joined  ·  2. Roll number linked  ·  3. Waiting for your records")
            if st.button("Refresh"): st.rerun()
            return
        result = student_assessment(user, student)
        kpis = st.columns(4)
        for column, label, value in zip(kpis, ["Attendance", "Assignments", "CT average", "Risk"], [f"{result['attendance']:.0f}%", f"{result['assignments']:.0f}%", f"{result['ct_average']:.0f}%", result["level"]]):
            column.metric(label, value)
        st.markdown(f"### {html.escape(user['name'])} · {student['roll_no']} &nbsp; <span class='{result['level'].lower() and {'High':'risk-high','Medium':'risk-medium','Low':'risk-low'}[result['level']]}'>{result['level']} risk</span>", unsafe_allow_html=True)
        st.write(" · ".join(result["reasons"]))
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Subject progress")
            for row in records:
                pct = row["classes_attended"] / row["classes_held"] if row["classes_held"] else 0
                st.write(f"**{row['subject']}** · attendance {pct:.0%}")
                st.progress(min(1.0, pct))
        with c2:
            st.subheader("Attendance plan")
            for row in records:
                plan = leave_calculator(row["classes_attended"], row["classes_held"])
                st.write(f"**{row['subject']}**: {plan['classes_can_miss']} classes you can still miss" if not plan["below_requirement"] else f"**{row['subject']}**: attend {plan['classes_needed']} classes to recover")
        attendance = db.query("SELECT week,attendance_pct FROM attendance_history WHERE workspace_id=? AND roll_no=? ORDER BY week", (user["workspace_id"], user["roll_no"]))
        if attendance:
            st.plotly_chart(attendance_line(pd.DataFrame([{"Week": f"Week {row['week']}", "Attendance": row["attendance_pct"]} for row in attendance]), st.session_state["theme"] == "dark"), use_container_width=True, theme=None)
        remarks = db.query("SELECT remark,created_on FROM remarks WHERE workspace_id=? AND roll_no=? ORDER BY created_on DESC LIMIT 5", (user["workspace_id"], user["roll_no"]))
        if remarks:
            st.subheader("Latest teacher notes")
            for remark in remarks: st.info(remark["remark"])
        return
    assessments = [(student, student_assessment(user, student)) for student in students]
    avg_attendance = sum(result["attendance"] for _, result in assessments) / len(assessments) if assessments else 0
    high = sum(result["level"] == "High" for _, result in assessments)
    medium = sum(result["level"] == "Medium" for _, result in assessments)
    low = sum(result["level"] == "Low" for _, result in assessments)
    cols = st.columns(5)
    for col, label, value in zip(cols, ["Students", "High risk", "Medium risk", "Low risk", "Avg attendance"], [len(students), high, medium, low, f"{avg_attendance:.0f}%"]):
        col.metric(label, value)
    if not students or not any(student_records(user, student["roll_no"]) for student in students):
        st.markdown("### Your workspace is ready")
        st.info("No data yet. Start by adding your students, then their subject records. Your class code is ready to share.")
        workspace = db.query("SELECT class_code FROM workspaces WHERE id=?", (user["workspace_id"],))
        st.code(workspace[0]["class_code"] if workspace else "")
        if st.button("Go to Data Studio"): st.session_state.page = "Data Studio"; st.rerun()
        st.markdown("**Getting started** · 1. Add students · 2. Add subject records · 3. Upload guidance · 4. Share your class code")
        return
    left, right = st.columns([1, 1.2])
    with left:
        st.subheader("Risk distribution")
        st.plotly_chart(risk_donut(pd.DataFrame([{"Risk": name, "Students": value} for name, value in [("High", high), ("Medium", medium), ("Low", low)]]), st.session_state["theme"] == "dark"), use_container_width=True, theme=None)
    with right:
        st.subheader("Attendance across the class")
        rows = db.query("SELECT week,AVG(attendance_pct) attendance_pct FROM attendance_history WHERE workspace_id=? GROUP BY week ORDER BY week", (user["workspace_id"],))
        if rows:
            st.plotly_chart(attendance_line(pd.DataFrame([{"Week": f"Week {r['week']}", "Attendance": r["attendance_pct"]} for r in rows]), st.session_state["theme"] == "dark"), use_container_width=True, theme=None)
        else: st.info("Attendance trends will appear after records are added.")
    st.subheader("Students who may need support")
    top = sorted(assessments, key=lambda item: (item[1]["score"], -item[1]["attendance"]), reverse=True)[:5]
    for student, result in top:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 2, 1])
            c1.write(f"**{student['name']}** · {student['roll_no']}")
            c2.write(f"{result['level']} risk · {result['reasons'][0]}")
            if c3.button("Open 360", key=f"open-{student['roll_no']}"):
                st.session_state.selected_roll = student["roll_no"]
                st.session_state.page = "Student 360"
                st.rerun()


def render_students(user: dict) -> None:
    """Show a searchable roster and expandable student risk details."""
    hero("Students", "Search the roster, understand the signals, and choose a supportive next step.")
    students = scoped_students(user)
    query_text = st.text_input("Search students", placeholder="Name or roll number")
    level_filter = st.multiselect("Risk level", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
    section_filter = st.multiselect("Section", sorted(set(item["section"] for item in students)))
    filtered = []
    for student in students:
        if query_text.lower() not in (student["name"] + student["roll_no"]).lower(): continue
        if section_filter and student["section"] not in section_filter: continue
        result = student_assessment(user, student)
        if result["level"] in level_filter: filtered.append((student, result))
    table = [{"Name": s["name"], "Roll": s["roll_no"], "Section": s["section"], "Risk": r["level"], "Attendance": f"{r['attendance']:.0f}%", "Assignments": f"{r['assignments']:.0f}%", "CT avg": f"{r['ct_average']:.0f}%", "Weakest subject": r["weakest_subject"]} for s, r in filtered]
    if table: st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)
    else: st.info("No students match these filters yet.")
    for student, result in filtered:
        with st.expander(f"{student['name']} · {student['roll_no']} · {result['level']} risk"):
            st.write("**Signals:** " + " · ".join(result["reasons"]))
            st.write("**Suggested support:** " + result["intervention"])
            if st.button("Open student profile", key=f"profile-{student['roll_no']}"):
                st.session_state.selected_roll = student["roll_no"]
                st.session_state.page = "Student 360"
                st.rerun()
    st.download_button("Export filtered CSV", pd.DataFrame(table).to_csv(index=False), "kavached-students.csv", "text/csv")
    with st.expander("Add student"):
        with st.form("add_student"):
            name = st.text_input("Student name")
            roll = st.text_input("Roll number")
            section = st.selectbox("Section", ["A", "B", "C"])
            submit = st.form_submit_button("Add student")
        if submit:
            if not name.strip() or not roll.strip(): st.error("Enter a name and roll number.")
            else:
                try:
                    db.execute("INSERT INTO students(id,workspace_id,roll_no,name,section) VALUES(?,?,?,?,?)", (db.new_id(), user["workspace_id"], roll.strip().upper(), name.strip(), section))
                    st.success("Student added to your workspace."); st.rerun()
                except sqlite3.IntegrityError:
                    st.error("That roll number already exists in this workspace.")


def render_student360(user: dict) -> None:
    """Show the selected student's records, history, notes, and interventions."""
    hero("Student 360", "A focused profile that brings academic signals and human support together.")
    students = scoped_students(user)
    if not students: st.info("Add a student to see their profile."); return
    rolls = [item["roll_no"] for item in students]
    preferred = st.session_state.get("selected_roll")
    roll = st.selectbox("Choose student", rolls, index=rolls.index(preferred) if preferred in rolls else 0)
    student = next(item for item in students if item["roll_no"] == roll)
    result = student_assessment(user, student)
    st.markdown(f"## {html.escape(student['name'])} · {student['roll_no']} · Section {student['section']}")
    st.markdown(f"<span class='{ {'High':'risk-high','Medium':'risk-medium','Low':'risk-low'}[result['level']]}'> {result['level']} risk</span> &nbsp; {result['trend']}", unsafe_allow_html=True)
    st.write("**Reasons:** " + " · ".join(result["reasons"]))
    records = student_records(user, roll)
    if records:
        st.dataframe(pd.DataFrame(records)[["subject", "classes_held", "classes_attended", "assignments_total", "assignments_submitted", "ct_marks", "ct_max", "project_done"]], use_container_width=True, hide_index=True)
    a, b = st.columns(2)
    with a:
        with st.form("add_remark"):
            remark = st.text_area("Add a teacher note")
            sentiment = st.selectbox("Tone", ["positive", "neutral", "negative"])
            if st.form_submit_button("Save note") and remark.strip():
                db.execute("INSERT INTO remarks(id,workspace_id,roll_no,remark,sentiment) VALUES(?,?,?,?,?)", (db.new_id(), user["workspace_id"], roll, remark.strip(), sentiment))
                st.success("Note saved."); st.rerun()
    with b:
        with st.form("add_intervention"):
            action = st.text_input("Support action")
            if st.form_submit_button("Plan intervention") and action.strip():
                db.execute("INSERT INTO interventions(id,workspace_id,roll_no,action,status) VALUES(?,?,?,?,?)", (db.new_id(), user["workspace_id"], roll, action.strip(), "Planned"))
                st.success("Intervention added."); st.rerun()
    remarks = db.query("SELECT remark,created_on FROM remarks WHERE workspace_id=? AND roll_no=? ORDER BY created_on DESC", (user["workspace_id"], roll))
    if remarks:
        st.subheader("Teacher notes")
        for row in remarks: st.write(f"• {row['remark']}  ·  {row['created_on']}")
    report = f"<html><body><h1>{html.escape(student['name'])} · {html.escape(roll)}</h1><p>Risk: {result['level']} · Attendance: {result['attendance']:.1f}%</p><p>{html.escape('; '.join(result['reasons']))}</p></body></html>"
    st.download_button("Download student report", report, f"{roll}-report.html", "text/html")


def render_data_studio(user: dict) -> None:
    """Provide forms and CSV tools for workspace data entry."""
    hero("Data Studio", "Add and maintain student records with clear, workspace-scoped data entry.")
    tabs = st.tabs(["Add student", "Subject record", "Add remark", "Bulk CSV", "Export"])
    with tabs[0]:
        with st.form("studio_student"):
            name, roll = st.text_input("Full name"), st.text_input("Roll number")
            section = st.selectbox("Section", ["A", "B", "C"])
            submitted = st.form_submit_button("Add student")
        if submitted:
            if not name.strip() or not roll.strip():
                st.error("Enter a name and roll number.")
            else:
                try:
                    db.execute("INSERT INTO students(id,workspace_id,roll_no,name,section) VALUES(?,?,?,?,?)", (db.new_id(), user["workspace_id"], roll.upper().strip(), name.strip(), section))
                    st.success("Student added."); st.rerun()
                except sqlite3.IntegrityError:
                    st.error("That roll number already exists in this workspace.")
    with tabs[1]:
        students = scoped_students(user)
        if not students: st.info("Add a student before adding subject records.")
        else:
            with st.form("subject_record"):
                roll = st.selectbox("Student", [item["roll_no"] for item in students])
                subject = st.text_input("Subject", "Mathematics")
                c1, c2, c3 = st.columns(3)
                held = c1.number_input("Classes held", min_value=0, value=20)
                attended = c2.number_input("Classes attended", min_value=0, value=16)
                total = c3.number_input("Assignments", min_value=0, value=4)
                c4, c5, c6 = st.columns(3)
                submitted_count = c4.number_input("Assignments submitted", min_value=0, value=3)
                marks = c5.number_input("CT marks", min_value=0.0, value=35.0)
                maximum = c6.number_input("CT maximum", min_value=1.0, value=50.0)
                done = st.checkbox("Project complete", value=True)
                save = st.form_submit_button("Save subject record")
            if save:
                if attended > held or submitted_count > total: st.error("Attended/submitted counts cannot exceed the corresponding totals.")
                else:
                    with db.connect() as connection:
                        connection.execute("""INSERT INTO subject_records
                        (id,workspace_id,roll_no,subject,classes_held,classes_attended,assignments_total,assignments_submitted,ct_marks,ct_max,project_done)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(workspace_id,roll_no,subject) DO UPDATE SET
                        classes_held=excluded.classes_held,classes_attended=excluded.classes_attended,
                        assignments_total=excluded.assignments_total,assignments_submitted=excluded.assignments_submitted,
                        ct_marks=excluded.ct_marks,ct_max=excluded.ct_max,project_done=excluded.project_done""",
                        (db.new_id(), user["workspace_id"], roll, subject.strip(), held, attended, total, submitted_count, marks, maximum, int(done)))
                    st.success("Subject record saved."); st.rerun()
    with tabs[2]:
        students = scoped_students(user)
        if not students:
            st.info("Add a student before recording a remark.")
        else:
            with st.form("studio_remark"):
                roll = st.selectbox("Student", [item["roll_no"] for item in students], key="remark_roll")
                remark = st.text_area("Remark")
                sentiment = st.selectbox("Sentiment", ["positive", "neutral", "negative"])
                submitted = st.form_submit_button("Save remark")
            if submitted:
                if not remark.strip():
                    st.error("Enter a remark before saving.")
                else:
                    db.execute(
                        "INSERT INTO remarks(id,workspace_id,roll_no,remark,sentiment) VALUES(?,?,?,?,?)",
                        (db.new_id(), user["workspace_id"], roll, remark.strip(), sentiment),
                    )
                    st.success("Remark saved."); st.rerun()
    with tabs[3]:
        template_df = pd.DataFrame(columns=["roll_no", "subject", "classes_held", "classes_attended", "assignments_total", "assignments_submitted", "ct_marks", "ct_max", "project_done"])
        st.download_button("Download CSV template", template_df.to_csv(index=False), "student-records-template.csv", "text/csv")
        uploaded = st.file_uploader("Choose a CSV file", type=["csv"])
        if uploaded:
            try:
                frame = pd.read_csv(uploaded)
                required = set(template_df.columns)
                missing = required - set(frame.columns)
                if missing: st.error("Missing columns: " + ", ".join(sorted(missing)))
                else:
                    st.dataframe(frame.head(20), use_container_width=True, hide_index=True)
                    if st.button("Import valid rows"):
                        roster = {item["roll_no"] for item in scoped_students(user)}
                        errors = []
                        for number, row in frame.iterrows():
                            if str(row["roll_no"]) not in roster:
                                errors.append(f"Row {number + 2}: unknown roll number {row['roll_no']}")
                                continue
                            values = [int(row["classes_held"]), int(row["classes_attended"]), int(row["assignments_total"]), int(row["assignments_submitted"])]
                            if values[1] > values[0] or values[3] > values[2]:
                                errors.append(f"Row {number + 2}: attended/submitted exceeds total")
                                continue
                            db.execute("""INSERT INTO subject_records
                            (id,workspace_id,roll_no,subject,classes_held,classes_attended,assignments_total,assignments_submitted,ct_marks,ct_max,project_done)
                            VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(workspace_id,roll_no,subject) DO UPDATE SET
                            classes_held=excluded.classes_held,classes_attended=excluded.classes_attended,
                            assignments_total=excluded.assignments_total,assignments_submitted=excluded.assignments_submitted,
                            ct_marks=excluded.ct_marks,ct_max=excluded.ct_max,project_done=excluded.project_done""",
                            (db.new_id(), user["workspace_id"], str(row["roll_no"]), str(row["subject"]), *values, float(row["ct_marks"]), float(row["ct_max"]), int(row["project_done"])))
                        if errors: st.warning("Some rows were skipped:\n" + "\n".join(errors))
                        else: st.success("All rows imported.")
                        st.rerun()
            except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError, ValueError):
                st.error("Could not read this CSV. Check the file and try again.")
    with tabs[4]:
        records = db.query("SELECT * FROM subject_records WHERE workspace_id=?", (user["workspace_id"],))
        if records:
            st.download_button("Export all subject records", pd.DataFrame(records).to_csv(index=False), "kavached-records.csv", "text/csv")
        else: st.info("There are no records to export yet.")


def render_knowledge_base(user: dict) -> None:
    """Manage the policy documents used by KavachED answers."""
    hero("Knowledge Base", "Add your institution's guidance so answers are grounded in the right documents.")
    upload = st.file_uploader("Upload a .txt or .pdf file", type=["txt", "pdf"])
    if upload and st.button("Add document"):
        try:
            if upload.type == "application/pdf":
                from pypdf import PdfReader
                text = "\n".join(page.extract_text() or "" for page in PdfReader(upload).pages)
            else:
                text = upload.getvalue().decode("utf-8")
            if not text.strip(): st.error("This document has no readable text.")
            else:
                db.execute("INSERT INTO documents(id,workspace_id,filename,content) VALUES(?,?,?,?)", (db.new_id(), user["workspace_id"], upload.name, text))
                st.success("Document added to your workspace."); st.rerun()
        except (PdfReadError, UnicodeDecodeError, OSError, ValueError):
            st.error("We could not read this document. Try a text-based PDF or a UTF-8 text file.")
    docs = db.query("SELECT id,filename,content,uploaded_on FROM documents WHERE workspace_id=? ORDER BY uploaded_on DESC", (user["workspace_id"],))
    if not docs: st.info("Your knowledge base is empty. Upload attendance or exam guidance to begin.")
    for document in docs:
        chunks = max(1, (len(document["content"]) + 399) // 400)
        with st.expander(f"📄 {document['filename']} · {chunks} chunks"):
            st.caption(document["uploaded_on"])
            st.write(document["content"][:1200] + ("…" if len(document["content"]) > 1200 else ""))
            if st.button("Delete document", key=f"delete-doc-{document['id']}"):
                db.execute("DELETE FROM documents WHERE id=? AND workspace_id=?", (document["id"], user["workspace_id"]))
                st.success("Document removed."); st.rerun()


def render_ask(user: dict) -> None:
    """Render the cited document question-and-answer workspace."""
    hero("Ask KavachED", "Ask a question and get a grounded answer from your college's guidance.")
    docs = db.query("SELECT id,filename,content FROM documents WHERE workspace_id=?", (user["workspace_id"],))
    if not docs:
        st.info("No documents are available yet. Ask your teacher to upload a policy or guidance document.")
        return
    left, right = st.columns([1.6, 1])
    with right:
        st.subheader("Sources")
        for document in docs:
            st.markdown(f"**{document['filename']}**")
            st.caption(f"{len(document['content'])} characters · available in this workspace")
    with left:
        filenames = ["All documents"] + [document["filename"] for document in docs]
        selected = st.selectbox("Search in", filenames)
        thread = db.query(
            "SELECT role,message FROM chat_history WHERE workspace_id=? AND user_id=? ORDER BY created_on DESC LIMIT 8",
            (user["workspace_id"], user["id"]),
        )
        for message in reversed(thread):
            with st.chat_message("assistant" if message["role"] == "assistant" else "user"):
                st.write(message["message"])
        suggestions = ["What is the attendance requirement?", "Where can students get academic support?", "What should I do if I am falling behind?", "When should I contact my mentor?"]
        st.caption("Try one of these")
        buttons = st.columns(2)
        for index, prompt in enumerate(suggestions):
            if buttons[index % 2].button(prompt, key=f"suggest-{index}"):
                st.session_state.ask_question = prompt
        question = st.text_input("Your question", key="ask_question", placeholder="Ask about attendance, exams, or support…")
        if st.button("Find an answer", type="primary") and question.strip():
            save_chat_message(user, "user", question)
            response, citations = answer_question(user, question, None if selected == "All documents" else selected)
            save_chat_message(user, "assistant", response)
            st.session_state.last_answer = {"user_id": user["id"], "question": question, "response": response, "citations": citations}
        last_answer = st.session_state.get("last_answer", {})
        if last_answer.get("user_id") == user["id"]:
            st.markdown(f'<div class="card"><b>KavachED</b><p>{html.escape(last_answer["response"]).replace(chr(10), "<br>")}</p></div>', unsafe_allow_html=True)
            citations = last_answer["citations"]
            if citations:
                score = citations[0]["score"]
                confidence = "High" if score >= 0.25 else "Medium" if score >= 0.1 else "Low"
                st.caption(f"Confidence: {confidence}")
                st.markdown("**Sources**")
                for item in citations:
                    with st.expander(f"{item['filename']} · chunk {item['chunk']} · similarity {item['score']:.2f}"):
                        st.write(item["text"])
            else:
                st.caption("No source matched confidently enough.")
            feedback = st.feedback("thumbs", key=f"feedback-{user['id']}-{last_answer['question'][:24]}")
            feedback_event = (user["id"], last_answer["question"], feedback)
            if feedback is not None and st.session_state.get("saved_feedback") != feedback_event:
                save_chat_feedback(user, last_answer["question"], feedback)
                st.session_state.saved_feedback = feedback_event
                st.toast("Thanks, your feedback was saved.")
    st.caption("Answers are generated from workspace documents. Verify important decisions with your institution.")


def render_interventions(user: dict) -> None:
    """Display and update the intervention board for the workspace."""
    hero("Interventions", "Coordinate practical next steps and keep every support action visible.")
    statuses = ["Planned", "In progress", "Done"]
    columns = st.columns(3)
    for column, status in zip(columns, statuses):
        with column:
            rows = db.query("SELECT * FROM interventions WHERE workspace_id=? AND status=? ORDER BY created_on DESC", (user["workspace_id"], status))
            st.subheader(f"{status} · {len(rows)}")
            for row in rows:
                student = db.query("SELECT name FROM students WHERE workspace_id=? AND roll_no=?", (user["workspace_id"], row["roll_no"]))
                name = student[0]["name"] if student else row["roll_no"]
                with st.container(border=True):
                    st.markdown(f"**{html.escape(name)}**")
                    st.write(row["action"])
                    next_status = statuses[(statuses.index(status) + 1) % len(statuses)]
                    if st.button(f"Move to {next_status}", key=f"move-{row['id']}"):
                        db.execute("UPDATE interventions SET status=? WHERE id=? AND workspace_id=?", (next_status, row["id"], user["workspace_id"]))
                        st.rerun()
    with st.expander("Create an intervention"):
        students = scoped_students(user)
        if students:
            with st.form("new_intervention"):
                roll = st.selectbox("Student", [item["roll_no"] for item in students])
                action = st.text_input("Action")
                if st.form_submit_button("Add to planned") and action.strip():
                    db.execute("INSERT INTO interventions(id,workspace_id,roll_no,action,status) VALUES(?,?,?,?,?)", (db.new_id(), user["workspace_id"], roll, action.strip(), "Planned"))
                    st.rerun()
        else: st.info("Add a student before creating an intervention.")


def render_study_coach(user: dict) -> None:
    """Load the logged-in student's records for the Study Coach view."""
    student = next(iter(scoped_students(user)), None)
    if not student:
        render_student_study_coach(user, None, [], {})
        return
    records = student_records(user, student["roll_no"])
    assessment = student_assessment(user, student) if records else {}
    render_student_study_coach(user, student, records, assessment)


def render_what_if(user: dict) -> None:
    """Let the student explore attendance and assessment scenarios."""
    hero("What-If & Goals", "Explore how steady attendance and a future assessment could change your progress.")
    student = next(iter(scoped_students(user)), None)
    if not student: st.info("Your linked student profile is not available."); return
    records = student_records(user, student["roll_no"])
    if not records: st.info("Your teacher hasn't added records yet."); return
    held = sum(row["classes_held"] for row in records)
    attended = sum(row["classes_attended"] for row in records)
    ct_marks, ct_max = sum(row["ct_marks"] for row in records), sum(row["ct_max"] for row in records)
    next_classes = st.slider("Attend the next number of classes", 0, 30, 5)
    next_ct = st.slider("Score on the next assessment (%)", 0, 100, 70)
    result = what_if(attended, held, next_classes, ct_marks, ct_max, next_ct)
    c1, c2 = st.columns(2)
    c1.metric("Attendance now", f"{result['before_attendance']:.1f}%")
    c2.metric("After attending", f"{result['after_attendance']:.1f}%", f"{result['after_attendance'] - result['before_attendance']:+.1f}%")
    st.write(f"Estimated attendance status: **{result['before_risk']} → {result['after_risk']}**. Assessment average: **{result['before_ct']:.0f}% → {result['after_ct']:.0f}%**.")
    target = st.slider("My attendance goal", 75, 100, 80)
    plan = leave_calculator(attended, held, target)
    st.progress(min(1.0, plan["current"] / target))
    if plan["below_requirement"]:
        st.info(f"Your current attendance is {plan['current']:.1f}%. Attend the next {plan['classes_needed']} classes to reach your goal.")
    else:
        st.success(f"You're at {plan['current']:.1f}% and can miss up to {plan['classes_can_miss']} additional classes while staying at or above your goal.")


def render_settings(user: dict) -> None:
    """Show profile, workspace code, theme, and safe workspace controls."""
    hero("Settings", "Manage your profile and preferences.")
    st.markdown(f"**Name:** {html.escape(user['name'])}  \n**Email:** {html.escape(user['email'])}  \n**Role:** {user['role'].title()}")
    st.caption(f"Current appearance: {st.session_state['theme'].title()}.")
    render_theme_toggle("settings-theme-toggle")
    workspace = db.query("SELECT name,class_code FROM workspaces WHERE id=?", (user["workspace_id"],))
    if workspace:
        st.write(f"**Workspace:** {workspace[0]['name']}")
        st.write(f"**Class code:** `{workspace[0]['class_code']}`")
    if user["role"] == "teacher":
        st.warning("Deleting workspace data is permanent. For safety, workspace deletion is not available from this demo build.")
    if st.button("Log out"):
        logout()


def render_student_subjects(user: dict) -> None:
    """Show per-subject performance and attendance planning for one student."""
    hero("My Subjects", "See where you're doing well and where a little extra support could help.")
    student = next(iter(scoped_students(user)), None)
    if not student: st.info("Your linked student profile is not available."); return
    records = student_records(user, student["roll_no"])
    if not records: st.info("Your teacher hasn't added your records yet."); return
    for row in records:
        with st.container(border=True):
            st.markdown(f"### {html.escape(row['subject'])}")
            left, right, third = st.columns(3)
            attendance = row["classes_attended"] / row["classes_held"] * 100 if row["classes_held"] else 0
            left.metric("Attendance", f"{attendance:.0f}%")
            right.metric("Assignments", f"{row['assignments_submitted']}/{row['assignments_total']}")
            third.metric("CT marks", f"{row['ct_marks']:.0f}/{row['ct_max']:.0f}")
            plan = leave_calculator(row["classes_attended"], row["classes_held"])
            st.write(f"Attend **{plan['classes_needed']} classes** to recover." if plan["below_requirement"] else f"You can still miss **{plan['classes_can_miss']} classes** and remain at 75%.")


def route(user: dict, page: str) -> None:
    """Route the selected page after verifying it belongs to the user's role."""
    allowed = TEACHER_PAGES if user["role"] == "teacher" else STUDENT_PAGES
    if page not in allowed:
        st.error("This page is not available for your account.")
        return
    if page in ("Overview", "My Overview"): render_overview(user)
    elif page == "Students": render_students(user)
    elif page == "Student 360": render_student360(user)
    elif page == "Data Studio": render_data_studio(user)
    elif page == "Knowledge Base": render_knowledge_base(user)
    elif page == "Interventions": render_interventions(user)
    elif page == "Ask KavachED": render_ask(user)
    elif page == "Study Coach": render_study_coach(user)
    elif page == "What-If & Goals": render_what_if(user)
    elif page == "My Subjects": render_student_subjects(user)
    elif page == "Settings": render_settings(user)


if st.session_state.user is None:
    identity = google_identity()
    if identity:
        render_google_profile(identity)
    else:
        render_landing()
else:
    current_user = st.session_state.user
    selected_page = render_sidebar(current_user)
    with st.container(key="topbar-controls"):
        breadcrumb, search_control, theme_control, notification_control, profile = st.columns([2, 1.8, 1.45, 1.45, 2.65], gap="small")
        with breadcrumb:
            st.markdown(f"<div class='topline'><span class='topline-left'>KavachED / {html.escape(selected_page)}</span></div>", unsafe_allow_html=True)
        if current_user["role"] == "teacher":
            with search_control:
                with st.popover(" ", icon=":material/search:", help="Search students"):
                    search = st.text_input("Name or roll", placeholder="Search students")
                    matches = [s for s in scoped_students(current_user) if search.lower() in (s["name"] + s["roll_no"]).lower()]
                    for match in matches[:8]:
                        if st.button(f"{match['name']} · {match['roll_no']}", key=f"search-{match['roll_no']}"):
                            st.session_state.selected_roll = match["roll_no"]
                            st.session_state.page = "Student 360"
                            st.rerun()
        with theme_control:
            render_theme_toggle("topbar-theme-toggle")
        with notification_control:
            st.button(" ", icon=":material/notifications:", help="Notifications", key="topbar-notifications")
        with profile:
            st.markdown(
                f'<div class="sidebar-account topbar-profile" style="margin:0"><div class="account-avatar">{html.escape("".join(part[0] for part in current_user["name"].split()[:2]).upper())}</div><div><div class="account-name">{html.escape(current_user["name"])}</div><div class="account-role">{html.escape(current_user["role"].title())}</div></div></div>',
                unsafe_allow_html=True,
            )
    route(current_user, selected_page)
