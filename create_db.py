from config import SQLALCHEMY_DATABASE_URI
from AIPscope import db
import os.path

db.create_all()
