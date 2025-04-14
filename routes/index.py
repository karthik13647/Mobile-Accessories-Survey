# routes/index.py
import json, requests
from datetime import datetime
import hashlib, uuid
from flask import Blueprint, render_template, request, redirect, url_for, session
from sqlalchemy import text
from models import db, UniqueUser, SurveyResponse, CustomerAction, hash_referral_id, generate_direct_referral
from flask_mail import Message
from config import Config
import os

index_bp = Blueprint('index_bp', __name__)

# Predefined referral links and their codes (email addresses in this case)
REFERRAL_LINKS = {
    'special-offer-1': 'karthik@pepeleads.com',
    'vip-access': 'jayant.a@pepeleads.com',
}

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

@index_bp.route('/<referral_link>', methods=['GET'])
def referral_redirect(referral_link):
    from app import mail  # Import mail from the main app to avoid circular imports

    if referral_link in REFERRAL_LINKS:
        referral_code = REFERRAL_LINKS[referral_link]
        hashed_referral = hash_referral_id(referral_code)
        recipient_email = referral_code  # referral_code is the email address
        
        # Send email notification
        try:
            msg = Message(
                subject="New Referral Link Click",
                recipients=[recipient_email],
                body=f"Your referral link '{referral_link}' was clicked!",
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
        # Retrieve survey form responses
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
        gender = request.form.get('gender')
        day_experience = request.form.get('dayExperience')
        device_type = request.form.get('deviceType')
        
        # Bundle additional data
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
        tracking_data = request.form.get('trackingData')
        name = "Anonymous"

        # Process referral from session if present
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

        new_response = SurveyResponse(
            unique_user_id=unique_user_id,
            referral_id=final_referral,
            age=age,
            gender=gender,
            other_data=other_data_json,
            tracking_data=tracking_data,
            status="Completed",
            device_type=device_type,
            ip_address=ip_info['ip_address'] if ip_info else None,
            country=ip_info['country'] if ip_info else None,
            city=ip_info['city'] if ip_info else None,
            region=ip_info['region'] if ip_info else None,
            latitude=ip_info['latitude'] if ip_info else None,
            longitude=ip_info['longitude'] if ip_info else None,
            day_experience=day_experience
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
    responses = SurveyResponse.query.all()
    return render_template('response1.html', responses=responses)

@index_bp.route('/clicked_status')
def clicked_status():
    actions = CustomerAction.query.order_by(CustomerAction.timestamp.desc()).all()
    return render_template('clicked_status.html', actions=actions)
