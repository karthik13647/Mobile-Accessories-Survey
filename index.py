from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import hashlib, uuid, json
from datetime import datetime
import requests
from sqlalchemy import text

# Create a Blueprint for the main index
index_bp = Blueprint('index_bp', __name__)
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
    if not referral_id:
        return None
    return hashlib.sha256(referral_id.encode()).hexdigest()

def generate_user_code():
    return uuid.uuid4().hex[:6]

def generate_direct_referral():
    return "direct-" + uuid.uuid4().hex[:6]

def get_ip_info():
    try:
        ip_response = requests.get('https://api.ipify.org?format=json')
        ip_address = ip_response.json().get('ip')
        location_response = requests.get(f'http://ip-api.com/json/{ip_address}')
        location_data = location_response.json()
        if location_data.get('status') == 'success':
            return {
                'ip_address': ip_address,
                'country': location_data.get('country'),
                'city': location_data.get('city'),
                'region': location_data.get('regionName'),
                'latitude': location_data.get('lat'),
                'longitude': location_data.get('lon')
            }
    except Exception as e:
        print(f"Error getting IP info: {e}")
    return None

# --------------------------
# Functions to Update/Migrate Table Columns
# --------------------------
def add_day_experience_column():
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE survey_response ADD COLUMN day_experience VARCHAR(50)"))
            conn.commit()
    except Exception as e:
        # Column might already exist
        print(f"Note (day_experience): {e}")

def add_device_type_column():
    try:
        with db.engine.connect() as conn:
            conn.execute(text("ALTER TABLE survey_response ADD COLUMN device_type VARCHAR(20)"))
            conn.commit()
    except Exception as e:
        print(f"Note (device_type): {e}")

def add_location_tracking_columns():
    try:
        with db.engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE survey_response 
                ADD COLUMN ip_address VARCHAR(45),
                ADD COLUMN country VARCHAR(100),
                ADD COLUMN city VARCHAR(100),
                ADD COLUMN region VARCHAR(100),
                ADD COLUMN latitude FLOAT,
                ADD COLUMN longitude FLOAT
            """))
            conn.commit()
    except Exception as e:
        print(f"Note (location tracking): {e}")

def migrate_table_with_new_columns():
    try:
        with db.engine.connect() as conn:
            # Create a temporary table with all the required columns.
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS survey_response_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unique_user_id INTEGER NOT NULL,
                    referral_id VARCHAR(64) NOT NULL DEFAULT 'direct',
                    age VARCHAR(20) NOT NULL DEFAULT '-',
                    gender VARCHAR(20),
                    other_data TEXT,
                    tracking_data TEXT,
                    status VARCHAR(50) DEFAULT 'Completed',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    device_type VARCHAR(20),
                    ip_address VARCHAR(45),
                    country VARCHAR(100),
                    city VARCHAR(100),
                    region VARCHAR(100),
                    latitude FLOAT,
                    longitude FLOAT,
                    day_experience VARCHAR(50)
                )
            """))
            # Copy data from the old table to the new one.
            conn.execute(text("""
                INSERT INTO survey_response_new 
                (id, unique_user_id, referral_id, age, gender, other_data, tracking_data, status, timestamp, device_type, ip_address, country, city, region, latitude, longitude, day_experience)
                SELECT id, unique_user_id, referral_id, age, NULL, other_data, tracking_data, status, timestamp, device_type, ip_address, country, city, region, latitude, longitude, NULL
                FROM survey_response
            """))
            # Drop the old table.
            conn.execute(text("DROP TABLE survey_response"))
            # Rename the new table to the original name.
            conn.execute(text("ALTER TABLE survey_response_new RENAME TO survey_response"))
            conn.commit()
            print("Table migrated successfully with new columns")
    except Exception as e:
        print(f"Error migrating table: {e}")
        # Optionally, attempt to rollback by dropping the temporary table.
        try:
            with db.engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS survey_response_new"))
                conn.commit()
        except:
            pass

