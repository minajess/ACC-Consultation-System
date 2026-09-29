from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DateField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired()])


class RegisterForm(FlaskForm):
    """Self-registration is only available to students, per the spec."""

    student_id = StringField("Student ID", validators=[DataRequired(), Length(max=30)])
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    middle_name = StringField("Middle Name", validators=[Optional(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    sex = SelectField("Sex", choices=[("Male", "Male"), ("Female", "Female")], validators=[DataRequired()])
    date_of_birth = DateField("Date of Birth", validators=[DataRequired()])
    contact_number = StringField("Contact Number", validators=[DataRequired(), Length(max=30)])
    course = StringField("Course / Program", validators=[DataRequired(), Length(max=120)])
    year_level = SelectField(
        "Year Level",
        choices=[("1st Year", "1st Year"), ("2nd Year", "2nd Year"), ("3rd Year", "3rd Year"), ("4th Year", "4th Year")],
        validators=[DataRequired()],
    )
    address = StringField("Address", validators=[DataRequired(), Length(max=255)])
    emergency_contact = StringField("Emergency Contact (name - number)", validators=[DataRequired(), Length(max=120)])

    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters long.")],
    )
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
