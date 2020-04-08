from flask import Flask, render_template
from AIPscope import app, db
from .models import fetch_jobs, storage_services
from .add_sample_data import adddata


@app.route("/")
def home():
    metsFetchJobs = fetch_jobs.query.all()
    return render_template("list_fetch_jobs.html", metsFetchJobs=metsFetchJobs)


@app.route("/add_sample_data")
def add_sample_data():
    adddata()
    return render_template("add_sample_data.html")
