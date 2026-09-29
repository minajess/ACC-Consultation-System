from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, TextAreaField, StringField
from wtforms.validators import DataRequired, Length, Optional


HOUR_CHOICES = [(f"{h:02d}:00", f"{h:02d}:00") for h in range(6, 20)] + [(f"{h:02d}:30", f"{h:02d}:30") for h in range(6, 20)]
HOUR_CHOICES = sorted(set(HOUR_CHOICES))


class AvailabilityForm(FlaskForm):
    slot_date = DateField("Date", validators=[DataRequired()])
    start_time = SelectField("Start Time", choices=HOUR_CHOICES, validators=[DataRequired()])
    end_time = SelectField("End Time", choices=HOUR_CHOICES, validators=[DataRequired()])


class RejectForm(FlaskForm):
    rejection_reason = TextAreaField("Reason for Rejection", validators=[DataRequired(), Length(max=255)])


class RescheduleForm(FlaskForm):
    availability_id = SelectField("New Slot", coerce=int, validators=[DataRequired()])


class CompleteForm(FlaskForm):
    notes = TextAreaField("Consultation Notes", validators=[DataRequired(), Length(max=2000)])
    recommendation = TextAreaField("Recommendation", validators=[Optional(), Length(max=2000)])
