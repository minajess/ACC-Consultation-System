"""
Central place to create Flask extension instances.

Creating them here (without binding to an app yet) avoids circular imports:
models.py can import `db`, and blueprints can import `login_manager`, while
the actual app object is only built once, inside the application factory in
app/__init__.py.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# Where Flask-Login sends anonymous users who hit a @login_required route
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"
