from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db_connection
import calendar
import datetime
import stripe
from extensions import mail
from flask_mail import Message
from dotenv import load_dotenv
import os

customer = Blueprint('customer', __name__, template_folder='templates', static_folder='static')

@customer.route('/homepage', methods=['GET', 'POST'])
def customer_homepage():
    # Render homepage for customer, including the calendar, buttons, bookings, shifts, etc...

    # Get name from session to display on the homepage
    name = session.get('name')
    
    # Using .today(), get current date infomation and the object in the today variable so we can access individual components of the current day
    today = datetime.date.today()
    
    # Retrieve the selected_date argument from the form request if it exists
    selected_date_str = request.args.get('selected_date')
    if selected_date_str:
        # When we get the date from the form request, it is a string like 'YYYY-MM-DD'
        # We gotta convert this to a datetime object so we can efficiently access components of the date
        # Using the datetime module and datetime class and strptime method to convert the string to a datetime object
        # Datetime object have the current date and time components, but we are only concerned with date components
        # So we turn the selected_date into a date object using the date() method (strips away the time components)
        selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    else:
        # If no date is provided (ie: first time customer logs in) we set the selected_date to the current day
        selected_date = today
    
    # We will display the weekday, month, and day of the selected_date on the right side of the page
    # It will need to be formatted in the (ie: Monday, January 01) 
    # %A - Full weekday name, %B - Full month name, %d - Day of the month
    display_date = selected_date.strftime('%A, %B %d')
    
    # Get the month and year components of the date object (selected_date)
    current_month = selected_date.month
    current_year = selected_date.year
    # Use the calendar module to get the string of the current_month
    current_month_name = calendar.month_name[current_month]
    
    # Use the generate_calendar function to create the calendar for the selected month and year
    calendar_weeks = generate_calendar(current_year, current_month, selected_date)
    
    # Check if the selected date is blocked (Used for how the 'block' button will be displayed)
    is_blocked = check_if_date_blocked(selected_date)

    # Get all the available timeslots for the selected_date and render them in the page
    available_timeslots = get_available_timeslots_for_date(selected_date)
    
    # Finaally we pass in all the data required to render the homepage components (calendar, shifts, bookings, etc)
    return render_template('customer_homepage.html', 
                          name=name, # Displayed on the top right of the page
                          calendar_weeks=calendar_weeks, # Calendar object which contains all the days information stored as dictonaries.
                          selected_date=selected_date.strftime('%Y-%m-%d'), # The selected date in the format YYYY-MM-DD (ie date object)
                          display_date=display_date, # The selected date in the format (ie: Monday, January 01) shown on the right side of the page
                          current_month=current_month, # The current month number (1-12)
                          current_year=current_year, # The current year (YYYY)
                          current_month_name=current_month_name, # The current month name (ie: January)
                          is_blocked=is_blocked,    # Boolean value indicating if the selected_date is blocked or not (used for configuring button text)
                          available_timeslots=available_timeslots)  # Available timeslots for the selected date


