from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (
    MedicalExpert,
    Availability,
    Consultation,
    Notification,
    log_action,
    notify,
    ROLE_STUDENT,
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_RESCHEDULED,
    STATUS_CANCELLED,
)
from app.student.forms import ConsultationRequestForm, CancelForm
from app.utils import roles_required, get_client_ip

student_bp = Blueprint("student", __name__, template_folder="../templates/student")


@student_bp.before_request
@login_required
@roles_required(ROLE_STUDENT)
def restrict_to_students():
    pass


def _current_student():
    """The Student profile row for the logged-in user, or 404."""
    if current_user.student_profile is None:
        abort(404)
    return current_user.student_profile


@student_bp.route("/dashboard")
def dashboard():
    student = _current_student()
    upcoming = (
        student.consultations.filter(Consultation.status.in_([STATUS_APPROVED, STATUS_RESCHEDULED]))
        .order_by(Consultation.requested_date)
        .first()
    )
    pending_count = student.consultations.filter_by(status=STATUS_PENDING).count()
    history = student.consultations.order_by(Consultation.created_at.desc()).limit(5).all()
    recent_notifications = current_user.notifications.order_by(Notification.created_at.desc()).limit(5).all()
    return render_template(
        "student/dashboard.html",
        upcoming=upcoming,
        pending_count=pending_count,
        history=history,
        notifications=recent_notifications,
    )


@student_bp.route("/consultations/request", methods=["GET", "POST"])
def request_consultation():
    student = _current_student()
    form = ConsultationRequestForm()

    experts = MedicalExpert.query.join(MedicalExpert.user).filter_by(is_active_account=True).order_by(MedicalExpert.last_name).all()
    form.expert_id.choices = [(e.id, f"Dr. {e.full_name} — {e.specialization}") for e in experts]

    # Populate available slots for the currently selected (or first) expert
    selected_expert_id = request.values.get("expert_id", type=int) or (experts[0].id if experts else None)
    open_slots = (
        Availability.query.filter_by(expert_id=selected_expert_id, is_booked=False)
        .filter(Availability.slot_date >= datetime.utcnow().date())
        .order_by(Availability.slot_date, Availability.start_time)
        .all()
        if selected_expert_id
        else []
    )
    form.availability_id.choices = [
        (s.id, f"{s.slot_date.strftime('%b %d, %Y')} — {s.start_time.strftime('%I:%M %p')} to {s.end_time.strftime('%I:%M %p')}")
        for s in open_slots
    ]

    if not experts:
        flash("No active medical experts are available right now. Please try again later.", "warning")

    if form.validate_on_submit():
        slot = Availability.query.get(form.availability_id.data)

        # Re-check the slot right before booking to prevent a race condition
        # where two students submit for the same slot at nearly the same time.
        if slot is None or slot.is_booked or slot.expert_id != form.expert_id.data:
            flash("That time slot is no longer available. Please choose another.", "danger")
            return redirect(url_for("student.request_consultation"))

        slot.is_booked = True
        consultation = Consultation(
            student_id=student.id,
            expert_id=slot.expert_id,
            availability_id=slot.id,
            consultation_type=form.consultation_type.data,
            requested_date=slot.slot_date,
            requested_time=slot.start_time,
            reason=form.reason.data.strip(),
            status=STATUS_PENDING,
        )
        db.session.add(consultation)
        db.session.flush()

        notify(slot.expert.user_id, f"New consultation request from {student.full_name} on {slot.slot_date.strftime('%b %d, %Y')}.")
        log_action(current_user, "request_consultation", f"Requested consultation with expert #{slot.expert_id}.", get_client_ip())
        db.session.commit()

        flash("Consultation request submitted. You will be notified once it is reviewed.", "success")
        return redirect(url_for("student.my_consultations"))

    return render_template("student/request_consultation.html", form=form, experts=experts, selected_expert_id=selected_expert_id)


@student_bp.route("/consultations")
def my_consultations():
    student = _current_student()
    status = request.args.get("status", "")
    query = student.consultations
    if status:
        query = query.filter_by(status=status)
    consultation_list = query.order_by(Consultation.created_at.desc()).all()
    cancel_form = CancelForm()
    return render_template("student/my_consultations.html", consultations=consultation_list, status=status, cancel_form=cancel_form)


@student_bp.route("/consultations/<int:consultation_id>/cancel", methods=["POST"])
def cancel_consultation(consultation_id):
    student = _current_student()
    consultation = Consultation.query.get_or_404(consultation_id)

    if consultation.student_id != student.id:
        abort(403)
    if consultation.status not in (STATUS_PENDING, STATUS_APPROVED, STATUS_RESCHEDULED):
        flash("This consultation can no longer be cancelled.", "warning")
        return redirect(url_for("student.my_consultations"))

    consultation.status = STATUS_CANCELLED
    if consultation.slot:
        consultation.slot.is_booked = False

    notify(consultation.expert.user_id, f"{student.full_name} cancelled their consultation on {consultation.requested_date.strftime('%b %d, %Y')}.")
    log_action(current_user, "cancel_consultation", f"Cancelled consultation #{consultation.id}.", get_client_ip())
    db.session.commit()

    flash("Consultation cancelled.", "info")
    return redirect(url_for("student.my_consultations"))


@student_bp.route("/profile")
def profile():
    student = _current_student()
    return render_template("student/profile.html", student=student)


@student_bp.route("/notifications")
def notifications():
    items = current_user.notifications.order_by(Notification.created_at.desc()).all()
    for n in items:
        n.is_read = True
    db.session.commit()
    return render_template("student/notifications.html", notifications=items)
