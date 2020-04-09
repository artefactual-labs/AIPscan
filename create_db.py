from config import SQLALCHEMY_DATABASE_URI
from AIPscan import db
import os.path

db.create_all()
