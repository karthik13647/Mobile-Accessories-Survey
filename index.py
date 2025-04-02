from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import hashlib
import uuid
import json
from datetime import datetime

# Create a Blueprint for the main index
index_bp = Blueprint('index_bp', __name__)

# Initialize a separate SQLAlchemy instance
db = SQLAlchemy()

# Predefined referral links and their codes
REFERRAL_LINKS = {
    'special-offer-1': 'LINK001',
    'vip-access': 'LINK002',
    'exclusive-deal': 'LINK003',
    'premium-survey': 'LINK004',
    'member-special': 'LINK005',
    'limited-time': 'LINK006',
    'early-access': 'LINK007',
    'priority-user': 'LINK008',
    'special-member': 'LINK009',
    'vip-member': 'LINK010'
}

def hash_referral_id(referral_id):
    """Generate a SHA256 hash for the referral ID."""
    if not referral_id:
        return None
    return hashlib.sha256(referral_id.encode()).hexdigest()

def generate_user_code():
    """Generate a short unique user code (e.g., def456)."""
    return uuid.uuid4().hex[:6]  # use the first 6 hex digits

def generate_direct_referral():
    """Generate a unique referral id for direct access users."""
    return "direct-" + uuid.uuid4().hex[:6]

class UniqueUser(db.Model):
    __tablename__ = 'unique_user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # A user-friendly unique code for display (e.g., def456)
    user_code = db.Column(db.String(20), nullable=False, unique=True, default=generate_user_code)
    name = db.Column(db.String(100), nullable=False)
    referral_id = db.Column(db.String(64), nullable=False, unique=True)  # Store hashed referral ID or direct id

    # Relationship to Survey Responses
    responses = db.relationship('SurveyResponseIndex', backref='unique_user', lazy=True)

class SurveyResponseIndex(db.Model):
    __tablename__ = 'survey_response'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # Every survey response is linked to a UniqueUser
    unique_user_id = db.Column(db.Integer, db.ForeignKey('unique_user.id'), nullable=False)
    # referral_id field to record the referral (or direct) identifier
    referral_id = db.Column(db.String(64), nullable=False, default="direct")
    
    # Survey details – note that age is stored in a dedicated column
    age = db.Column(db.String(20), nullable=False, default='-')
    # Other responses are stored as a JSON string in other_data
    other_data = db.Column(db.Text, nullable=True)
    
    # Survey status: Set to "Completed" on form submission.
    status = db.Column(db.String(50), nullable=True, default="Completed")
    # Timestamp for when the survey was submitted
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class CustomerAction(db.Model):
    __tablename__ = 'customer_action'
    id = db.Column(db.Integer, primary_key=True)
    unique_user_id = db.Column(db.Integer, nullable=True)   # Stores the UniqueUser id
    action_type = db.Column(db.String(20), nullable=False)    # e.g., 'Clicked' or 'Completed'
    referral_id = db.Column(db.String(64), nullable=False)    # Referral identifier (hashed or direct)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

# Referral redirect route: logs a "Clicked" action and creates a UniqueUser if needed.
@index_bp.route('/<referral_link>', methods=['GET'])
def referral_redirect(referral_link):
    if referral_link in REFERRAL_LINKS:
        referral_code = REFERRAL_LINKS[referral_link]
        hashed_referral = hash_referral_id(referral_code)
        unique_user = UniqueUser.query.filter_by(referral_id=hashed_referral).first()
        if not unique_user:
            # Create a UniqueUser for the referral click event.
            unique_user = UniqueUser(name="Referral User", referral_id=hashed_referral)
            try:
                db.session.add(unique_user)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return f"Error creating user: {str(e)}", 500
        # Log the "Clicked" event
        new_action = CustomerAction(
            unique_user_id=unique_user.id,
            action_type="Clicked",
            referral_id=hashed_referral
        )
        try:
            db.session.add(new_action)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"Error logging action: {str(e)}", 500
        # Save referral_code in session so the form knows it came from a referral
        session['referral_code'] = referral_code
        return redirect(url_for('index_bp.index'))
    return "Invalid referral link", 404

# Main page route: handles form submission for survey responses.
@index_bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # --- Retrieve new form fields from the Premium Mobile Accessories Survey ---
        # Note: Some fields are checkboxes so use getlist for those arrays.
        mood = request.form.get('mood')
        special = request.form.get('special')
        productivity = request.form.getlist('productivity[]')
        accessories_love = request.form.getlist('accessoriesLove[]')
        accessories_dislike = request.form.getlist('accessoriesDislike[]')
        quality_brand = request.form.get('quality_brand')
        quality_material = request.form.get('quality_material')
        quality_design = request.form.get('quality_design')
        quality_durability = request.form.get('quality_durability')
        quality_features = request.form.get('quality_features')
        quality_warranty = request.form.get('quality_warranty')
        quality_fit = request.form.get('quality_fit')
        quality_eco = request.form.get('quality_eco')
        phonecase_value = request.form.get('phonecase_value')
        music_pick = request.form.getlist('music_pick[]')
        spend = request.form.get('spend')
        age = request.form.get('age') or '-'  # This also goes to the SurveyResponseIndex.age column

        # Bundle all additional responses into a dictionary and convert to JSON.
        additional_info = {
            "mood": mood,
            "special": special,
            "productivity": productivity,
            "accessoriesLove": accessories_love,
            "accessoriesDislike": accessories_dislike,
            "quality_brand": quality_brand,
            "quality_material": quality_material,
            "quality_design": quality_design,
            "quality_durability": quality_durability,
            "quality_features": quality_features,
            "quality_warranty": quality_warranty,
            "quality_fit": quality_fit,
            "quality_eco": quality_eco,
            "phonecase_value": phonecase_value,
            "music_pick": music_pick,
            "spend": spend
        }
        other_data_json = json.dumps(additional_info)

        # Since the new HTML does not include a name field, use a default value.
        name = "Anonymous"

        # Check if there is a referral code in session.
        referral_code = session.pop('referral_code', None)
        if referral_code:
            hashed_referral = hash_referral_id(referral_code)
            unique_user = UniqueUser.query.filter_by(referral_id=hashed_referral).first()
            if not unique_user:
                unique_user = UniqueUser(name=name, referral_id=hashed_referral)
                try:
                    db.session.add(unique_user)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    return f"Error creating user: {str(e)}", 500
            unique_user_id = unique_user.id
            final_referral = hashed_referral
        else:
            # Direct access: generate a unique referral id.
            direct_ref = generate_direct_referral()
            unique_user = UniqueUser(name=name, referral_id=direct_ref)
            try:
                db.session.add(unique_user)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return f"Error creating user: {str(e)}", 500
            unique_user_id = unique_user.id
            final_referral = direct_ref

        # Create a new survey response with status "Completed"
        new_response = SurveyResponseIndex(
            unique_user_id=unique_user_id,
            referral_id=final_referral,
            age=age,
            other_data=other_data_json,
            status="Completed"
        )
        try:
            db.session.add(new_response)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"Error saving survey response: {str(e)}", 500

        return redirect(url_for('index_bp.responses'))

    return render_template('index.html')

# Route to view all survey responses.
@index_bp.route('/responses')
def responses():
    responses = SurveyResponseIndex.query.all()
    return render_template('response1.html', responses=responses)