def generate_calendar(year, month, selected_date):
    # We will create a calendar object that can be utilized in the html template for the calendar component using Jinja2
    # In order to do this, we need to get the very first day of the month (ex: March 1, 2025)
    # We need to get the day of the week of the first day of the month (ex: March 1, 2025 is a Saturday)
    # Lastly, we need to get the total number of days that are in the current month (ex: March has 31 days)
    # Using this information we can generate a calendar list in which each entry is a list (corresponding to weeks)
    # And in each week is a dictionary object containing information for a certain day of the month: day, date, and class (business or blocked)
    first_day = datetime.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]

    # Get current date for comparing past dates
    today = datetime.date.today()
    
    # Get the day of the week for the first day (0 = Monday, 6 = Sunday) For instance, March 1, 2025 is a Saturday so it will return 5
    first_weekday = first_day.weekday()
    
    # Our calendar headings for the weekday will be 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
    # So we need to adjust the first_weekday to match this format
    # Adjust for Sunday as the first day of the week (0 = Sunday, 6 = Saturday)
    first_weekday = (first_weekday + 1) % 7
    
    # Get blocked dates for this month (will use this to determine the css class styling later on)
    blocked_dates = get_blocked_dates(year, month)
    
    # Initialize the calendar and commence a counter that will count the number of days that have ellapsed in the for loop
    calendar_weeks = []
    day = 1
    
    # Generate up to 6 weeks (max possible in a month view)
    for week in range(6):
        week_days = []
        
        # Generate 7 day enteries (each entry will be a dictionary and contain day info) for each week
        for weekday in range(7):
            # Check if the current day is within the month
            # If its the first week there may be some days to skip and don't make more entries when you past the last day
            if (week == 0 and weekday < first_weekday) or (day > last_day):
                # Add empty day placeholder, this will indicate that the current date doesn't exist in the month
                # This will be used to create empty spaces in the calendar for days that are not in the month
                week_days.append({'date': None})
            else:
                # Use the passed in year and month and the day counter to create a date object
                # and use the strftime method to convert it to a string in the format 'YYYY-MM-DD'
                # We need it in the string format since the block_dates is a list of strings with the format 'YYYY-MM-DD' ...
                # containing the block date
                # Create date object for current day
                current_date = datetime.date(year, month, day)
                date_str = current_date.strftime('%Y-%m-%d')
                
                # We check to see if the current iteration of the date is in the block_dates list
                if current_date < today and date_str not in blocked_dates:
                    # If it is then we assign the class to be 'blocked-day' (used for styling)
                    # day_class will be assigned to the class attribute of the day object
                    day_class = 'past-day'

                elif date_str in blocked_dates:
                    day_class = 'blocked-day'

                else:
                    # If not then we assign the class to be 'business-day' (used for styling)
                    day_class = 'business-day'
                
                # Now we create a dictionary object for the current day and add it to the week_days list
                # The dictionary object will contain the day (a number), date (a string), and class (business or blocked)
                # The day attribute is the day of the month (1-31) and the date string is the formatted date string
                # The date_string will be used to check if its the current day or not in the Jinja2 template
                # The class is the css class that will be used to style the day in the calendar
                week_days.append({
                    'day': day,
                    'date': date_str,
                    'class': day_class
                })
                
                # We increment the day counter to move to the next day and repeat the process of creating corresponding dictionaries
                # For each day of the week in the current month/year.
                day += 1
        
        # Add this week to the calendar
        calendar_weeks.append(week_days)
        
        # If we reach the end of the month (ie: day (March 32) > last_day (March 31)) we break out of the loop
        if day > last_day:
            break
    
    # In the end we will have a list of weeks for the calendar and each week will have a list of days and each 
    # day will be a dictionary object containing the data required for the Jinja2 template to render the calendar correctly.
    return calendar_weeks

def get_blocked_dates(year, month):
    # Helper method for the generate_calendar method
    # This method will query the database for all blocked dates in the current month and return them as a list of strings
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # The database is storing the blocked dates in the format 'YYYY-MM-DD' string (ie: sql DATE objects)
    # We need to create a boundary for the select query within the current month (ie: the first day of mont) and 
    # date before the next day of month.

    # We create the start date of the current month (ie: March 1, 2025)
    start_date_obj = datetime.date(year, month, 1)

    # Create end date (first day of next month)
    # If the month is december then we need to increment the year by 1 and set the month to January 
    if month == 12:
        end_date_obj = datetime.date(year + 1, 1, 1)
    else: 
        # Otherwise we simply increment the month by 1
        end_date_obj = datetime.date(year, month + 1, 1)

    # Currently we have date objects in the start_date and end_date but we need them as strings because
    # The database stores the dates as strings (sql DATE objects) so we apply the strftime method to convert them into
    # strings with the same format 'YYYY-MM-DD'
    start_date = start_date_obj.strftime("%Y-%m-%d")
    end_date = end_date_obj.strftime("%Y-%m-%d")
    
    try:
        # We execute the query that selects all dates from the block_days table that are within the start_date (March 1, 2025) and end_date before (April 1, 2025)
        cursor.execute("SELECT date FROM block_days WHERE date >= %s AND date < %s", 
                    (start_date, end_date))
        
        # We fetch all the results of the query and convert them into strings for easy comparison for generating the calendar_weeks
        blocked_dates = [row['date'].strftime('%Y-%m-%d') for row in cursor.fetchall()]

    except Exception as e:
        # If there is an error we flash the error message to the user
        flash(f'Error fetching blocked dates: {str(e)}', 'error')
        blocked_dates = [] # send an empty list in the case of an error

    finally:
        # We close the cursor and connection to the database
        cursor.close()
        conn.close()
    
    # We return the list of blocked dates for the current month ['YYYY-MM-DD', 'YYYY-MM-DD', ...]
    return blocked_dates

