from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DateField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional


class StudentForm(FlaskForm):
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
    emergency_contact = StringField("Emergency Contact", validators=[DataRequired(), Length(max=120)])

    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Password (leave blank to keep current)", validators=[Optional(), Length(min=8, message="Minimum 8 characters.")]
    )
    is_active_account = BooleanField("Account Active", default=True)


class ExpertForm(FlaskForm):
    expert_id = StringField("Expert ID", validators=[DataRequired(), Length(max=30)])
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=80)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=80)])
    specialization = StringField("Specialization", validators=[DataRequired(), Length(max=120)])
    license_number = StringField("License Number", validators=[Optional(), Length(max=60)])
    contact_number = StringField("Contact Number", validators=[DataRequired(), Length(max=30)])

    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField(
        "Password (leave blank to keep current)", validators=[Optional(), Length(min=8, message="Minimum 8 characters.")]
    )
    is_active_account = BooleanField("Account Active", default=True)
