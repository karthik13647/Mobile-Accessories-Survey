# app.py
import os
import json
import pandas as pd
from flask import Flask, request, jsonify, send_file
from index import index_bp, db, CustomerAction, init_db
from referral import referral_bp
from flask_mail import Mail, Message
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Load environment variables (from .env file if needed)
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__)
# Configure MySQL connection using SQLAlchemy (using URL-encoded credentials)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'SQLALCHEMY_DATABASE_URI',
    'mysql+pymysql://root:Abhiprince%4047@127.0.0.1/survey_response?charset=utf8mb4'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.urandom(24)
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', '1']
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
app.config['MAIL_SSL'] = True
# Optional: remote server URL for sending JSON payloads
app.config['REMOTE_SERVER_URL'] = os.getenv('REMOTE_SERVER_URL', 'http://127.0.0.1:5000/responses')

# Initialize Flask-Mail
mail = Mail(app)
# Initialize the database with our app
db.init_app(app)

# Register Blueprints
app.register_blueprint(index_bp)         # Handles survey form at '/'
app.register_blueprint(referral_bp)        # Handles referral routes at '/referral'

# Custom Jinja filter to convert JSON strings to Python objects
def fromjson_filter(s):
    try:
        return json.loads(s)
    except Exception:
        return {}
        
app.jinja_env.filters['fromjson'] = fromjson_filter

# Create/update tables on app startup
with app.app_context():
    init_db(app)

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

# --- New Endpoint: Export DB Table to JSON File using Pandas ---
@app.route('/export-json')
def export_json():
    # Create a SQLAlchemy engine using the same connection string as your app
    engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    try:
        # Read the survey_response table into a Pandas DataFrame
        df = pd.read_sql_table('survey_response', con=engine)
    except Exception as e:
        return jsonify({"error": f"Unable to read table: {str(e)}"}), 500
    
    # Convert the DataFrame to JSON (records orientation, indented)
    json_data = df.to_json(orient='records', indent=4)
    
    # Define the output file path
    output_file = os.path.join(basedir, 'survey_responses.json')
    
    # Write the JSON data to the file
    with open(output_file, 'w') as f:
        f.write(json_data)
    
    # Send the file as an attachment to the client
    return send_file(output_file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