def check_if_date_blocked(date):
    # Check if the specific date is blocked (used for determining text on the block button)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try: 
        # Run query to check if the date passed into the method is in the block_days table
        cursor.execute("SELECT COUNT(*) as count FROM block_days WHERE date = %s", (date,))
        result = cursor.fetchone()

    except Exception as e:
        # If there is an error we flash the error message to the user
        flash(f'Error checking blocked date: {str(e)}', 'error')
        result = {'count': 0} # Also, in the case of error we set the count attribute to 0 

    finally:
        # We close the cursor and connection to the database
        cursor.close()
        conn.close()
    
    # We check to see if the count is greater than 0 (meaning the date is blocked)
    # If it is then we set blocked to True, otherwise we set it to False
    blocked = result['count'] > 0

    # We return the boolean value indicating if the date is blocked or not
    return blocked

def format_time(datetime_delta):
    # Helper method for converting the TIME datatypes from the database (HH:MM:SS) to a 12-hour string format with AM/PM

    # We get the datetime_delta objects from the database and convert them to seconds
    total_seconds = datetime_delta.total_seconds() 

    # We convert the total seconds to hours and minutes and parse them into integers (no longer objects)
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    
    # Now that we have the hours we can determine whether the passed in time is AM or PM
    if hours < 12:
        period = "AM"
    else:
        period = "PM"

    # We need to convert the hours from military time to a 12-hour format
    display_hours = hours % 12

    # If the hours are 0 it means it is 12 o clock and we need to display it as 12 instead of 0
    if display_hours == 0:
        display_hours = 12
    
    # We return a formatted string that contains the time in the format 'HH:MM AM/PM'
    return f"{display_hours}:{minutes:02d} {period}"

def get_available_timeslots_for_date(date):
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get the available timeslots for the selected date (current_bookings < max_bookings)
        # Get the available timeslots for the selected date (current_bookings < max_bookings)
        today = datetime.datetime.today().date()  # Get today's date
        current_time = datetime.datetime.now().time()  # Get the current time

        # If the selected date is today, we need to check for past timeslots
        if date == today:
            cursor.execute("""
                SELECT slot_id, start_time, end_time, current_bookings, max_bookings
                FROM time_slots
                WHERE slot_date = %s AND current_bookings < max_bookings
                AND start_time > %s
                ORDER BY start_time
            """, (date, current_time))
        else:
            # For dates other than today, no need to filter by current time
            cursor.execute("""
                SELECT slot_id, start_time, end_time, current_bookings, max_bookings
                FROM time_slots
                WHERE slot_date = %s AND current_bookings < max_bookings
                ORDER BY start_time
            """, (date,))

        timeslots = cursor.fetchall()
        
        # Format times for display and calculate the available timeslots
        for slot in timeslots:
            slot['start_time'] = format_time(slot['start_time'])
            slot['end_time'] = format_time(slot['end_time'])

            slot['available_slots'] = slot['max_bookings'] - slot['current_bookings']
        
    except Exception as e:
        # In the case of error display it to user
        flash(f'Error fetching available timeslots: {str(e)}', 'error')
        timeslots = []
    
    finally:
        cursor.close()
        conn.close()
    
    # Return the list of open timeslots for the selected date so it can be rendered in the page
    return timeslots

@customer.route('/book_appointment', methods=['GET','POST'])
def book_appointment():
    # Get the date string from the form
    date_str = request.form['selected_date']
    # We want to change its format, so lets convert it into a date object with the datetime module and datetime class (datetime.datetime)
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    # We format the new date obj into a string with the format like "Month, Day Year"
    display_date = date_obj.strftime('%B %d, %Y')
    slot_id = request.form['slot_id']
    user_id = session.get('user_id')    

    if allowed_to_book(user_id) == False:
        flash(f'You have reached the maximum limit of 3 bookings. Please complete or cancel existing appointments before making a new one.', 'warning')
        return redirect(url_for('customer.manage_appointments'))

    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get the selected timeslot so we can display its start and end time
    cursor.execute("""
                   SELECT start_time, end_time
                   FROM time_slots
                   WHERE slot_id = %s
                   """, (slot_id,))
    
    selected_slot = cursor.fetchone()

    # Format the time into 12-hour format
    selected_slot['formatted_start_time'] = format_time(selected_slot['start_time'])
    selected_slot['formatted_end_time'] = format_time(selected_slot['end_time'])

    # Render the form with the required data for the customer
    return render_template('book_appointment.html', 
                        display_date=display_date,
                        slot_id=slot_id,
                        user_id=user_id,
                        selected_slot=selected_slot)

