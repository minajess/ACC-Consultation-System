from datetime import datetime, date as date_cls

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import (
    Availability,
    Consultation,
    log_action,
    notify,
    ROLE_MEDICAL_EXPERT,
    STATUS_PENDING,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_RESCHEDULED,
    STATUS_COMPLETED,
)
from app.medical.forms import AvailabilityForm, RejectForm, RescheduleForm, CompleteForm
from app.utils import roles_required, get_client_ip

medical_bp = Blueprint("medical", __name__, template_folder="../templates/medical")


@medical_bp.before_request
@login_required
@roles_required(ROLE_MEDICAL_EXPERT)
def restrict_to_experts():
    pass


def _current_expert():
    if current_user.expert_profile is None:
        abort(404)
    return current_user.expert_profile


@medical_bp.route("/dashboard")
def dashboard():
    expert = _current_expert()
    today = date_cls.today()
    todays_consultations = expert.consultations.filter(
        Consultation.requested_date == today, Consultation.status.in_([STATUS_APPROVED, STATUS_RESCHEDULED])
    ).all()
    pending = expert.consultations.filter_by(status=STATUS_PENDING).order_by(Consultation.requested_date).all()
    upcoming = (
        expert.consultations.filter(Consultation.status.in_([STATUS_APPROVED, STATUS_RESCHEDULED]), Consultation.requested_date >= today)
        .order_by(Consultation.requested_date)
        .limit(10)
        .all()
    )
    completed_count = expert.consultations.filter_by(status=STATUS_COMPLETED).count()
    return render_template(
        "medical/dashboard.html",
        todays_consultations=todays_consultations,
        pending=pending,
        upcoming=upcoming,
        completed_count=completed_count,
    )


@medical_bp.route("/requests")
def requests_list():
    expert = _current_expert()
    status = request.args.get("status", "")
    query = expert.consultations
    if status:
        query = query.filter_by(status=status)
    consultation_list = query.order_by(Consultation.requested_date).all()
    return render_template("medical/requests.html", consultations=consultation_list, status=status)


def _get_owned_consultation(consultation_id):
    expert = _current_expert()
    consultation = Consultation.query.get_or_404(consultation_id)
    if consultation.expert_id != expert.id:
        abort(403)
    return consultation


@medical_bp.route("/requests/<int:consultation_id>")
def consultation_detail(consultation_id):
    consultation = _get_owned_consultation(consultation_id)
    reject_form = RejectForm()
    complete_form = CompleteForm()

    reschedule_form = RescheduleForm()
    open_slots = (
        Availability.query.filter_by(expert_id=consultation.expert_id, is_booked=False)
        .filter(Availability.slot_date >= date_cls.today())
        .order_by(Availability.slot_date, Availability.start_time)
        .all()
    )
    reschedule_form.availability_id.choices = [
        (s.id, f"{s.slot_date.strftime('%b %d, %Y')} — {s.start_time.strftime('%I:%M %p')}") for s in open_slots
    ]

    return render_template(
        "medical/consultation_detail.html",
        consultation=consultation,
        reject_form=reject_form,
        complete_form=complete_form,
        reschedule_form=reschedule_form,
    )


@medical_bp.route("/requests/<int:consultation_id>/approve", methods=["POST"])
def approve_consultation(consultation_id):
    consultation = _get_owned_consultation(consultation_id)
    if consultation.status != STATUS_PENDING:
        flash("Only pending requests can be approved.", "warning")
        return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))

    consultation.status = STATUS_APPROVED
    notify(consultation.student.user_id, f"Your consultation on {consultation.requested_date.strftime('%b %d, %Y')} was approved.")
    log_action(current_user, "approve_consultation", f"Approved consultation #{consultation.id}.", get_client_ip())
    db.session.commit()
    flash("Consultation approved.", "success")
    return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))


@medical_bp.route("/requests/<int:consultation_id>/reject", methods=["POST"])
def reject_consultation(consultation_id):
    consultation = _get_owned_consultation(consultation_id)
    form = RejectForm()
    if consultation.status != STATUS_PENDING:
        flash("Only pending requests can be rejected.", "warning")
        return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))

    if form.validate_on_submit():
        consultation.status = STATUS_REJECTED
        consultation.rejection_reason = form.rejection_reason.data.strip()
        if consultation.slot:
            consultation.slot.is_booked = False
        notify(
            consultation.student.user_id,
            f"Your consultation request on {consultation.requested_date.strftime('%b %d, %Y')} was rejected: {consultation.rejection_reason}",
        )
        log_action(current_user, "reject_consultation", f"Rejected consultation #{consultation.id}.", get_client_ip())
        db.session.commit()
        flash("Consultation rejected.", "info")
    else:
        flash("Please provide a reason for rejection.", "danger")
    return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))


