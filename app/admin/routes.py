from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (
    User,
    Student,
    MedicalExpert,
    Availability,
    Consultation,
    AuditLog,
    log_action,
    notify,
    ROLE_SUPER_ADMIN,
    ROLE_MEDICAL_EXPERT,
    ROLE_STUDENT,
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
)
from app.admin.forms import StudentForm, ExpertForm
from app.utils import roles_required, get_client_ip

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@admin_bp.before_request
@login_required
@roles_required(ROLE_SUPER_ADMIN)
def restrict_to_admins():
    """Applies the login+role check to every route in this blueprint."""
    pass


@admin_bp.route("/dashboard")
def dashboard():
    stats = {
        "total_students": Student.query.count(),
        "total_experts": MedicalExpert.query.count(),
        "pending": Consultation.query.filter_by(status=STATUS_PENDING).count(),
        "completed": Consultation.query.filter_by(status=STATUS_COMPLETED).count(),
        "cancelled": Consultation.query.filter_by(status=STATUS_CANCELLED).count(),
    }
    recent_activity = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    return render_template("admin/dashboard.html", stats=stats, recent_activity=recent_activity)


# ---------------------------------------------------------------------------
# Student management
# ---------------------------------------------------------------------------

@admin_bp.route("/students")
def students():
    q = request.args.get("q", "").strip()
    query = Student.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Student.first_name.ilike(like),
                Student.last_name.ilike(like),
                Student.student_id.ilike(like),
                Student.course.ilike(like),
            )
        )
    student_list = query.order_by(Student.last_name).all()
    return render_template("admin/students.html", students=student_list, q=q)


@admin_bp.route("/students/add", methods=["GET", "POST"])
def add_student():
    form = StudentForm()
    form.password.validators = [v for v in form.password.validators]  # required on create, enforced below
    if form.validate_on_submit():
        if not form.password.data:
            flash("Password is required when creating a new account.", "danger")
            return render_template("admin/student_form.html", form=form, mode="add")
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash("An account with that email already exists.", "danger")
            return render_template("admin/student_form.html", form=form, mode="add")
        if Student.query.filter_by(student_id=form.student_id.data.strip()).first():
            flash("A student with that Student ID already exists.", "danger")
            return render_template("admin/student_form.html", form=form, mode="add")

        user = User(email=form.email.data.lower().strip(), role=ROLE_STUDENT, is_active_account=form.is_active_account.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id,
            student_id=form.student_id.data.strip(),
            first_name=form.first_name.data.strip(),
            middle_name=(form.middle_name.data or "").strip() or None,
            last_name=form.last_name.data.strip(),
            sex=form.sex.data,
            date_of_birth=form.date_of_birth.data,
            contact_number=form.contact_number.data.strip(),
            course=form.course.data.strip(),
            year_level=form.year_level.data,
            address=form.address.data.strip(),
            emergency_contact=form.emergency_contact.data.strip(),
        )
        db.session.add(student)
        log_action(current_user, "create_student", f"Created student account {user.email}.", get_client_ip())
        db.session.commit()
        flash("Student account created.", "success")
        return redirect(url_for("admin.students"))

    return render_template("admin/student_form.html", form=form, mode="add")


@admin_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    user = student.user
    form = StudentForm(obj=student)
    if request.method == "GET":
        form.email.data = user.email
        form.is_active_account.data = user.is_active_account

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            flash("Another account already uses that email.", "danger")
            return render_template("admin/student_form.html", form=form, mode="edit", student=student)

        user.email = email
        user.is_active_account = form.is_active_account.data
        if form.password.data:
            user.set_password(form.password.data)

        student.student_id = form.student_id.data.strip()
        student.first_name = form.first_name.data.strip()
        student.middle_name = (form.middle_name.data or "").strip() or None
        student.last_name = form.last_name.data.strip()
        student.sex = form.sex.data
        student.date_of_birth = form.date_of_birth.data
        student.contact_number = form.contact_number.data.strip()
        student.course = form.course.data.strip()
        student.year_level = form.year_level.data
        student.address = form.address.data.strip()
        student.emergency_contact = form.emergency_contact.data.strip()

        log_action(current_user, "update_student", f"Updated student account {user.email}.", get_client_ip())
        db.session.commit()
        flash("Student account updated.", "success")
        return redirect(url_for("admin.students"))

    return render_template("admin/student_form.html", form=form, mode="edit", student=student)


@admin_bp.route("/students/<int:student_id>/toggle-active", methods=["POST"])
def toggle_student_active(student_id):
    student = Student.query.get_or_404(student_id)
    student.user.is_active_account = not student.user.is_active_account
    action = "activated" if student.user.is_active_account else "deactivated"
    log_action(current_user, "toggle_student", f"Student {student.user.email} {action}.", get_client_ip())
    db.session.commit()
    flash(f"Student account {action}.", "success")
    return redirect(url_for("admin.students"))