@customer.route('/schedule_appointment/<int:slot_id>', methods=['POST'])
def schedule_appointment(slot_id):
    appointment_type = request.form['appointment_type']
    payment_method = request.form['payment_method']
    user_id = session.get('user_id')   

    # For online payments we will require card details so proceed users who want to pay via stripe to
    # Another route 
    if payment_method == "stripe":
        return redirect(url_for('customer.online_payment', 
                         appointment_type=appointment_type, 
                         slot_id=slot_id, 
                         payment_method=payment_method,
                         user_id=user_id))

    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get service type_id and price for the appointment_type specified by user
        cursor.execute("""
            SELECT type_id, price
            FROM booking_types 
            WHERE type_name = %s
        """, (appointment_type,))
        service_type = cursor.fetchone()

        # Create payment transaction record using the payment_method and service_type price
        # Set stripe_transaction_id to null for in-store bookings
        cursor.execute("""
            INSERT INTO payment_transactions 
            (payment_method, amount, stripe_transaction_id) 
            VALUES (%s, %s, NULL)
        """, (payment_method, service_type['price']))
        
        # Get the transaction ID of the newly inserted record (ie: the last row)
        transaction_id = cursor.lastrowid

        # Insert booking record with the newly created transaction_id and assign it the
        # type_id, slot_id, and user_id it corresponds to
        cursor.execute("""
            INSERT INTO bookings 
            (customer_id, type_id, transaction_id, slot_id, appointment_status) 
            VALUES (%s, %s, %s, %s, 'current')
        """, (user_id, service_type['type_id'], transaction_id, slot_id))

        # Increment current bookings for the time slot (since new booking has been made)
        cursor.execute("""
            UPDATE time_slots 
            SET current_bookings = current_bookings + 1 
            WHERE slot_id = %s
        """, (slot_id,))

        # Get the time slot information for formatting the date and time for the receipt
        cursor.execute("""
            SELECT slot_date, start_time, end_time
            FROM time_slots
            WHERE slot_id = %s
        """, (slot_id,))
        slot_info = cursor.fetchone()
        
        # Format the date: "Monday, January 1, 2025"
        date_str = slot_info['slot_date'].strftime('%A, %B %d, %Y')
        
        # Format the time: "2:30 PM - 3:00 PM"
        start_time_str = format_time(slot_info['start_time'])
        end_time_str = format_time(slot_info['end_time'])
        time_str = f"{start_time_str} - {end_time_str}"

        conn.commit()

        if payment_method == "in_store":
            # If the payment method is in-store, we need to send a receipt to the customer via email
            cursor.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
            customer_email = cursor.fetchone()['email']

            # Construct and send receipt email
            msg = Message("Your Appointment Booking Receipt", recipients=[customer_email])

            msg.body = f"""
Thank you for booking!

Appointment Details:

- Service: {appointment_type}
- Date: {date_str}
- Time: {time_str}
- Amount Due: ${service_type['price']}

"""
            mail.send(msg) #send the email
        
        flash('Appointment booked successfully! A confirmation email has been sent.', 'success')
        
        # Redirect to manage appointments or homepage
        return redirect(url_for('customer.manage_appointments'))
    
    except Exception as e:
        # In the case of error, return the customer to the homepage and display a error msg
        flash(f'Error booking appointment: {str(e)}', 'error')
        return redirect(url_for('customer.customer_homepage'))
    
    finally:
        cursor.close()
        conn.close()

# Stripe API Configuration
load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

stripe.api_key = STRIPE_SECRET_KEY

