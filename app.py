from flask import Flask, request, jsonify
from index import index_bp, db, CustomerAction, init_db
from referral import referral_bp
import os
import json
from flask_mail import Mail, Message
from dotenv import load_dotenv
from mongoengine import connect


# Load environment variables (from .env file if needed)
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///survey_response.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', '1']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
app.config['MAIL_SSL']=True
# Optional: remote server URL for sending JSON payloads
app.config['REMOTE_SERVER_URL'] = os.getenv('REMOTE_SERVER_URL', 'http://127.0.0.1:5000/responses')

# Initialize the database with our app
mail=Mail(app)
db.init_app(app)
# mail.init_app(app)

# Custom Jinja filter to convert JSON strings to Python objects
def fromjson_filter(s):
    try:
        return json.loads(s)
    except Exception:
        return {}

app.jinja_env.filters['fromjson'] = fromjson_filter

# Register Blueprints
app.register_blueprint(index_bp)         # Handles survey form at '/'
app.register_blueprint(referral_bp)        # Handles referral routes at '/referral'

# Create/update tables on app startup
with app.app_context():
    db.create_all()

@app.route('/track-dropoff', methods=['POST'])
def track_dropoff():
    return "Dropoff tracked", 200

# --- S2S Tracking Endpoint ---
@app.route('/track-action', methods=['POST'])
def track_action():
    data = request.get_json()
    unique_user_id = data.get("unique_user_id")
    action_type = data.get("action_type")
    referral_id = data.get("referral_id")
    
    if not all([unique_user_id, action_type, referral_id]):
        return jsonify({"error": "Missing data"}), 400
    
    new_event = CustomerAction(
        unique_user_id=unique_user_id,
        action_type=action_type,
        referral_id=referral_id
    )
    try:
        db.session.add(new_event)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(debug=True)
