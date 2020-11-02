#!venv/bin/python

# chmod a+x create_aipscan.db.py
# ./create_aipscan.db.py

from AIPscan import db
from AIPscan.application import create_app

app = create_app()
app.app_context().push()
db.create_all()
