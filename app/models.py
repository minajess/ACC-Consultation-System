"""
Database models for the Abuyog Community College Consultation System.

Design overview
----------------
- `User` is the single authentication table (email/password/role). It is
  what Flask-Login works with. Every user has exactly one role:
  'super_admin', 'medical_expert', or 'student'.
- `Student` and `MedicalExpert` are 1-to-1 "profile" tables linked to a
  `User` row via a unique foreign key (user_id). This keeps login concerns
  (User) separate from role-specific profile data.
- `Availability` rows are time slots a medical expert opens up. A slot can
  be booked by at most one `Consultation` (enforced with a unique
  constraint on availability_id), which is how double-booking is prevented.
- `Consultation` is the central transactional table linking a Student to a
  MedicalExpert (optionally to a specific Availability slot), carrying a
  status that moves through the workflow described in the README.
- `Notification` gives each user a simple in-app inbox of status updates.
- `AuditLog` records administrative and security-relevant actions for the
  Super Admin's audit trail.

All tables include created_at (and updated_at where the row can change)
timestamps, and foreign keys use ON DELETE rules appropriate to the data
(e.g. consultations are kept even if related lookups change).
"""

from datetime import datetime, date, time

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db

# ---------------------------------------------------------------------------
# Enums (implemented as plain strings with helper tuples so SQLite - which
# has no native ENUM type - stores them simply as TEXT with app-level checks)
# ---------------------------------------------------------------------------

ROLE_SUPER_ADMIN = "super_admin"
ROLE_MEDICAL_EXPERT = "medical_expert"
ROLE_STUDENT = "student"
ROLES = (ROLE_SUPER_ADMIN, ROLE_MEDICAL_EXPERT, ROLE_STUDENT)

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_RESCHEDULED = "rescheduled"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
CONSULTATION_STATUSES = (
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_RESCHEDULED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
)


class User(UserMixin, db.Model):
    """Authentication record. One row per person who can log in."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)
    is_active_account = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    student_profile = db.relationship("Student", backref="user", uselist=False, cascade="all, delete-orphan")
    expert_profile = db.relationship("MedicalExpert", backref="user", uselist=False, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    # --- Flask-Login required overrides ---
    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        # Flask-Login checks this property to block deactivated accounts
        # from staying logged in / logging in again.
        return self.is_active_account

    # --- Password helpers ---
    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def display_name(self):
        if self.role == ROLE_STUDENT and self.student_profile:
            return f"{self.student_profile.first_name} {self.student_profile.last_name}"
        if self.role == ROLE_MEDICAL_EXPERT and self.expert_profile:
            return f"Dr. {self.expert_profile.first_name} {self.expert_profile.last_name}"
        if self.role == ROLE_SUPER_ADMIN:
            return "System Administrator"
        return self.email

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Student(db.Model):
    """Profile data for a user with role='student'."""

    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    student_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(80), nullable=False)
    middle_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80), nullable=False)
    sex = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    contact_number = db.Column(db.String(30))
    course = db.Column(db.String(120))
    year_level = db.Column(db.String(20))
    address = db.Column(db.String(255))
    emergency_contact = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    consultations = db.relationship("Consultation", backref="student", lazy="dynamic", foreign_keys="Consultation.student_id")

    @property
    def full_name(self):
        middle = f" {self.middle_name}" if self.middle_name else ""
        return f"{self.first_name}{middle} {self.last_name}"


class MedicalExpert(db.Model):
    """Profile data for a user with role='medical_expert'."""

    __tablename__ = "medical_experts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    expert_id = db.Column(db.String(30), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    specialization = db.Column(db.String(120), nullable=False)
    license_number = db.Column(db.String(60))
    contact_number = db.Column(db.String(30))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    availability_slots = db.relationship("Availability", backref="expert", lazy="dynamic", cascade="all, delete-orphan")
    consultations = db.relationship("Consultation", backref="expert", lazy="dynamic", foreign_keys="Consultation.expert_id")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Availability(db.Model):
    """A single open time slot offered by a medical expert."""

    __tablename__ = "availability"

    id = db.Column(db.Integer, primary_key=True)
    expert_id = db.Column(db.Integer, db.ForeignKey("medical_experts.id", ondelete="CASCADE"), nullable=False, index=True)
    slot_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_booked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("expert_id", "slot_date", "start_time", name="uq_expert_slot"),
    )

    @property
    def is_past(self):
        return datetime.combine(self.slot_date, self.end_time) < datetime.now()


class Consultation(db.Model):
    """The central consultation request/record."""

    __tablename__ = "consultations"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    expert_id = db.Column(db.Integer, db.ForeignKey("medical_experts.id", ondelete="CASCADE"), nullable=False, index=True)
    availability_id = db.Column(
        db.Integer, db.ForeignKey("availability.id", ondelete="SET NULL"), unique=True, nullable=True
    )

    consultation_type = db.Column(db.String(80), nullable=False)
    requested_date = db.Column(db.Date, nullable=False)
    requested_time = db.Column(db.Time, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING, index=True)
    rejection_reason = db.Column(db.String(255))
    notes = db.Column(db.Text)
    recommendation = db.Column(db.Text)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    slot = db.relationship("Availability", backref=db.backref("consultation", uselist=False))

    @property
    def status_badge_class(self):
        return {
            STATUS_PENDING: "bg-warning text-dark",
            STATUS_APPROVED: "bg-info text-dark",
            STATUS_REJECTED: "bg-danger",
            STATUS_RESCHEDULED: "bg-secondary",
            STATUS_COMPLETED: "bg-success",
            STATUS_CANCELLED: "bg-dark",
        }.get(self.status, "bg-light text-dark")


class Notification(db.Model):
    """A short in-app message shown to a user (e.g. status changes)."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class AuditLog(db.Model):
    """Records administrative / security-relevant actions."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    actor = db.relationship("User")


def log_action(user, action, description, ip_address=None):
    """Helper used throughout the app to write a single audit log row."""
    entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        description=description,
        ip_address=ip_address,
    )
    db.session.add(entry)


def notify(user_id, message):
    """Helper to create a notification for a user."""
    db.session.add(Notification(user_id=user_id, message=message))
