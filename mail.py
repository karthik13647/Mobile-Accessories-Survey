import os
import smtplib

app = Flask(__name__)
app.config.update(
    MAIL_SERVER=os.getenv('MAIL_SERVER'),
    MAIL_PORT=os.getenv('MAIL_PORT', 587),
    MAIL_USE_TLS=os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', '1'],
    MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER=os.getenv('MAIL_DEFAULT_SENDER')
)
mail.init_app(app)