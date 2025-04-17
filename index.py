from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from flask_sqlalchemy import SQLAlchemy
import hashlib, uuid, json
from datetime import datetime
import requests
from sqlalchemy import text
from flask_mail import Mail, Message
from dotenv import load_dotenv
import os
import random
import pandas as pd
from sqlalchemy import create_engine

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'Envs.env'))

# Initialize Flask-Mail
mail = Mail()
# Create a Blueprint for the main index
index_bp = Blueprint('index_bp', __name__)
db = SQLAlchemy()

# Predefined referral links and their codes
REFERRAL_LINKS = {
    'uiengineer': 'karthik@pepeleads.com',
    'dataengineer': 'jayant.a@pepeleads.com',
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

def send_payload_to_remote(data):
    """
    Sends a JSON payload to the remote server. Returns the response text (expected "OK" or "error").
    """
    remote_server_url = os.getenv("REMOTE_SERVER_URL", "http://127.0.0.1:5000/responses")
    try:
        response = requests.post(remote_server_url, json=data, timeout=5)
        result_text = response.text.strip()
        print("Remote server responded:", result_text)
        return result_text
    except Exception as e:
        print("Error sending payload:", e)
        return "error"

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
def update_json_file():
    """
    Update the local JSON file with current survey responses.
    (Return True if the file updated correctly; otherwise, False.)
    """
    try:
        # Your code to update 'survey_responses.json'
        # For example: fetching data from the database and writing to the file.
        # Here we assume the file is updated successfully.
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to update JSON file: {e}")
        return False

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
            conn.execute(text("""
                INSERT INTO survey_response_new 
                (id, unique_user_id, referral_id, age, gender, other_data, tracking_data, status, timestamp, device_type, ip_address, country, city, region, latitude, longitude, day_experience)
                SELECT id, unique_user_id, referral_id, age, NULL, other_data, tracking_data, status, timestamp, device_type, ip_address, country, city, region, latitude, longitude, NULL
                FROM survey_response
            """))
            conn.execute(text("DROP TABLE survey_response"))
            conn.execute(text("ALTER TABLE survey_response_new RENAME TO survey_response"))
            conn.commit()
            print("Table migrated successfully with new columns")
    except Exception as e:
        print(f"Error migrating table: {e}")
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
# Additional Methods to Send the JSON File to a Remote Server
# --------------------------
def send_json_file_payload(json_file_path, target_url):
    """
    Load the JSON data from the file and POST it directly to the target URL.
    """
    try:
        # Load the contents of the JSON file.
        with open(json_file_path, 'r') as f:
            data = json.load(f)

        # Send the entire JSON data as a single POST request.
        response = requests.post(target_url, json=data)
        current_app.logger.info(
            f"Sent JSON file to {target_url}. Response: {response.status_code}, {response.text}"
        )
    except Exception as e:
        current_app.logger.error(f"Error sending JSON file: {e}")



def send_json_file_attachment(json_file_path, target_url):
    """
    Sends the JSON file as a file attachment.
    """
    try:
        with open(json_file_path, 'rb') as f:
            files = {'file': ('survey_responses.json', f, 'application/json')}
            response = requests.post(target_url, files=files)
        current_app.logger.info("Response from sending JSON attachment: %s", response.text)
        return response
    except Exception as e:
        current_app.logger.error("Error sending JSON attachment: %s", e)
        return None

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

# --------------------------
# Routes
# --------------------------
@index_bp.route('/<referral_link>', methods=['GET'])
def referral_redirect(referral_link):
    if referral_link in REFERRAL_LINKS:
        referral_code = REFERRAL_LINKS[referral_link]
        hashed_referral = hash_referral_id(referral_code)
        recipient_email = referral_code  # Since REFERRAL_LINKS values are emails
        
        # Send email notification
        try:
            msg = Message(
                subject="New Referral Link Click",
                recipients=[recipient_email],
                body=f"Your referral link '{referral_link}' was clicked!",
                sender=os.getenv('MAIL_DEFAULT_SENDER')
            )
            mail.send(msg)
        except Exception as e:
            print(f"Error sending email: {str(e)}")
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
            tracking_data=tracking_data,      # Save tracking info (field interaction & drop-off)
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

        # -------------------------------
        # Send JSON payload to remote server and log its result
        # -------------------------------
        payload = {
            "survey_response_id": new_response.id,
            "unique_user_id": unique_user_id,
            "referral_id": final_referral,
            "age": age,
            "gender": gender,
            "other_data": additional_info,
            "timestamp": new_response.timestamp.isoformat() if new_response.timestamp else None
        }
        remote_result = send_payload_to_remote(payload)
        action_type = "RemoteResponseOK" if remote_result == "OK" else "RemoteResponseError"
        log_action = CustomerAction(
            unique_user_id=unique_user_id,
            action_type=action_type,
            referral_id=final_referral
        )
        try:
            db.session.add(log_action)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error logging remote response action: {e}")

        return redirect(url_for('index_bp.responses'))

    return render_template('index.html')

@index_bp.route('/clicked_status')
def clicked_status():
    actions = CustomerAction.query.order_by(CustomerAction.timestamp.desc()).all()
    return render_template('clicked_status.html', actions=actions)

@index_bp.route('/responses')
def responses():
    # 1) Update the JSON file
    if not update_json_file():
        current_app.logger.error("JSON file update failed.")

    # 2) Locate your JSON file
    basedir         = os.path.abspath(os.path.dirname(__file__))
    json_file_path  = os.path.join(basedir, 'survey_responses.json')

    # 3) Your two base endpoints (no payout parameter here)
    base_urls = [
        "https://surveytitans.com/postback/7b7662e8159314ef0bdb32bf038bba29?",
        "https://kingopinions.com/postback/d90a817d5474da1feb49ec55c69f6bbf?",
        "https://surveytitans.com/postback/6ccfb58eb8c47a7a54f4ca8a9bbcabcc?",
        "https://surveytitans.com/postback/db2321a6b97f71653fd07f2ac70af751?"
    ]

    # 4) The list of integer points you want to end up with
    payout_options = [100, 75, 35, 25, 75, 20, 30, 40, 50, 85]

    # 5) For each endpoint, pick one payout at random,
    #    convert it into a decimal, and send.
    for base in base_urls:
        pts       = random.choice(payout_options)
        decimal   = pts / 100.0                  
        url       = f"{base}payout={decimal:.2f}"
        send_json_file_payload(json_file_path, url)
        current_app.logger.info(f"Sent JSON file to {url}")

    # 6) Render the template as before
    responses = SurveyResponseIndex.query.\
                  order_by(SurveyResponseIndex.timestamp.desc()).all()
    return render_template('response1.html', responses=responses)