@medical_bp.route("/requests/<int:consultation_id>/reschedule", methods=["POST"])
def reschedule_consultation(consultation_id):
    consultation = _get_owned_consultation(consultation_id)
    if consultation.status not in (STATUS_PENDING, STATUS_APPROVED):
        flash("This consultation cannot be rescheduled.", "warning")
        return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))

    form = RescheduleForm()
    open_slots = (
        Availability.query.filter_by(expert_id=consultation.expert_id, is_booked=False)
        .filter(Availability.slot_date >= date_cls.today())
        .all()
    )
    form.availability_id.choices = [(s.id, "") for s in open_slots]

    if form.validate_on_submit():
        new_slot = Availability.query.get(form.availability_id.data)
        if new_slot is None or new_slot.is_booked:
            flash("That slot is no longer available.", "danger")
            return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))

        old_slot = consultation.slot
        if old_slot:
            old_slot.is_booked = False

        new_slot.is_booked = True
        consultation.availability_id = new_slot.id
        consultation.requested_date = new_slot.slot_date
        consultation.requested_time = new_slot.start_time
        consultation.status = STATUS_RESCHEDULED

        notify(
            consultation.student.user_id,
            f"Your consultation was rescheduled to {new_slot.slot_date.strftime('%b %d, %Y')} at {new_slot.start_time.strftime('%I:%M %p')}.",
        )
        log_action(current_user, "reschedule_consultation", f"Rescheduled consultation #{consultation.id}.", get_client_ip())
        db.session.commit()
        flash("Consultation rescheduled.", "success")
    else:
        flash("Please select a valid new slot.", "danger")
    return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))


@medical_bp.route("/requests/<int:consultation_id>/complete", methods=["POST"])
def complete_consultation(consultation_id):
    consultation = _get_owned_consultation(consultation_id)
    form = CompleteForm()
    if consultation.status not in (STATUS_APPROVED, STATUS_RESCHEDULED):
        flash("Only approved consultations can be marked complete.", "warning")
        return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))

    if form.validate_on_submit():
        consultation.status = STATUS_COMPLETED
        consultation.notes = form.notes.data.strip()
        consultation.recommendation = (form.recommendation.data or "").strip() or None
        notify(consultation.student.user_id, f"Your consultation on {consultation.requested_date.strftime('%b %d, %Y')} has been completed.")
        log_action(current_user, "complete_consultation", f"Completed consultation #{consultation.id}.", get_client_ip())
        db.session.commit()
        flash("Consultation marked as completed.", "success")
    else:
        flash("Please add consultation notes before completing.", "danger")
    return redirect(url_for("medical.consultation_detail", consultation_id=consultation.id))


# ---------------------------------------------------------------------------
# Availability management
# ---------------------------------------------------------------------------

@medical_bp.route("/availability", methods=["GET", "POST"])
def availability():
    expert = _current_expert()
    form = AvailabilityForm()

    if form.validate_on_submit():
        start = datetime.strptime(form.start_time.data, "%H:%M").time()
        end = datetime.strptime(form.end_time.data, "%H:%M").time()

        if start >= end:
            flash("End time must be after start time.", "danger")
        elif form.slot_date.data < date_cls.today():
            flash("Cannot add availability for a past date.", "danger")
        elif Availability.query.filter_by(expert_id=expert.id, slot_date=form.slot_date.data, start_time=start).first():
            flash("You already have a slot starting at that time on that date.", "warning")
        else:
            db.session.add(Availability(expert_id=expert.id, slot_date=form.slot_date.data, start_time=start, end_time=end))
            log_action(current_user, "add_availability", f"Added availability slot on {form.slot_date.data}.", get_client_ip())
            db.session.commit()
            flash("Availability slot added.", "success")
        return redirect(url_for("medical.availability"))

    upcoming_slots = (
        Availability.query.filter_by(expert_id=expert.id)
        .filter(Availability.slot_date >= date_cls.today())
        .order_by(Availability.slot_date, Availability.start_time)
        .all()
    )
    return render_template("medical/availability.html", form=form, slots=upcoming_slots)


@medical_bp.route("/availability/<int:slot_id>/delete", methods=["POST"])
def delete_availability(slot_id):
    expert = _current_expert()
    slot = Availability.query.get_or_404(slot_id)
    if slot.expert_id != expert.id:
        abort(403)
    if slot.is_booked:
        flash("Cannot remove a slot that is already booked.", "warning")
        return redirect(url_for("medical.availability"))

    db.session.delete(slot)
    log_action(current_user, "delete_availability", f"Removed availability slot #{slot_id}.", get_client_ip())
    db.session.commit()
    flash("Availability slot removed.", "info")
    return redirect(url_for("medical.availability"))
