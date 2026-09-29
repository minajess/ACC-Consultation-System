"""
Flask CLI commands used to set up the database for development/demo use:

    flask init-db     -> creates all tables (drops nothing that exists)
    flask seed-db      -> populates sample accounts and demo data
    flask reset-db     -> drops all tables, recreates them, and reseeds

These are registered on the app in app/__init__.py so they're available as
soon as FLASK_APP=run.py is set, with no separate script to remember.
"""

from datetime import date, time, timedelta

import click

from app.extensions import db
from app.models import (
    User,
    Student,
    MedicalExpert,
    Availability,
    Consultation,
    Notification,
    AuditLog,
    ROLE_SUPER_ADMIN,
    ROLE_MEDICAL_EXPERT,
    ROLE_STUDENT,
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_COMPLETED,
)


def register_cli_commands(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all database tables."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed-db")
    def seed_db():
        """Populate the database with sample accounts and demo data."""
        _seed(app)
        click.echo("Sample data created.")
        click.echo("  Super Admin : admin@abuyogcollege.edu.ph / Admin@12345")
        click.echo("  Medical Exp : medical@abuyogcollege.edu.ph / Medical@12345")
        click.echo("  Student     : student@abuyogcollege.edu.ph / Student@12345")

    @app.cli.command("reset-db")
    def reset_db():
        """Drop, recreate, and reseed the database. Destroys all data."""
        db.drop_all()
        db.create_all()
        _seed(app)
        click.echo("Database reset and reseeded.")


def _seed(app):
    """Idempotent-ish seeding: skips creating accounts that already exist."""

    if User.query.filter_by(email="admin@abuyogcollege.edu.ph").first() is None:
        admin = User(email="admin@abuyogcollege.edu.ph", role=ROLE_SUPER_ADMIN, is_active_account=True)
        admin.set_password("Admin@12345")
        db.session.add(admin)

    expert_user = User.query.filter_by(email="medical@abuyogcollege.edu.ph").first()
    if expert_user is None:
        expert_user = User(email="medical@abuyogcollege.edu.ph", role=ROLE_MEDICAL_EXPERT, is_active_account=True)
        expert_user.set_password("Medical@12345")
        db.session.add(expert_user)
        db.session.flush()  # get expert_user.id before creating the profile
        expert_profile = MedicalExpert(
            user_id=expert_user.id,
            expert_id="EXP-0001",
            first_name="Maria",
            last_name="Santos",
            specialization="General Medicine",
            license_number="PRC-112233",
            contact_number="0917-000-1111",
        )
        db.session.add(expert_profile)
        db.session.flush()

        # A week of sample availability, 9am-11am and 2pm-4pm on weekdays
        today = date.today()
        for i in range(1, 8):
            slot_date = today + timedelta(days=i)
            if slot_date.weekday() >= 5:  # skip weekends
                continue
            db.session.add(Availability(expert_id=expert_profile.id, slot_date=slot_date, start_time=time(9, 0), end_time=time(10, 0)))
            db.session.add(Availability(expert_id=expert_profile.id, slot_date=slot_date, start_time=time(10, 0), end_time=time(11, 0)))
            db.session.add(Availability(expert_id=expert_profile.id, slot_date=slot_date, start_time=time(14, 0), end_time=time(15, 0)))

    student_user = User.query.filter_by(email="student@abuyogcollege.edu.ph").first()
    if student_user is None:
        student_user = User(email="student@abuyogcollege.edu.ph", role=ROLE_STUDENT, is_active_account=True)
        student_user.set_password("Student@12345")
        db.session.add(student_user)
        db.session.flush()
        student_profile = Student(
            user_id=student_user.id,
            student_id="2026-00123",
            first_name="Juan",
            middle_name="Reyes",
            last_name="Dela Cruz",
            sex="Male",
            date_of_birth=date(2004, 5, 14),
            contact_number="0917-222-3333",
            course="BS Information Technology",
            year_level="3rd Year",
            address="Javier, Leyte, Philippines",
            emergency_contact="Ana Dela Cruz - 0917-444-5555",
        )
        db.session.add(student_profile)
        db.session.flush()

        # One sample past-completed consultation and one pending request,
        # so every dashboard has something to display on first login.
        expert_profile = MedicalExpert.query.filter_by(expert_id="EXP-0001").first()
        if expert_profile:
            db.session.add(
                Consultation(
                    student_id=student_profile.id,
                    expert_id=expert_profile.id,
                    consultation_type="General Check-up",
                    requested_date=date.today() - timedelta(days=10),
                    requested_time=time(9, 0),
                    reason="Routine wellness check before the semester.",
                    status=STATUS_COMPLETED,
                    notes="Vitals normal. Advised adequate sleep and hydration.",
                    recommendation="Follow up only if symptoms recur.",
                )
            )
            pending_slot = (
                Availability.query.filter_by(expert_id=expert_profile.id, is_booked=False)
                .order_by(Availability.slot_date)
                .first()
            )
            if pending_slot:
                pending_slot.is_booked = True
                db.session.add(
                    Consultation(
                        student_id=student_profile.id,
                        expert_id=expert_profile.id,
                        availability_id=pending_slot.id,
                        consultation_type="Follow-up Consultation",
                        requested_date=pending_slot.slot_date,
                        requested_time=pending_slot.start_time,
                        reason="Persistent mild headache for the past 3 days.",
                        status=STATUS_PENDING,
                    )
                )

    db.session.add(AuditLog(user_id=None, action="seed", description="Development sample data seeded."))
    db.session.commit()
