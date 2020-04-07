from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from config import DevConfig

app = Flask(__name__)
app.config.from_object(DevConfig)
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(255))
    password = db.Column(db.String(255))


def __init__(self, username):
    self.username = username


def __repr__(self):
    return "<User '{}'>".format(self.username)


@app.route("/")
def home():
    return render_template("home.html")


if __name__ == "__main__":
    app.run()
