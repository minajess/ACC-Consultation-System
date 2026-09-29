# Abuyog Community College Consultation System

A web-based platform that lets students request and manage consultations
with medical experts, while giving administrators full control over users,
schedules, consultation records, and system activity.

Built with **Python 3, Flask, Flask-SQLAlchemy, Flask-Login, and SQLite** —
no external database server required. Runs entirely on your local machine
with a single command.

---

## 1. System Overview

The system supports three roles:

- **Super Admin** — manages student and medical expert accounts, oversees
  every consultation and schedule, and reviews the audit log.
- **Medical Expert** — defines their own availability, reviews incoming
  consultation requests, and approves, rejects, reschedules, or completes
  them with clinical notes.
- **Student** — registers an account, requests a consultation with an
  available expert and time slot, tracks its status, and views their
  consultation history.

**Workflow:** Student registers/logs in → requests a consultation by
picking an expert and an open time slot → Medical Expert reviews the
request → approves, rejects (with a reason), or reschedules it → on the
day of the consultation, the expert records notes and a recommendation and
marks it completed → the student sees the outcome in their history and
notifications.

---

## 2. Features

- Secure authentication with hashed passwords (Werkzeug) and session-based
  login (Flask-Login)
- Role-Based Access Control enforced on every route, not just hidden in the
  UI
- Student self-registration, plus full admin-managed CRUD for students and
  medical experts, including account activation/deactivation
