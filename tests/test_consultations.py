from app.models import Consultation, Availability, STATUS_PENDING, STATUS_APPROVED, STATUS_CANCELLED
from tests.conftest import login


def _submit_request(client, expert_id, slot_id, reason="Feeling unwell for two days."):
    return client.post(
        "/student/consultations/request",
        data={
            "expert_id": expert_id,
            "availability_id": slot_id,
            "consultation_type": "General Check-up",
            "reason": reason,
        },
        follow_redirects=True,
    )


def test_student_can_create_consultation_request(client, db, student_user, expert_user, open_slot):
    login(client, "student@example.com", "Student@12345")
    response = _submit_request(client, expert_user.expert_profile.id, open_slot.id)
    assert response.status_code == 200

    consultation = Consultation.query.first()
    assert consultation is not None
    assert consultation.status == STATUS_PENDING
    assert consultation.student_id == student_user.student_profile.id

    slot = Availability.query.get(open_slot.id)
    assert slot.is_booked is True


def test_double_booking_is_prevented(client, db, student_user, expert_user, open_slot):
    login(client, "student@example.com", "Student@12345")
    _submit_request(client, expert_user.expert_profile.id, open_slot.id)

    # A second attempt to book the SAME already-booked slot must be rejected,
    # and must not create a second consultation for that slot.
    response = _submit_request(client, expert_user.expert_profile.id, open_slot.id, reason="Trying again")
    assert response.status_code == 200

    consultations_for_slot = Consultation.query.filter_by(availability_id=open_slot.id).count()
    assert consultations_for_slot == 1


def test_medical_expert_can_approve_consultation(client, db, student_user, expert_user, open_slot):
    login(client, "student@example.com", "Student@12345")
    _submit_request(client, expert_user.expert_profile.id, open_slot.id)
    client.get("/logout")

    login(client, "expert@example.com", "Medical@12345")
    consultation = Consultation.query.first()
    response = client.post(f"/medical/requests/{consultation.id}/approve", follow_redirects=True)
    assert response.status_code == 200

    updated = Consultation.query.get(consultation.id)
    assert updated.status == STATUS_APPROVED


def test_expert_cannot_approve_another_experts_consultation(client, db, student_user, expert_user, open_slot):
    from app.models import User, MedicalExpert, ROLE_MEDICAL_EXPERT

    login(client, "student@example.com", "Student@12345")
    _submit_request(client, expert_user.expert_profile.id, open_slot.id)
    client.get("/logout")

    other_user = User(email="other-expert@example.com", role=ROLE_MEDICAL_EXPERT, is_active_account=True)
    other_user.set_password("Medical@12345")
    db.session.add(other_user)
    db.session.flush()
    other_expert = MedicalExpert(
        user_id=other_user.id,
        expert_id="EXP-TEST-2",
        first_name="Other",
        last_name="Expert",
        specialization="Dentistry",
        contact_number="0900-999-9999",
    )
    db.session.add(other_expert)
    db.session.commit()

    login(client, "other-expert@example.com", "Medical@12345")
    consultation = Consultation.query.first()
    response = client.post(f"/medical/requests/{consultation.id}/approve")
    assert response.status_code == 403


def test_student_can_cancel_pending_consultation(client, db, student_user, expert_user, open_slot):
    login(client, "student@example.com", "Student@12345")
    _submit_request(client, expert_user.expert_profile.id, open_slot.id)

    consultation = Consultation.query.first()
    response = client.post(f"/student/consultations/{consultation.id}/cancel", follow_redirects=True)
    assert response.status_code == 200

    updated = Consultation.query.get(consultation.id)
    assert updated.status == STATUS_CANCELLED

    # Cancelling should free up the slot again for other students.
    slot = Availability.query.get(open_slot.id)
    assert slot.is_booked is False


def test_student_cannot_cancel_another_students_consultation(client, db, student_user, expert_user, open_slot):
    from app.models import User, Student, ROLE_STUDENT
    from datetime import date

    login(client, "student@example.com", "Student@12345")
    _submit_request(client, expert_user.expert_profile.id, open_slot.id)
    client.get("/logout")

    other_user = User(email="other-student@example.com", role=ROLE_STUDENT, is_active_account=True)
    other_user.set_password("Student@12345")
    db.session.add(other_user)
    db.session.flush()
    other_student = Student(
        user_id=other_user.id,
        student_id="2026-00002",
        first_name="Other",
        last_name="Student",
        sex="Female",
        date_of_birth=date(2004, 6, 6),
        contact_number="0900-777-7777",
        course="BSIT",
        year_level="2nd Year",
        address="Leyte",
        emergency_contact="Parent - 0900-888-8888",
    )
    db.session.add(other_student)
    db.session.commit()

    login(client, "other-student@example.com", "Student@12345")
    consultation = Consultation.query.first()
    response = client.post(f"/student/consultations/{consultation.id}/cancel")
    assert response.status_code == 403