def init_db(app):
    with app.app_context():
        db.create_all()
        # Uncomment any or all of these functions as needed for your migration:
        # add_day_experience_column()
        # add_device_type_column()
        # add_location_tracking_columns()
        # migrate_table_with_new_columns()

# --------------------------
# Database Models
# --------------------------
class UniqueUser(db.Model):
    __tablename__ = 'unique_user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_code = db.Column(db.String(20), nullable=False, unique=True, default=generate_user_code)
    name = db.Column(db.String(100), nullable=False)
    referral_id = db.Column(db.String(64), nullable=False, unique=True)
    responses = db.relationship('SurveyResponseIndex', backref='unique_user', lazy=True)

class SurveyResponseIndex(db.Model):
    __tablename__ = 'survey_response'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    unique_user_id = db.Column(db.Integer, db.ForeignKey('unique_user.id'), nullable=False)
    referral_id = db.Column(db.String(64), nullable=False, default="direct")
    age = db.Column(db.String(20), nullable=False, default='-')
    gender = db.Column(db.String(20), nullable=True)  # New field for gender
    other_data = db.Column(db.Text, nullable=True)
    # New column to store tracking data (JSON string with field interactions and drop-off info)
    tracking_data = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), nullable=True, default="Completed")
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # New columns for device and location information, and day_experience
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

# --------------------------
# Routes
# --------------------------
@index_bp.route('/<referral_link>', methods=['GET'])
def referral_redirect(referral_link):
    if referral_link in REFERRAL_LINKS:
        referral_code = REFERRAL_LINKS[referral_link]
        hashed_referral = hash_referral_id(referral_code)
        unique_user = UniqueUser.query.filter_by(referral_id=hashed_referral).first()
        if not unique_user:
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
        session['referral_code'] = referral_code
        return redirect(url_for('index_bp.index'))
    return "Invalid referral link", 404

@index_bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # -------------------------------
        # Retrieve Survey Responses from the Form
        # -------------------------------
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
        age = request.form.get('age') or '-'
        
        # Retrieve gender and dayExperience from the form
        gender = request.form.get('gender')
        day_experience = request.form.get('dayExperience')
        
        # Retrieve device type from the form (ensure your form includes a field named "deviceType")
        device_type = request.form.get('deviceType')

        # Bundle additional info into a dictionary
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

        # Retrieve tracking data (time spent & field interactions) from the form
        tracking_data = request.form.get('trackingData')

        # Use a default name (since the form doesn't capture a name)
        name = "Anonymous"

        # -------------------------------
        # Check for Referral Code in Session and Create UniqueUser
        # -------------------------------
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

        # Get IP and location information
        ip_info = get_ip_info()

        # -------------------------------
        # Create and Save the Survey Response with Tracking Data and Device/Location Info
        # -------------------------------
        new_response = SurveyResponseIndex(
            unique_user_id=unique_user_id,
            referral_id=final_referral,
            age=age,
            gender=gender,                    # Save gender
            other_data=other_data_json,
            tracking_data=tracking_data,      # Save tracking (field interaction & drop-off) info here
            status="Completed",
            device_type=device_type,
            ip_address=ip_info['ip_address'] if ip_info else None,
            country=ip_info['country'] if ip_info else None,
            city=ip_info['city'] if ip_info else None,
            region=ip_info['region'] if ip_info else None,
            latitude=ip_info['latitude'] if ip_info else None,
            longitude=ip_info['longitude'] if ip_info else None,
            day_experience=day_experience      # Save day experience
        )
        try:
            db.session.add(new_response)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"Error saving survey response: {str(e)}", 500

        return redirect(url_for('index_bp.responses'))

    return render_template('index.html')

@index_bp.route('/responses')
def responses():
    responses = SurveyResponseIndex.query.all()
    return render_template('response1.html', responses=responses)