- Role-specific dashboards with live counts (pending, completed, cancelled,
  today's schedule, etc.)
- Consultation lifecycle: pending → approved / rejected / rescheduled →
  completed, or cancelled by the student at any point before completion
- Expert-managed availability calendar with **double-booking prevention**
  (unique constraint + a server-side re-check at booking time)
- In-app notifications for every status change
- Search/filter on students, medical experts, and consultation lists
- Full audit log of logins, account changes, and consultation status
  changes, including timestamp and IP address
- CSRF protection on every form (Flask-WTF)
- Custom 403 / 404 / 500 error pages that never leak internal details
- Responsive Bootstrap 5 interface
- Automated test suite (pytest) covering auth, RBAC, and the booking
  workflow, including double-booking prevention

---

## 3. Database Design

SQLite database managed with SQLAlchemy ORM. Seven tables:

| Table             | Purpose                                                                 |
|-------------------|--------------------------------------------------------------------------|
| `users`           | Login credentials + role (`super_admin`, `medical_expert`, `student`). Password is stored as a Werkzeug hash, never plaintext. |
| `students`        | 1-to-1 profile linked to `users.id`. Student ID, name, course, year level, contact info, emergency contact. |
| `medical_experts` | 1-to-1 profile linked to `users.id`. Expert ID, name, specialization, license number, contact info. |
| `availability`    | Time slots an expert opens up (`slot_date`, `start_time`, `end_time`, `is_booked`). Unique constraint on `(expert_id, slot_date, start_time)` so an expert can't create the same slot twice. |
| `consultations`   | The central record: links a `student` and a `medical_expert` (and optionally a specific `availability` slot via a **unique** foreign key, so a slot can never back two consultations). Carries `status`, `reason`, `notes`, `recommendation`, `rejection_reason`, and timestamps. |
| `notifications`   | Short messages tied to a `user_id`, shown in-app and marked read on view. |
| `audit_logs`      | `user_id` (nullable, so failed-login attempts are still logged), `action`, `description`, `ip_address`, `created_at`. |

**Relationships:** `users` 1—1 `students`/`medical_experts` · `students` 1—N
`consultations` · `medical_experts` 1—N `consultations` and 1—N
`availability` · `availability` 1—1 `consultations` (via a unique FK, which
is what makes double-booking impossible at the database level, not just in
application code) · `users` 1—N `notifications` and 1—N `audit_logs`.

All tables carry `created_at`, and mutable tables also carry `updated_at`.
Indexes are placed on foreign keys and on columns used for lookup/filtering
(`email`, `role`, `status`, `student_id`, `expert_id`).

---

## 4. Project Structure

```
abuyog-consultation-system/
│
├── app/
│   ├── __init__.py           # Application factory
│   ├── models.py             # All SQLAlchemy models
│   ├── extensions.py         # db, login_manager, csrf instances
│   ├── utils.py              # roles_required decorator, IP helper
│   ├── seed_helpers.py       # `flask init-db` / `seed-db` / `reset-db`
│   │
│   ├── auth/                 # Login, logout, student registration
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   │
│   ├── admin/                 # Super Admin: users, consultations, audit log
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   │
│   ├── student/                # Student: request/view/cancel consultations
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   │
│   ├── medical/                # Medical Expert: requests, availability
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── forms.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── auth/ admin/ student/ medical/ errors/
│   │
│   └── static/
│       ├── css/style.css
│       └── js/main.js
│
├── instance/                  # abuyog_consultation.db lives here (created at runtime)
├── tests/                     # pytest suite
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_consultations.py
│
├── config.py
├── run.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 5. Installation (Windows)

**Step 1 — Check Python is installed** (3.9+ recommended):

```
python --version
```

**Step 2 — Create and activate a virtual environment:**

```
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` appear at the start of your command prompt.

**Step 3 — Install dependencies:**

```
pip install -r requirements.txt
```

**Step 4 — Configure environment variables:**

```
copy .env.example .env
```

Open `.env` in a text editor and replace `SECRET_KEY` with a real random
value. You can generate one with:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as the value of `SECRET_KEY` in `.env`.

---

## 6. Database Setup

With the virtual environment active and `.env` configured:

```
set FLASK_APP=run.py
flask init-db
flask seed-db
```

- `flask init-db` creates every table in a new SQLite file at
  `instance/abuyog_consultation.db`.
- `flask seed-db` creates the three sample accounts below plus a week of
  sample availability and a couple of demo consultations, so every
  dashboard has something to show on first login.

To wipe everything and start over at any point:

```
flask reset-db
```

### Development/Test Accounts

> These are **development credentials only**. Change them (or delete these
> accounts) before any real deployment.

| Role           | Email                              | Password        |
|----------------|-------------------------------------|-----------------|
| Super Admin    | admin@abuyogcollege.edu.ph          | Admin@12345     |
| Medical Expert | medical@abuyogcollege.edu.ph        | Medical@12345   |
| Student        | student@abuyogcollege.edu.ph        | Student@12345   |

---

## 7. Running the Application

```
python run.py
```

Then open your browser to:

```
http://127.0.0.1:5000
```

You'll land on the login page. Log in with any of the sample accounts
above, or register a new student account from the login page.

---

## 8. Testing

With the virtual environment active:

```
pytest
```

or, for more detail:

```
pytest -v
```

The suite covers: password hashing, student self-registration, login /
logout, deactivated-account login blocking, role-based access control on
every blueprint, consultation request creation, **double-booking
prevention**, expert approval, an expert being blocked from acting on
another expert's consultation, and student-initiated cancellation
(including a student being blocked from cancelling someone else's
consultation). Tests run against an in-memory SQLite database, so they
never touch your real `instance/abuyog_consultation.db`.

---

## 9. Troubleshooting

**`'flask' is not recognized as an internal or external command`**
Make sure the virtual environment is activated (`venv\Scripts\activate`)
before running `flask` commands — the `flask` executable is installed
inside the virtual environment.

**`sqlalchemy.exc.OperationalError: no such table`**
The database hasn't been initialized yet. Run `flask init-db` (and
`flask seed-db` if you also want the sample accounts).

**Login page keeps saying "Invalid email or password"**
Double check for extra spaces, and remember emails are matched
case-insensitively but passwords are case-sensitive. If you're not sure the
account exists, re-run `flask seed-db` (it skips accounts that already
exist, so it's safe to run again) or check the account in the Super Admin's
Student/Medical Expert management pages.

**Port 5000 is already in use**
Another program (or a previous `python run.py` you forgot to stop) is using
port 5000. Stop it, or edit `run.py` and change `port=5000` to another port
such as `5001`.

**Changes to templates or code don't seem to appear**
Set `FLASK_DEBUG=1` in `.env` (already the default) and restart
`python run.py` — the development server auto-reloads on code changes when
debug mode is on.

**I want a clean slate**
Run `flask reset-db`. This drops every table and reseeds the three sample
accounts — all other data will be lost.

**CSRF token errors on form submit**
This usually means the browser tab was left open across a server restart,
or the `.env` session lifetime expired. Refresh the page and try again.

---

## Security Notes

- Passwords are always hashed with Werkzeug (`generate_password_hash`) —
  the database never stores plaintext passwords.
- Every admin, student, and medical-expert route is protected by a
  `roles_required` decorator that checks both authentication and role — a
  student cannot reach an admin URL even by typing it directly into the
  browser.
- All forms are protected against CSRF via Flask-WTF.
- Consultation and student records are only accessible to the student who
  owns them, the medical expert assigned to them, and the Super Admin.
- Error pages never expose stack traces or internal details to the browser.
- `SECRET_KEY` and the database location are read from environment
  variables (`.env`), which is excluded from version control via
  `.gitignore`.

This project was built for academic demonstration and coursework purposes.
Before using it beyond a classroom setting, change all default credentials,
set a strong `SECRET_KEY`, set `FLASK_ENV=production`, and serve it behind
a proper WSGI server (e.g. Waitress on Windows) rather than the Flask
development server.