# ---------------------------------------------------------------------------
# Medical expert management
# ---------------------------------------------------------------------------

@admin_bp.route("/experts")
def experts():
    q = request.args.get("q", "").strip()
    query = MedicalExpert.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                MedicalExpert.first_name.ilike(like),
                MedicalExpert.last_name.ilike(like),
                MedicalExpert.specialization.ilike(like),
                MedicalExpert.expert_id.ilike(like),
            )
        )
    expert_list = query.order_by(MedicalExpert.last_name).all()
    return render_template("admin/experts.html", experts=expert_list, q=q)


@admin_bp.route("/experts/add", methods=["GET", "POST"])
def add_expert():
    form = ExpertForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash("Password is required when creating a new account.", "danger")
            return render_template("admin/expert_form.html", form=form, mode="add")
        if User.query.filter_by(email=form.email.data.lower().strip()).first():
            flash("An account with that email already exists.", "danger")
            return render_template("admin/expert_form.html", form=form, mode="add")
        if MedicalExpert.query.filter_by(expert_id=form.expert_id.data.strip()).first():
            flash("An expert with that Expert ID already exists.", "danger")
            return render_template("admin/expert_form.html", form=form, mode="add")

        user = User(email=form.email.data.lower().strip(), role=ROLE_MEDICAL_EXPERT, is_active_account=form.is_active_account.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        expert = MedicalExpert(
            user_id=user.id,
            expert_id=form.expert_id.data.strip(),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            specialization=form.specialization.data.strip(),
            license_number=(form.license_number.data or "").strip() or None,
            contact_number=form.contact_number.data.strip(),
        )
        db.session.add(expert)
        log_action(current_user, "create_expert", f"Created medical expert account {user.email}.", get_client_ip())
        db.session.commit()
        flash("Medical expert account created.", "success")
        return redirect(url_for("admin.experts"))

    return render_template("admin/expert_form.html", form=form, mode="add")


@admin_bp.route("/experts/<int:expert_id>/edit", methods=["GET", "POST"])
def edit_expert(expert_id):
    expert = MedicalExpert.query.get_or_404(expert_id)
    user = expert.user
    form = ExpertForm(obj=expert)
    if request.method == "GET":
        form.email.data = user.email
        form.is_active_account.data = user.is_active_account

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            flash("Another account already uses that email.", "danger")
            return render_template("admin/expert_form.html", form=form, mode="edit", expert=expert)

        user.email = email
        user.is_active_account = form.is_active_account.data
        if form.password.data:
            user.set_password(form.password.data)

        expert.expert_id = form.expert_id.data.strip()
        expert.first_name = form.first_name.data.strip()
        expert.last_name = form.last_name.data.strip()
        expert.specialization = form.specialization.data.strip()
        expert.license_number = (form.license_number.data or "").strip() or None
        expert.contact_number = form.contact_number.data.strip()

        log_action(current_user, "update_expert", f"Updated medical expert account {user.email}.", get_client_ip())
        db.session.commit()
        flash("Medical expert account updated.", "success")
        return redirect(url_for("admin.experts"))

    return render_template("admin/expert_form.html", form=form, mode="edit", expert=expert)


@admin_bp.route("/experts/<int:expert_id>/toggle-active", methods=["POST"])
def toggle_expert_active(expert_id):
    expert = MedicalExpert.query.get_or_404(expert_id)
    expert.user.is_active_account = not expert.user.is_active_account
    action = "activated" if expert.user.is_active_account else "deactivated"
    log_action(current_user, "toggle_expert", f"Medical expert {expert.user.email} {action}.", get_client_ip())
    db.session.commit()
    flash(f"Medical expert account {action}.", "success")
    return redirect(url_for("admin.experts"))


# ---------------------------------------------------------------------------
# Consultations (admin oversight) and schedules
# ---------------------------------------------------------------------------

@admin_bp.route("/consultations")
def consultations():
    status = request.args.get("status", "")
    query = Consultation.query
    if status:
        query = query.filter_by(status=status)
    consultation_list = query.order_by(Consultation.created_at.desc()).all()
    return render_template("admin/consultations.html", consultations=consultation_list, status=status)


@admin_bp.route("/schedules")
def schedules():
    expert_list = MedicalExpert.query.order_by(MedicalExpert.last_name).all()
    slots = (
        Availability.query.filter(Availability.slot_date >= datetime.utcnow().date())
        .order_by(Availability.slot_date, Availability.start_time)
        .all()
    )
    return render_template("admin/schedules.html", experts=expert_list, slots=slots)


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

@admin_bp.route("/audit-logs")
def audit_logs():
    action = request.args.get("action", "").strip()
    query = AuditLog.query
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    logs = query.order_by(AuditLog.created_at.desc()).limit(300).all()
    return render_template("admin/audit_logs.html", logs=logs, action=action)
