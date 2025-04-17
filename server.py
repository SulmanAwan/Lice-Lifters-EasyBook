from flask import Flask, render_template
from extensions import mail
from accountmanager.accountmanager import account_manager
from admin.admin import admin
from employee.employee import employee
from customer.customer import customer
from flask_apscheduler import APScheduler
import datetime
from customer.customer import send_appointment_reminders

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'secretkey'

# Configure Flask-Mail with Gmail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'easybookverify@gmail.com'
app.config['MAIL_PASSWORD'] = 'mstc ohrb hwts mcgn'
app.config['MAIL_DEFAULT_SENDER'] = 'easybookverify@gmail.com'

mail.init_app(app)

# Register blueprints
app.register_blueprint(account_manager, url_prefix='/account')
app.register_blueprint(admin, url_prefix='/admin')
app.register_blueprint(employee, url_prefix='/employee')
app.register_blueprint(customer, url_prefix='/customer')

# Upon starting up the app, send email notification reminders to all customers who have
# an appointment booked for tommorow
with app.app_context():
    send_appointment_reminders()

scheduler = APScheduler()
scheduler.init_app(app) # Initialize the scheduler with the Flask app

# Schedule the email reminder method to run once every day while the app is running
@scheduler.task('interval', id='send_appointment_reminders', days=1)
def scheduled_appointment_reminders():
    with app.app_context():
        send_appointment_reminders()

scheduler.start() # Start running the shceduler in the background of the app

@app.route('/')
def index():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)