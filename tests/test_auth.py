from datetime import date

from app.models import User, Student, ROLE_STUDENT
from tests.conftest import login


def test_password_is_hashed_not_plaintext(db):
    user = User(email="hash@example.com", role=ROLE_STUDENT)
    user.set_password("PlainText123")
    assert user.password_hash != "PlainText123"
    assert user.check_password("PlainText123")
    assert not user.check_password("WrongPassword")


def test_student_self_registration(client, db):
    response = client.post(
        "/register",
        data={
            "student_id": "2026-99999",
            "first_name": "New",
            "middle_name": "",
            "last_name": "Student",
            "sex": "Female",
            "date_of_birth": "2005-03-10",
            "contact_number": "0900-333-4444",
            "course": "BSIT",
            "year_level": "1st Year",
            "address": "Abuyog, Leyte",
            "emergency_contact": "Guardian - 0900-555-6666",
            "email": "newstudent@example.com",
            "password": "SecurePass1",
            "confirm_password": "SecurePass1",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    user = User.query.filter_by(email="newstudent@example.com").first()
    assert user is not None
    assert user.role == ROLE_STUDENT
    assert Student.query.filter_by(student_id="2026-99999").first() is not None


def test_login_and_logout(client, student_user):
    response = login(client, "student@example.com", "Student@12345")
    assert response.status_code == 200
    assert b"Welcome back" in response.data or b"Dashboard" in response.data or response.request.path != "/login"

    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200


def test_login_fails_with_wrong_password(client, student_user):
    response = login(client, "student@example.com", "WrongPassword")
    assert response.status_code == 200
    assert response.request.path == "/login"


def test_deactivated_account_cannot_login(client, db, student_user):
    student_user.is_active_account = False
    db.session.commit()
    response = login(client, "student@example.com", "Student@12345")
    assert response.status_code == 200
    assert response.request.path == "/login"


def test_unauthenticated_user_redirected_to_login(client):
    response = client.get("/student/dashboard", follow_redirects=True)
    assert response.request.path == "/login"


def test_student_cannot_access_admin_routes(client, student_user):
    login(client, "student@example.com", "Student@12345")
    response = client.get("/admin/dashboard")
    assert response.status_code == 403


def test_expert_cannot_access_admin_routes(client, expert_user):
    login(client, "expert@example.com", "Medical@12345")
    response = client.get("/admin/dashboard")
    assert response.status_code == 403


def test_admin_can_access_admin_dashboard(client, admin_user):
    login(client, "admin@example.com", "Admin@12345")
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
