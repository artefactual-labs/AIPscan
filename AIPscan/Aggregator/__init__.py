# -*- coding: utf-8 -*-

from AIPscan import db

# Setup and create database if it doesn't exist. If it does exist, the
# create_all() function will only create the tables which don't exist.
db.create_all()
