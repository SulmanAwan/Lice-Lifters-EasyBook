from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from flask_mail import Message
from extensions import mail
from db import get_db_connection
from datetime import datetime, timedelta
import random
import string

account_manager = Blueprint('account_manager', __name__, template_folder='templates', static_folder='static')

# TODO: update routes when you create the homepages for the various user types ltaer.
@account_manager.route('/login', methods=['GET', 'POST'])
def login():
    # Check to make sure user isn't already logged in to the session.
    if 'logged_in' in session and session['logged_in']:
        # If the user is already logged in, transfer them to the cooressponding homepage based on user type.
        # TODO: dont forget to pass the required data to render the calendar in the case the user is stored in session as well.

        if session['permission'] == 'admin':
            return redirect(url_for('admin.admin_homepage'))
        elif session['permission'] == 'employee':
            return redirect(url_for('employee.employee_homepage'))
        else:
            return redirect(url_for('customer.customer_homepage'))
    
    # If the user is sending a post request, it means they filled the form.
    if request.method == 'POST':
        # Store their email and password
        email = request.form['email']
        password = request.form['password']

        # Connect into database and retrieve data in the form of dictionaries
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Execute query to find user in the database with the entered email
            cursor.execute(
                "SELECT * FROM users WHERE email = %s",
                (email,)
            )
            user = cursor.fetchone() # Get one row of the query result

            # Check if the user exists and password matches
            if user and user['password'] == password:
                # If the credentials are fine, save the user data in a session to use later.
                session['user_id'] = user['user_id']
                session['name'] = user['name']
                session['email'] = user['email']
                session['permission'] = user['permission']
                session['logged_in'] = True

                # Alert the user that login was successful
                flash('Login successful!', 'success')

                # Based on user permission, route them to their corspoonding homepage.
                # TODO: to render the calendars for each type we MUST pass in the following data:
                # - month, day, year
                # - first day of the month (Ex: if it is a tuesday)
                # - number of days in the month
                # - block days
                # - current day
                if user['permission'] == 'admin': 
                    return redirect(url_for('admin.admin_homepage'))
                elif user['permission'] == 'employee':
                    return redirect(url_for('employee.employee_homepage'))
                else:
                    return redirect(url_for('customer.customer_homepage'))
            else:
                # On the other hand, if the user enters the wrong credeentials warn him.
                flash('Invalid email or password. Please try again.', 'error')

        except Exception as e:
            # In case any error happens, flash the user about the error.
            flash(f'An error occurred: {str(e)}', 'error')
        finally:
            # Close the cursor and connection
            cursor.close()
            conn.close()
    
    # If its a GET method, render template (ex: login fails, then render template again with get method)
    return render_template('login.html')

