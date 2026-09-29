from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField
from wtforms.validators import DataRequired, Length


CONSULTATION_TYPES = [
    ("General Check-up", "General Check-up"),
    ("Follow-up Consultation", "Follow-up Consultation"),
    ("Mental Health Consultation", "Mental Health Consultation"),
    ("Dental Concern", "Dental Concern"),
    ("Other", "Other"),
]


class ConsultationRequestForm(FlaskForm):
    expert_id = SelectField("Medical Expert", coerce=int, validators=[DataRequired()])
    availability_id = SelectField("Available Slot", coerce=int, validators=[DataRequired()])
    consultation_type = SelectField("Consultation Type", choices=CONSULTATION_TYPES, validators=[DataRequired()])
    reason = TextAreaField("Reason for Consultation", validators=[DataRequired(), Length(max=1000)])


class CancelForm(FlaskForm):
    """Empty form whose only job is to carry a valid CSRF token for a POST-only cancel button."""

    pass
