from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db_connection
import calendar
import datetime

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
        
        # Commit the changes and alert user that they have successfuly booked the appointment
        conn.commit()
        flash('Appointment booked successfully!', 'success')
        
        # Redirect to manage appointments or homepage
        return redirect(url_for('customer.manage_appointments'))
    
    except Exception as e:
        # In the case of error, return the customer to the homepage and display a error msg
        flash(f'Error booking appointment: {str(e)}', 'error')
        return redirect(url_for('customer.customer_homepage'))
    
    finally:
        cursor.close()
        conn.close()

@customer.route('/online_payment', methods=['GET', 'POST'])
def online_payment():
    appointment_type = request.args.get('appointment_type')
    slot_id = request.args.get('slot_id')
    payment_method = request.args.get('payment_method')
    user_id = request.args.get('user_id')

    # TODO: Implement Stripe Online Payment System here to process online payments

    return render_template('online_payment.html', 
                    appointment_type=appointment_type,
                    slot_id=slot_id,
                    payment_method=payment_method,
                    user_id=user_id)

@customer.route('/manage_appointments', methods=['GET', 'POST'])
def manage_appointments():

    return render_template('manage_appointments.html') 