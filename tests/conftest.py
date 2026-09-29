"""
Shared pytest fixtures.

Each test gets a fresh Flask app configured with an in-memory SQLite
database (TestingConfig), so tests never touch the real development
database and are fully isolated from one another.
"""

from datetime import date, time, timedelta

import pytest

from app import create_app
from app.extensions import db as _db
from app.models import (
    User,
    Student,
    MedicalExpert,
    Availability,
    ROLE_SUPER_ADMIN,
    ROLE_MEDICAL_EXPERT,
    ROLE_STUDENT,
)


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def db(app):
    return _db


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(db):
    user = User(email="admin@example.com", role=ROLE_SUPER_ADMIN, is_active_account=True)
    user.set_password("Admin@12345")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def expert_user(db):
    user = User(email="expert@example.com", role=ROLE_MEDICAL_EXPERT, is_active_account=True)
    user.set_password("Medical@12345")
    db.session.add(user)
    db.session.flush()
    expert = MedicalExpert(
        user_id=user.id,
        expert_id="EXP-TEST-1",
        first_name="Test",
        last_name="Expert",
        specialization="General Medicine",
        contact_number="0900-000-0000",
    )
    db.session.add(expert)
    db.session.commit()
    return user


@pytest.fixture
def open_slot(db, expert_user):
    slot = Availability(
        expert_id=expert_user.expert_profile.id,
        slot_date=date.today() + timedelta(days=1),
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    db.session.add(slot)
    db.session.commit()
    return slot


@pytest.fixture
def student_user(db):
    user = User(email="student@example.com", role=ROLE_STUDENT, is_active_account=True)
    user.set_password("Student@12345")
    db.session.add(user)
    db.session.flush()
    student = Student(
        user_id=user.id,
        student_id="2026-00001",
        first_name="Test",
        last_name="Student",
        sex="Male",
        date_of_birth=date(2004, 1, 1),
        contact_number="0900-111-1111",
        course="BSIT",
        year_level="3rd Year",
        address="Leyte, Philippines",
        emergency_contact="Parent - 0900-222-2222",
    )
    db.session.add(student)
    db.session.commit()
    return user


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)
