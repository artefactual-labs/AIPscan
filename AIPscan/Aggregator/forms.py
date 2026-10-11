from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms import IntegerField
from wtforms import StringField
from wtforms.validators import DataRequired
from wtforms.validators import InputRequired
from wtforms.validators import NumberRange
from wtforms.widgets import PasswordInput


class StorageServiceForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    url = StringField("URL", validators=[DataRequired()])
    user_name = StringField("User name", validators=[DataRequired()])
    api_key = StringField(
        "API key", validators=[DataRequired()], widget=PasswordInput(hide_value=False)
    )
    download_limit = IntegerField(
        "Download limit", default=20, validators=[InputRequired(), NumberRange(min=1)]
    )
    download_offset = IntegerField(
        "Download offset", default=0, validators=[InputRequired(), NumberRange(min=0)]
    )
    default = BooleanField("Default")