@customer.route('/online_payment', methods=['GET', 'POST'])
def online_payment():
    # We pass in the necessary fields required to add a booking 
    appointment_type = request.args.get('appointment_type')
    slot_id = request.args.get('slot_id')
    payment_method = request.args.get('payment_method')
    user_id = request.args.get('user_id')

    # Set the price based on the appointment type (this is required for stripe payment)
    if appointment_type == "Lice Check":
        price = 4000
    else:
        price = 18900

    # Get the date from the slot_id and customer email
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # We retrieve the slot date and format it so it can be passed back into book_appointment page in case user cancels
    cursor.execute("SELECT slot_date FROM time_slots WHERE slot_id = %s", (slot_id,))
    slot_date = cursor.fetchone()
    date_str = slot_date['slot_date'].strftime('%Y-%m-%d')

    # We pass the user email to the stripe checkout session
    cursor.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
    customer_email = cursor.fetchone()['email']

    cursor.close()
    conn.close()

    # We create a stripe checkout session and redirect the user to the stripe payment page
    # We provide the price, appointment type, and customer email to the session.
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': appointment_type,
                },
                'unit_amount': price,
            },
            'quantity': 1,
        }],
        mode='payment',
        # Upon a successful payment, redirect the user to the payment_success route with all the necessary data required to create a new booking record
        success_url=url_for('customer.payment_success', _external=True) + f'?session_id={{CHECKOUT_SESSION_ID}}&user_id={user_id}&slot_id={slot_id}&appointment_type={appointment_type}&payment_method={payment_method}',
        # Upon a canceled payment, redirect the user to the payment_cancel route with the same slot_id and date so the book_appointment page can be rendered with the flash msg indication
        cancel_url=url_for('customer.payment_cancel', _external=True) + f'?slot_id={slot_id}&date={date_str}',
        customer_email=customer_email
    )
    return redirect(session.url, code=303)

@customer.route('/payment_cancel', methods=['GET'])
def payment_cancel():
    # Get parameters from query string to render book_appointment page again
    slot_id = request.args.get('slot_id')
    date_str = request.args.get('date')
    user_id = session.get('user_id')

    # Flash a message to the user to let them know payment was canceled
    flash('Payment was canceled. You can try again or choose a different payment method.', 'warning')
    
    # Connect to database to get the timeslot information again
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get the selected timeslot again from database and format it for the page
    cursor.execute("""
                   SELECT start_time, end_time
                   FROM time_slots
                   WHERE slot_id = %s
                   """, (slot_id,))
    
    selected_slot = cursor.fetchone()
    
    # Format the date and time
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    display_date = date_obj.strftime('%B %d, %Y')
    
    # Format the time into 12-hour format
    selected_slot['formatted_start_time'] = format_time(selected_slot['start_time'])
    selected_slot['formatted_end_time'] = format_time(selected_slot['end_time'])
    
    cursor.close()
    conn.close()
    
    # Return to the book_appointment page with the same slot
    return render_template('book_appointment.html', 
                          display_date=display_date,
                          slot_id=slot_id,
                          user_id=user_id,
                          selected_slot=selected_slot)


@customer.route('/payment_success', methods=['GET'])
def payment_success():
    # Upon a success return from the stripe checkout session, we will need to add the new booking record
    # Get all the required data for the new record
    slot_id = request.args.get('slot_id')
    user_id = request.args.get('user_id')
    appointment_type = request.args.get('appointment_type')
    payment_method = request.args.get('payment_method')
    session_id = request.args.get('session_id')

    # Retrieve the stripe checkout session
    session = stripe.checkout.Session.retrieve(session_id)

    # Get the PaymentIntent ID
    payment_intent_id = session.get('payment_intent')

    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get service type_id and price for the appointment_type specified by user
        cursor.execute("""
            SELECT type_id, price
            FROM booking_types 
            WHERE type_name = %s
        """, (appointment_type,))
        service_type = cursor.fetchone()

        cursor.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
        customer_email = cursor.fetchone()['email']

        # Create payment transaction record using the payment_method and service_type price
        cursor.execute("""
            INSERT INTO payment_transactions 
            (payment_method, amount, stripe_transaction_id) 
            VALUES (%s, %s, %s)
        """, (payment_method, service_type['price'], payment_intent_id))
        
        # Get the transaction ID of the newly inserted record (ie: the last row)
        transaction_id = cursor.lastrowid

        # Insert booking record with the newly created transaction_id and assign it the
        # type_id, slot_id, and user_id it corresponds to
        cursor.execute("""
            INSERT INTO bookings 
            (customer_id, type_id, transaction_id, slot_id, appointment_status) 
            VALUES (%s, %s, %s, %s, 'current')
        """, (user_id, service_type['type_id'], transaction_id, slot_id))

        # Increment current bookings for the time slot (since new booking has been made)
        cursor.execute("""
            UPDATE time_slots 
            SET current_bookings = current_bookings + 1 
            WHERE slot_id = %s
        """, (slot_id,))

        # Get the time slot information for formatting the date and time for the receipt
        cursor.execute("""
            SELECT slot_date, start_time, end_time
            FROM time_slots
            WHERE slot_id = %s
        """, (slot_id,))
        slot_info = cursor.fetchone()
        
        # Format the date: "Monday, January 1, 2025"
        date_str = slot_info['slot_date'].strftime('%A, %B %d, %Y')
        
        # Format the time: "2:30 PM - 3:00 PM"
        start_time_str = format_time(slot_info['start_time'])
        end_time_str = format_time(slot_info['end_time'])
        time_str = f"{start_time_str} - {end_time_str}"
        
        # Commit the changes and alert user that they have successfuly booked the appointment
        conn.commit()

        # Construct and send receipt email
        msg = Message("Your Appointment Booking Receipt", recipients=[customer_email])
        msg.body = f"""
Thank you for booking!

Appointment Details:

- Service: {appointment_type}
- Date: {date_str}
- Time: {time_str}
- Amount Paid: ${service_type['price']}

Your stripe transaction ID is: {payment_intent_id}
"""
        mail.send(msg) #send the email
        
        # flash user that their booking was successfully made and a receipt has been sent to their email
        flash('Appointment booked successfully! A receipt has been sent to your email.', 'success')
        
    except Exception as e:
        # In the case of error, display the error msg to user
        flash(f'Error booking appointment: {str(e)}', 'error')
    
    finally:
        # Close the database connection
        cursor.close()
        conn.close()

    # Redirect to manage appointments page so the customer can now see their current bookings and all their past bookings
    return redirect(url_for('customer.manage_appointments'))