@account_manager.route('/create', methods=['GET', 'POST'])
def create_account():
    # If we are doing a post method, we need to retrieve the customers data from the create account form.
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        permission = 'customer' # Default permission for new users is customer
        
        # Connect to the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Check if email already exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()

            # emails are unique so if it exists we reload the users page with the flash mesage.
            if existing_user:
                flash('Email already registered', 'error')
                return render_template('create_account.html')
            
            # Otherwise if the email is not taken, we insert into the database.
            cursor.execute(
                "INSERT INTO users (name, email, password, permission) VALUES (%s, %s, %s, %s)",
                (name, email, password, permission)  
            )
            conn.commit()
            
            # We indicate to user that they created a account and proceed them to the login page.
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('account_manager.login'))
            
        except Exception as e:
            
            flash(f'An error occurred: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()
    
    # If method is GET or registration failed (when registration fails we need to flash method and keep user on same page)
    return render_template('create_account.html')


def generate_reset_code():
    # Creates a random code of integers and strings.
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@account_manager.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    # Check if its a post request and that the user entered an email in the form
    if request.method == 'POST' and 'email' in request.form:
        email = request.form['email'] # store the email
        
        # Check if email exists in database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM USERS WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            # Generate security code
            reset_code = generate_reset_code()
            expiry_time = datetime.now() + timedelta(minutes=15)  # Make code expire in 15 mins
            
            # Store code and expiry time in session to verify when you reset password.
            session['reset_email'] = email
            session['reset_code'] = reset_code
            session['reset_expiry'] = expiry_time.timestamp()

            # Send email to user with code
            msg = Message("Password Reset Code", recipients=[email])
            msg.body = f"Your password reset code is: {reset_code}. This code will expire in 15 minutes."
            mail.send(msg)
            
            cursor.close()
            conn.close()
            
            # Transfer user to the verify_code route.
            return redirect(url_for('account_manager.verify_code'))
        else:
            # If the user entered an email thats not inthe database indiccate this to user.
            flash(f'Email not found', 'error')
        
        cursor.close()
        conn.close()
        
        # If the method is post and the user DID NOT enter the email, indicate to user to enter a email in the form.
    elif request.method == 'POST':
        flash(f'Please enter your email address!', 'error')
    
    # If the method is GET or if the user enters a wrong email, render the template again
    return render_template('forgot_password.html')

@account_manager.route('/verify_code', methods=['GET', 'POST'])
def verify_code():

    # Check if reset info exists in session
    if 'reset_email' not in session or 'reset_code' not in session or 'reset_expiry' not in session:
        # If the email OR reset_code OR reset_expiry time are not in the session, then the session expired and we 
        # Show an error and redirect user to the forgot_password page.
        flash('Password reset session expired or invalid. Please try again.', 'error')
        return redirect(url_for('account_manager.forgot_password'))
    
    # If method is post then we take the verification code from the form
    if request.method == 'POST':
        # Get verification code from form
        verification_code = request.form['verification_code']
        
        # Get the current time (for comparison)
        current_time = datetime.now().timestamp()
        
         # Check to see if the code has expired
        if current_time > session['reset_expiry']:
            # Code expired
            flash('Verification code has expired. Please request a new one.', 'error')
            # Clear expired session data
            session.pop('reset_email', None)
            session.pop('reset_code', None)
            session.pop('reset_expiry', None)
            # Send user back to forgot_password page
            return redirect(url_for('account_manager.forgot_password'))
        
        # Check to see if the verification code that the user entered matches the generated one.
        if verification_code == session['reset_code']:
            # Code is valid, redirect to reset password page
            # Keep the email in session for the reset_password route (will use to update database)
            return redirect(url_for('account_manager.reset_password'))
        else:
            # User enters the wrong code, we create a flash and store that in the session for _alerts.html to use and show.
            flash('Invalid verification code. Please try again.', 'error')
    
    # For GET requests or failed verifications
    return render_template('verify_code.html')

@account_manager.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    # Check if reset email exists in session
    if 'reset_email' not in session:
        # Make sure reset_email is in the session so we don't cause problem
        # For instance, if the user just types the route(their email isnt in the session) then they should
        # Be sent back to the forgot_password page and forced to type their email
        flash('Password reset session expired or invalid. Please try again.', 'error')
        return redirect(url_for('account_manager.forgot_password'))
    
    # If the method is POST we are going to get the info from the form
    # Then validate that the info exists and that the passwords match
    # If they do then update the users table with the new password for the email in session.
    # Once this is done,  we can flush all the session data since the "forgot password" process is complete now.
    if request.method == 'POST':
        # Get new passwords from form
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Make sure user entered both passwords in the form (not null)
        if not new_password or not confirm_password:
            flash('Please enter and confirm your new password.', 'error')
            return render_template('reset_password.html')
        
        # Make sure the passwords match
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html')
        
        # Update password in database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET password = %s WHERE email = %s",
                (new_password, session['reset_email'])
            )
            conn.commit()
            cursor.close()
            conn.close()
            
            # Clear reset session data (The 'forgot password' process is complete)
            # We needed the session data only for added security (like routing users back if they didnt enter email and tried to manualy access a route)
            session.pop('reset_email', None)
            session.pop('reset_code', None)
            session.pop('reset_expiry', None)
            
            # Indicate to our usr that their credentials have been changed.
            flash('Your password has been updated successfully. Please log in with your new password.', 'success')
            return redirect(url_for('account_manager.login'))
        
        except Exception as e:
            # If any expcetions occur during this process, we display them and reload the page.
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('reset_password.html')
    
    # For a get reques we always render the page.
    return render_template('reset_password.html')

@account_manager.route('/logout')
def logout():
    # When user logs out we clear their session and display a flash that the user was logged out successfullly.
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('account_manager.login'))
        
