from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object("config")
db = SQLAlchemy(app)

from celery import Celery
from flask_celery import make_celery

celery = make_celery(app)

from AIPscan import views, models, tasks
