# models.py
from datetime import datetime
import hashlib, uuid
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def generate_user_code():
    return uuid.uuid4().hex[:6]

def generate_direct_referral():
    return "direct-" + uuid.uuid4().hex[:6]

def hash_referral_id(referral_id):
    if not referral_id:
        return None
    return hashlib.sha256(referral_id.encode()).hexdigest()

class UniqueUser(db.Model):
    __tablename__ = 'unique_user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_code = db.Column(db.String(20), nullable=False, unique=True, default=generate_user_code)
    name = db.Column(db.String(100), nullable=False)
    referral_id = db.Column(db.String(64), nullable=False, unique=True)
    responses = db.relationship('SurveyResponse', backref='unique_user', lazy=True)

class SurveyResponse(db.Model):
    __tablename__ = 'survey_response'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    unique_user_id = db.Column(db.Integer, db.ForeignKey('unique_user.id'), nullable=False)
    referral_id = db.Column(db.String(64), nullable=False, default="direct")
    age = db.Column(db.String(20), nullable=False, default='-')
    gender = db.Column(db.String(20), nullable=True)
    other_data = db.Column(db.Text, nullable=True)
    tracking_data = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=True, default="Completed")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    device_type = db.Column(db.String(20), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    region = db.Column(db.String(100), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    day_experience = db.Column(db.String(50), nullable=True)

class CustomerAction(db.Model):
    __tablename__ = 'customer_action'
    id = db.Column(db.Integer, primary_key=True)
    unique_user_id = db.Column(db.Integer, nullable=True)
    action_type = db.Column(db.String(20), nullable=False)
    referral_id = db.Column(db.String(64), nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
