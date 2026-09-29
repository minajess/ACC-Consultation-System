"""
Application factory for the Abuyog Community College Consultation System.

Using a factory function (rather than a module-level `app = Flask(...)`)
avoids circular imports between blueprints and extensions, and makes it easy
to create separate app instances for testing.
"""

import os
from flask import Flask, render_template

from config import config_by_name
from app.extensions import db, login_manager, csrf


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)

    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name[config_name])

    # Make sure the instance/ folder (where the SQLite file lives) exists
    os.makedirs(app.instance_path, exist_ok=True)

    # --- Initialize extensions ---
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # --- User loader for Flask-Login ---
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # --- Register blueprints ---
    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.student.routes import student_bp
    from app.medical.routes import medical_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(medical_bp, url_prefix="/medical")

    # --- Root route: send visitors to the right place ---
    from flask_login import current_user

    @app.route("/")
    def index():
        from flask import redirect, url_for

        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role == "super_admin":
            return redirect(url_for("admin.dashboard"))
        if current_user.role == "medical_expert":
            return redirect(url_for("medical.dashboard"))
        return redirect(url_for("student.dashboard"))

    # --- Error handlers ---
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        # Never leak internal exception details to the browser.
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # --- Template globals ---
    @app.context_processor
    def inject_notification_count():
        if current_user.is_authenticated:
            unread = current_user.notifications.filter_by(is_read=False).count()
        else:
            unread = 0
        return dict(unread_notification_count=unread)

    # --- CLI commands: `flask init-db` and `flask seed-db` ---
    from app.seed_helpers import register_cli_commands

    register_cli_commands(app)

    return app