def update_appointment_statuses():
    # We need to update the appointments database each time we enter the manage_bookings page
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Update the bookings table appointment status based on current date and time

        # First check to ensure that all past bookings have the past status
        cursor.execute("""
            UPDATE bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            SET b.appointment_status = 'past'
            WHERE b.appointment_status = 'current' 
            AND CONCAT(ts.slot_date, ' ', ts.end_time) < NOW()
        """)

        # We also check to ensure that if any current bookings have been moved to the past then their status is changed
        # We need to do this because the admin is allowed to modify bookings and if they change the date/time of a booking
        # Such that it was upcoming previously and now it has a date/time that was in the past
        cursor.execute("""
            UPDATE bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            SET b.appointment_status = 'current'
            WHERE b.appointment_status = 'past' 
            AND CONCAT(ts.slot_date, ' ', ts.end_time) > NOW()
        """)
        # We commit changes to database
        conn.commit()

    except Exception as e:
        # If error happened we alert user
        print(f"Error updating appointment statuses: {str(e)}")

    finally:
        cursor.close()
        conn.close()

@customer.route('/manage_appointments', methods=['GET'])
def manage_appointments():
    # Update appointment statuses before displaying
    update_appointment_statuses()
    
    # Get user_id from session
    user_id = session.get('user_id')
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Fetch upcoming appointments and all the necessary data for displaying the booking on the page
        cursor.execute("""
            SELECT b.booking_id, ts.slot_date, ts.start_time, ts.end_time,
                   bt.type_name as service_type, pt.payment_method,
                   pt.stripe_transaction_id as stripe_id
            FROM bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            JOIN booking_types bt ON b.type_id = bt.type_id
            JOIN payment_transactions pt ON b.transaction_id = pt.transaction_id
            WHERE b.customer_id = %s 
            AND b.appointment_status = 'current'
            ORDER BY ts.slot_date ASC, ts.start_time ASC
        """, (user_id,))
        
        upcoming_appointments = cursor.fetchall()
        
        # Fetch completed appointments and all the necessary data for displaying the booking on the page
        cursor.execute("""
                SELECT b.booking_id, ts.slot_date, ts.start_time, ts.end_time,
                   bt.type_name as service_type, pt.payment_method, pt.stripe_transaction_id as stripe_id,
                   IFNULL(r.rating, 0) as rating, r.comment,
                   CASE WHEN r.review_id IS NULL THEN 0 ELSE 1 END as has_review
            FROM bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            JOIN booking_types bt ON b.type_id = bt.type_id
            JOIN payment_transactions pt ON b.transaction_id = pt.transaction_id
            LEFT JOIN reviews r ON b.booking_id = r.booking_id
            WHERE b.customer_id = %s 
            AND b.appointment_status = 'past'
            ORDER BY ts.slot_date DESC, ts.start_time ASC
        """, (user_id,))
        
        completed_appointments = cursor.fetchall()
        
        # format the necessary data appointments in the upcoming_appointments 
        for appointment in upcoming_appointments:
            # Format slot_date for display
            appointment['slot_date'] = appointment['slot_date'].strftime('%A, %B %d, %Y')
        
            # Format start and end times for the booking
            appointment['start_time'] = format_time(appointment['start_time'])
            appointment['end_time'] = format_time(appointment['end_time'])
        
            # Format the payment method for display
            if appointment['payment_method'] == 'in_store':
                appointment['payment_method'] = 'In-store'
            else:
                appointment['payment_method'] = 'Online'

        for appointment in completed_appointments:
            # Format slot_date for display
            appointment['slot_date'] = appointment['slot_date'].strftime('%A, %B %d, %Y')
        
            # Format start and end times for the booking
            appointment['start_time'] = format_time(appointment['start_time'])
            appointment['end_time'] = format_time(appointment['end_time'])
            
            # Format the payment method for display
            if appointment['payment_method'] == 'in_store':
                appointment['payment_method'] = 'In-store'
            else:
                appointment['payment_method'] = 'Online'
                
    except Exception as e:
        # In case of error, display the error msg and return empty upcoming and completed appointment lists
        flash(f'Error fetching appointments: {str(e)}', 'error')
        upcoming_appointments = []
        completed_appointments = []
    
    finally:
        # Close cursor and booking
        cursor.close()
        conn.close()
    
    # Render the manage_appointments page with upcoming appointments and completed appointments information
    return render_template('manage_appointments.html', 
                          upcoming_appointments=upcoming_appointments, 
                          completed_appointments=completed_appointments)


