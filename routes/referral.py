from flask import Blueprint, render_template, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

referral_bp = Blueprint('referral_bp', __name__, url_prefix='/referral')

# Set up database connections for the different pages
engine_page1 = create_engine('sqlite:///survey_response.db', connect_args={'check_same_thread': False})

SessionPage1 = sessionmaker(bind=engine_page1)

@referral_bp.route('/', methods=['GET'])
def index():
    return render_template('referral.html')

@referral_bp.route('/search', methods=['POST'])
def search():
    # Local imports to prevent circular dependency issues.
    from index import SurveyResponseIndex

    search_id = request.form.get('search_id')
    if not search_id:
        return render_template('referral.html', error="Please enter an ID to search")

    try:
        search_id = int(search_id)
    except ValueError:
        return render_template('referral.html', error="Please enter a valid numeric ID")

    # Search in all three databases.
    session1 = SessionPage1()


    try:
        # --- Search in Page 1 (Premium Mobile Accessories Survey) database ---
        response1 = session1.query(SurveyResponseIndex).filter_by(id=search_id).first()
        if response1:
            other_data = {}
            if response1.other_data:
                try:
                    other_data = json.loads(response1.other_data)
                except Exception:
                    pass
            # Build the result using the new field names
            result = {
                'ID': response1.id,
                'Mood': other_data.get('mood', ''),
                'Special': other_data.get('special', ''),
                'Productivity': ", ".join(other_data.get('productivity', [])),
                'Accessories (Love)': ", ".join(other_data.get('accessoriesLove', [])),
                'Accessories (Dislike)': ", ".join(other_data.get('accessoriesDislike', [])),
                'Quality - Brand': other_data.get('quality_brand', ''),
                'Quality - Material': other_data.get('quality_material', ''),
                'Quality - Design': other_data.get('quality_design', ''),
                'Quality - Durability': other_data.get('quality_durability', ''),
                'Quality - Features': other_data.get('quality_features', ''),
                'Quality - Warranty': other_data.get('quality_warranty', ''),
                'Quality - Fit': other_data.get('quality_fit', ''),
                'Quality - Eco': other_data.get('quality_eco', ''),
                'Phone Case Value': other_data.get('phonecase_value', ''),
                'Music Picks': ", ".join(other_data.get('music_pick', [])),
                'Spending': other_data.get('spend', ''),
                'Age': response1.age,
                'Gender': response1.gender,
                'Unique User ID': response1.unique_user_id,
                'Referral ID': response1.referral_id,
                'Database': 'Page 1'
            }
            return render_template('referral.html', response=result)

        return render_template('referral.html', error=f"No entry found with ID {search_id} in any database")
    finally:
        session1.close()
        

@referral_bp.route('/unique-user/<referral_id>', methods=['GET'])
def view_unique_user(referral_id):
    from index import SurveyResponseIndex
    responses = SurveyResponseIndex.query.filter_by(referral_id=referral_id).all()
    if responses:
        return render_template('unique_user.html', referral_id=referral_id, responses=responses)
    return render_template('referral.html', error="No responses found for this unique user.")
