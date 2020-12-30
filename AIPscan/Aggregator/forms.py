# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField
from wtforms.validators import DataRequired


class StorageServiceForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    url = StringField("URL", validators=[DataRequired()])
    user_name = StringField("User name", validators=[DataRequired()])
    api_key = StringField("API key", validators=[DataRequired()])
    download_limit = StringField("Download limit", default="20")
    download_offset = StringField("Download offset", default="0")
    default = BooleanField("Default")