@customer.route('/cancel_booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get the slot record to be decremented alongside the booking record along with all booking details
        cursor.execute("""
            SELECT b.booking_id, b.slot_id
            FROM bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            WHERE b.booking_id = %s
        """, (booking_id,))
        
        booking = cursor.fetchone()
        
        # Decrement the current_bookings count in the time_slots table corresponding to the booking
        cursor.execute("""
            UPDATE time_slots
            SET current_bookings = current_bookings - 1
            WHERE slot_id = %s
        """, (booking['slot_id'],))

        # Set the appointment status to cancel for the booking
        cursor.execute("""
            UPDATE bookings
            SET appointment_status = 'cancel'
            WHERE booking_id = %s
            """, (booking_id,))
        
        # Add notification to booking_notifications table
        cursor.execute("""
            INSERT INTO booking_notification
            (booking_id, read_status) 
            VALUES (%s, FALSE)
        """, (booking_id,))

        # Get the slot record to be decremented alongside the booking record along with all booking details
        cursor.execute("""
            SELECT b.booking_id, b.slot_id, b.customer_id, b.appointment_status,
                   ts.slot_date, ts.start_time, ts.end_time,
                   u.name, u.email, bt.type_name, pt.amount, pt.payment_method,
                   pt.stripe_transaction_id
            FROM bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            JOIN users u ON b.customer_id = u.user_id
            JOIN booking_types bt ON b.type_id = bt.type_id
            JOIN payment_transactions pt ON b.transaction_id = pt.transaction_id
            WHERE b.booking_id = %s
        """, (booking_id,))

        booking = cursor.fetchone()

        date_str = booking['slot_date'].strftime('%A, %B %d, %Y')
        start_time_str = format_time(booking['start_time'])
        end_time_str = format_time(booking['end_time'])
        time_str = f"{start_time_str} - {end_time_str}"
        
        # Format payment method with the type of payment method that was selected
        if booking['payment_method'] == 'in_store':
            payment_method = "In-store"
        else:
            payment_method = "Online"

        customer_email = booking['email']

        # Format the transaction ID for the email, if it was a stripe transaction include it, if not then return empty string
        stripe_id = booking.get('stripe_transaction_id')
        if booking.get('payment_method') == 'stripe' and stripe_id:
            transaction_id = f"- Stripe Transaction ID: {stripe_id}"
        else:
            transaction_id = ""

        msg = Message("Appointment Cancellation Notification", recipients=[customer_email])
        
        # This is the creation of the email
        msg.body = f"""Hello {booking['name']},
Your appointment has been successfully cancelled.

Appointment Details:

- Service: {booking['type_name']}
- Date: {date_str}
- Time: {time_str}
- Payment Method: {payment_method}
- Amount: ${booking['amount']}
{ transaction_id }
"""
        
        # This will send the email to all admins
        mail.send(msg)

        # Commit changes
        conn.commit()
        
        # If it was a success, indicate to user
        flash('Booking cancelled successfully', 'success')
        
    except Exception as e:
        # If there is any error, rollback and display error
        conn.rollback()
        flash(f'Error cancelling booking: {str(e)}', 'error')
        
    finally:
        cursor.close()
        conn.close()
    
    # Re-render the manage_appointments page
    return redirect(url_for('customer.manage_appointments'))

@customer.route('/review/<int:booking_id>', methods=['GET'])
def review(booking_id):
    customer_id = session.get('user_id')

    if not booking_id or not customer_id:
        flash('Missing booking or customer information.', 'error')
        return redirect(url_for('customer.manage_appointments'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ts.slot_date
        FROM bookings b
        JOIN time_slots ts ON b.slot_id = ts.slot_id
        WHERE b.booking_id = %s
    """, (booking_id,))
    appointment = cursor.fetchone()
    conn.close()

    if appointment:
        appointment_date = appointment[0].strftime('%A, %B %d, %Y')
    else:
        appointment_date = "Date not found"

    return render_template('review.html',
                           booking_id=booking_id,
                           customer_id=customer_id,
                           appointment_date=appointment_date)

@customer.route('/submit_review', methods=['POST'])
def submit_review():
    booking_id = request.form['booking_id']
    customer_id = request.form['customer_id']
    rating = request.form['rating']
    review_text = request.form['review_text']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check for existing review
    cursor.execute("""
        SELECT * FROM reviews WHERE booking_id = %s AND customer_id = %s
    """, (booking_id, customer_id))
    existing_review = cursor.fetchone()

    if existing_review:
        conn.close()
        flash('You have already submitted a review for this appointment.', 'info')
        return redirect(url_for('customer.manage_appointments'))

    # Insert the new review
    cursor.execute("""
        INSERT INTO reviews (booking_id, customer_id, rating, comment)
        VALUES (%s, %s, %s, %s)
    """, (booking_id, customer_id, rating, review_text))
    conn.commit()
    conn.close()

    flash('Review submitted successfully!', 'success')
    return redirect(url_for('customer.manage_appointments'))

def allowed_to_book(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Count the number of active bookings for the customer passed into the method
        cursor.execute("""
            SELECT COUNT(*) as booking_count
            FROM bookings
            WHERE customer_id = %s AND appointment_status = 'current'
        """, (user_id,))
        
        result = cursor.fetchone()
            
    except Exception as e:
        # In the case of an error, display the error message and return 0 active bookings
        print(f"Error counting customer bookings: {str(e)}")
        return 0
    finally:
        cursor.close()
        conn.close()

    if result['booking_count'] >= 3:
        return False
    else:
        return True

def send_appointment_reminders():
    # Notification reminder method that runs upon app startup and once every day to send
    # email notifications to customers who have appointments scheduled for the next day

    # Calculate tomorrow's date (current date + 1 day)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y-%m-%d')
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try: 
        # Query for appointments happening tomorrow 
        cursor.execute("""
            SELECT ts.slot_date, ts.start_time, ts.end_time,
                    u.name, u.email
            FROM bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            JOIN users u ON b.customer_id = u.user_id
            WHERE ts.slot_date = %s
            AND b.appointment_status = 'current'
        """, (tomorrow_str,))
        
        appointments = cursor.fetchall()
            
        # For each appointment scheduled for tommorrow we will compose a email notification and send it.
        for appointment in appointments:
            # Format the date and timeslots to display in the email
            date_str = appointment['slot_date'].strftime('%A, %B %d, %Y')
            start_time_str = format_time(appointment['start_time'])
            end_time_str = format_time(appointment['end_time'])
            
            # Generate the email to be sent
            subject = "Appointment Reminder: Your Visit Tomorrow"
            body = f"""
    Hello {appointment['name']},

    You have an appointment scheduled for tomorrow:

    - Date: {date_str}
    - Time: {start_time_str} - {end_time_str}

    If you can't make it, please reschedule or cancel your appointment through the EasyBook website.
    """
            # Send the email to the customer
            msg = Message(subject=subject, recipients=[appointment['email']], body=body)
            mail.send(msg)
                
    except Exception as e:
        # If an error occurs, display the error message
        print(f"Error sending appointment reminders: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()
