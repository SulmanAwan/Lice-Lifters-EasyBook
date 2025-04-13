from flask import Flask, render_template
from extensions import mail
from accountmanager.accountmanager import account_manager
from admin.admin import admin
from employee.employee import employee
from customer.customer import customer, reminder_trigger

# Imported to allow threading to happen and imported a method above from customer to allow the method to run here
from threading import Thread

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

# This is in place so that the the thread can run the method with the app_context that lets flask run it
# If with app.app_context() is removed it will cause an error that an out of application is triggered
def reminder():
    with app.app_context():
        reminder_trigger()

@app.route('/')
def index():
    return render_template('home.html')

if __name__ == '__main__':
    # The thread is created as a daemon which allows this to work in the background of the app
    reminder_thread = Thread(target=reminder)
    # This ensures the thread will start/exit when the app starts/exits
    # Place before app.run to have it start first, if app.run is placed before it then it won't run
    reminder_thread.daemon = True
    reminder_thread.start()
    # Use_reloader= false is needed to make sure it only starts once instead of twice since it was run
    # in development mode which is why it runs twice.
    app.run(debug=True, use_reloader=False)