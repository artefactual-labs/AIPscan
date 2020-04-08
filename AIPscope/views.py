from flask import Flask, render_template
from AIPscope import app, db


@app.route("/")
def home():
    return render_template("fetch_jobs.html")
