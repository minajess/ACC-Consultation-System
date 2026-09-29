from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, Student, ROLE_STUDENT, log_action
from app.auth.forms import LoginForm, RegisterForm
from app.utils import get_client_ip

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        # Look up the user; deliberately give the same generic error whether
        # the email doesn't exist or the password is wrong, so an attacker
        # can't use the login form to discover which emails are registered.
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()

        if user is None or not user.check_password(form.password.data):
            log_action(None, "login_failed", f"Failed login attempt for {form.email.data}", get_client_ip())
            db.session.commit()
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", form=form)

        if not user.is_active_account:
            log_action(user, "login_blocked", "Login attempt on a deactivated account.", get_client_ip())
            db.session.commit()
            flash("This account has been deactivated. Please contact the administrator.", "danger")
            return render_template("auth/login.html", form=form)

        login_user(user)
        log_action(user, "login", "User logged in.", get_client_ip())
        db.session.commit()
        flash(f"Welcome back, {user.display_name}!", "success")

        next_page = request.args.get("next")
        return redirect(next_page or url_for("index"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    log_action(current_user, "logout", "User logged out.", get_client_ip())
    db.session.commit()
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("auth/register.html", form=form)

        if Student.query.filter_by(student_id=form.student_id.data.strip()).first():
            flash("An account with that Student ID already exists.", "danger")
            return render_template("auth/register.html", form=form)

        user = User(email=email, role=ROLE_STUDENT, is_active_account=True)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # assigns user.id without ending the transaction

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
        log_action(user, "register", "New student self-registered.", get_client_ip())
        db.session.commit()

        flash("Account created successfully. You may now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)
