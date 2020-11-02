# -*- coding: utf-8 -*-

from flask import Blueprint, redirect, url_for

home = Blueprint("home", __name__)


@home.route("/", methods=["GET"])
def index():
    """Define handling for application's / route."""
    return redirect(url_for("aggregator.ss_default"))
