from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired


class StorageServiceForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    url = StringField("URL", validators=[DataRequired()])
    user_name = StringField("User name", validators=[DataRequired()])
    api_key = StringField("API key", validators=[DataRequired()])
    default = BooleanField("Default")
