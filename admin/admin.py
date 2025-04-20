from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db_connection
import calendar
import datetime
from extensions import mail, Message
admin = Blueprint('admin', __name__, template_folder='templates', static_folder='static')

############## Notes for using datetime module ###############

# 1. datetime.date object's format: YYYY-MM-DD
# 2. datetime.datetime object's format: YYYY-MM-DD HH:MM:SS
# 3. datetime.timedelta object's format: HH:MM:SS

# MySQL DATE datatypes corresponds to datetime.date objects
# MySQL TIME datatypes corresponds to datetime.timedelta objects
# If we want to format any datetime object to a string we need to use the strftime() method

###########################
# PROPERTIES of datetime.date object:
# .year - returns the year (YYYY)
# .month - returns the month (1-12)
# .day - returns the day of the month (1-31)

# METHODS of datetime.date object:
# .strftime(format) - returns a string representation of the date object in the specified format
#    %A - Full weekday name
#    %B - Full month name
#    %d - Day of the month (01-31)
#    %Y - Year with century (YYYY)
#    %m - Month as a zero-padded decimal number (01-12)
#    %H - Hour (00-23)
#    %M - Minute (00-59)
#    %S - Second (00-59)
# .weekday() - returns numerical value representing day of the week (0 = Monday, 6 = Sunday)
# .today() - returns the current date as a date object
###########################


###########################
# PROPERTIES of datetime.timedelta object:
# .seconds - returns the seconds of the time object (HH:MM:SS)
# .days - returns the days of the time object (number of days)

# METHODS of datetime.timedelta object:
# .total_seconds() - returns the total seconds of the time object
# .seconds() - returns the seconds of the time object (HH:MM:SS)
###########################


###########################
# PROPERTIES of datetime.datetime object:
# .year - returns the year (YYYY)
# .month - returns the month (1-12)
# .day - returns the day of the month (1-31)
# .hour - returns the hour (0-23)
# .minute - returns the minute (0-59)
# .second - returns the second (0-59)

# METHODS of datetime.datetime object:
# .strftime(format) - returns a string representation of the datetime object in the specified format
#    %A - Full weekday name
#    %B - Full month name
#    %d - Day of the month (01-31)
#    %Y - Year with century (YYYY)
#    %m - Month as a zero-padded decimal number (01-12)
#    %H - Hour (00-23)
#    %M - Minute (00-59)
#    %S - Second (00-59)
# .time() - returns the time object from the datetime object
# .today() - returns the current date as a datetime object
##################################################################

@admin.route('/homepage', methods=['GET', 'POST'])
def admin_homepage():
    # Render homepage for admin, including the calendar, buttons, bookings, shifts, etc...

    # Get username from session to display on the homepage
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
        # If no date is provided (ie: first time admin logs in) we set the selected_date to the current day
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
    
    # Get shifts and bookings for the selected_date (Used for displaying shift and bookings for selected_date)
    shifts = get_shifts_for_date(selected_date)
    bookings = get_bookings_for_date(selected_date)

    # Get business hours for the selected date
    # weekday() will give a numerical value to the day of the week (0 = Monday, 6 = Sunday)
    weekday = selected_date.weekday()  
    if weekday == 5 or weekday == 6:  
        # On weekends business hours are 10AM - 4PM
        business_hours = "10AM - 4PM"
    else:  
        # On weekdays business hours are 9AM - 5Pm
        business_hours = "9AM - 5PM"
    
    # Finaally we pass in all the data required to render the homepage components (calendar, shifts, bookings, etc)
    return render_template('admin_homepage.html', 
                          name=name, # Displayed on the top right of the page
                          calendar_weeks=calendar_weeks, # Calendar object which contains all the days information stored as dictonaries.
                          selected_date=selected_date.strftime('%Y-%m-%d'), # The selected date in the format YYYY-MM-DD (ie date object)
                          display_date=display_date, # The selected date in the format (ie: Monday, January 01) shown on the right side of the page
                          current_month=current_month, # The current month number (1-12)
                          current_year=current_year, # The current year (YYYY)
                          current_month_name=current_month_name, # The current month name (ie: January)
                          is_blocked=is_blocked, # Boolean value indicating if the selected_date is blocked or not (used for configuring button text)
                          business_hours=business_hours, # Business hours for the selected-date (displayed on the right)
                          shifts=shifts, # List of dictionaries containing shifts for the selected_date (shown on the right)
                          bookings=bookings) # List of dictionaries containing bookings for the selected_date (shown on the right)

def generate_calendar(year, month, selected_date):
    # We will create a calendar object that can be utilized in the html template for the calendar component using Jinja2
    # In order to do this, we need to get the very first day of the month (ex: March 1, 2025)
    # We need to get the day of the week of the first day of the month (ex: March 1, 2025 is a Saturday)
    # Lastly, we need to get the total number of days that are in the current month (ex: March has 31 days)
    # Using this information we can generate a calendar list in which each entry is a list (corresponding to weeks)
    # And in each week is a dictionary object containing information for a certain day of the month: day, date, and class (business or blocked)
    first_day = datetime.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    
    # Get the day of the week for the first day (0 = Monday, 6 = Sunday) For instance, March 1, 2025 is a Saturday so it will return 5
    first_weekday = first_day.weekday()
    
    # Get current date for comparing past dates
    today = datetime.date.today()

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
                current_date = datetime.date(year, month, day)
                date_str = current_date.strftime('%Y-%m-%d')
                
                # Check if its a past date and is not blocked
                if current_date < today and date_str not in blocked_dates:
                    day_class = 'past-day'

                # Check if the current day is blocked
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

def get_shifts_for_date(date):
    # We will get a list of the shifts in the database for the selected date (used to display shifts on the right side of the page)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try: 
        # We will run a query that joins the user and employee tables on the foreign key of user_id
        # We need to do this because the user table contains the employee names and the shifts table contains the start_time and end_time
        # Of the shifts, all three of these pieces of data are required for us to display the shifts on the right side of the page
        # We will place the condition where the shift date is the current date and order the results by start_time
        # We order them because so when we display the shifts on the right side of the page they are in order easier to read.
        cursor.execute("""
            SELECT s.shift_id, s.start_time, s.end_time, u.name as employee_name
            FROM shifts s
            JOIN users u ON s.employee_id = u.user_id
            WHERE s.shift_date = %s
            ORDER BY s.start_time""", (date,))
        
        # We fetch all the results of the query and store them in the shifts variable
        shifts = cursor.fetchall()
        
        # When we query the shift start and end times they are of TIME datattypes in the database 
        # and are returned as datetime.timedelta objects
        # These have the format of 'HH:MM:SS' and are military time; however, we need the time to be formatted
        # In a 12-hour format with AM/PM (for example 2:00 PM instead of 14:00:00)
        # So we will use the format_time helper method to convert the start and end times to this format and do this
        # for every result from the query.
        for shift in shifts:
            shift['start_time'] = format_time(shift['start_time'])
            shift['end_time'] = format_time(shift['end_time'])

    except Exception as e:
        # If there is an error we flash the error message to the user
        flash(f'Error fetching shifts: {str(e)}', 'error')
        shifts = [] # We set shifts to an empty list in the case of an error

    finally:
        # We close the database and cursor
        cursor.close()
        conn.close()
    
    # We return the shifts list which contains all the shifts for the selected date
    # Each shift is a dictionary object containing the start_time, end_time, and employee_name
    return shifts

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

def get_bookings_for_date(date):
    # We will get a list of the bookings in the database for the selected date (used to display bookings on the bottom right side of the page)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # We develop a query to find the start_time, end_time, customer name, service type, and payment method, these are all the data we want to render for the selected day
        # We need to join the bookings table, time_slots table, users table, and payment_transactions table to get this data
        # To do this we will use the foreign keys in the tables to join them together 
        # We will place the condition where the slot_date is the current date and order the results by start_time (so that when we display it its in order)
        # Also have the condition to make sure the appointment wasn't cancelled.
        cursor.execute("""
            SELECT ts.start_time, ts.end_time, 
                u.name as customer_name, bt.type_name as service_type,
                pt.payment_method
            FROM bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            JOIN users u ON b.customer_id = u.user_id
            JOIN booking_types bt ON b.type_id = bt.type_id
            JOIN payment_transactions pt ON b.transaction_id = pt.transaction_id
            WHERE ts.slot_date = %s AND b.appointment_status != 'cancel'
            ORDER BY ts.start_time
        """, (date,))
        
        # We will get all the results of the query and store them in the bookings variable
        bookings = cursor.fetchall()
        
        # Same as in the shifts method, we need to convert the start and end times from the database (TIME datatypes) to a 12-hour format with AM/PM
        for booking in bookings:
            booking['start_time'] = format_time(booking['start_time'])
            booking['end_time'] = format_time(booking['end_time'])
            
            # Additionally, we want to convert the payment method into either In-store or Online (admin is not concerned with type of transaction for online payments)
            # They only want to difficiate between in-store and online payments also we need to have proper grammar on the page
            if booking['payment_method'] == 'in_store':
                booking['payment_method'] = 'In-store'
            else:
                booking['payment_method'] = 'Online'

    except Exception as e:
        # If there is an error we flash the error message to the user
        flash(f'Error fetching bookings: {str(e)}', 'error')
        bookings = [] # and send back an empty bookings list

    finally:
        # close cursor n connection
        cursor.close()
        conn.close()
    
    # We return the bookings list which contains all the bookings for the selected date
    # Each booking is a dictionary object containing the start_time, end_time, customer_name, service_type, and payment_method
    return bookings

@admin.route('/manage_accounts', methods=['GET', 'POST'])
def manage_accounts():
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get all users in the database so that the manage_accounts.html page can render them.
        cursor.execute("SELECT user_id, name, email, password, permission FROM users")
        users = cursor.fetchall()

    except Exception as e:
        # In the case of an exception we flash the exception to the user
        flash(f'Error fetching user accounts: {str(e)}', 'error')

    finally:
        cursor.close()
        conn.close()
    
    return render_template('manage_accounts.html', users=users)

@admin.route('/toggle_block_date', methods=['POST'])
def toggle_block_date():
    # Handle the blocking and unblocking of dates
    # This will be called when the admin clicks the block/unblock button on the calendar
    # Get the date and current status from the form
    # The date will be in the format 'YYYY-MM-DD' and the current status is either 'blocked' or 'unblocked'
    date_str = request.form.get('date')
    current_status = request.form.get('current_status')
    
    # Convert string date to datetime object since we need to compare it with the date in the database and
    # the database has datetime objects
    block_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()

    # Get the admin id from the session 
    admin_id = session.get('user_id')
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try: 
        # If the current_status is blocked then we need to unblock the date
        if current_status == 'blocked':
            # Unblock the date by deleting the date entry from the block_days table
            cursor.execute("DELETE FROM block_days WHERE date = %s", (block_date,))
            # Alert admin if successful
            flash('Date has been unblocked successfully!', 'success')
        else:
            # Block the date by inserting the date into the block_days table
            cursor.execute("INSERT INTO block_days (date, set_by) VALUES (%s, %s)", 
                        (block_date, admin_id))
            # Alert admin if succesful
            flash('Date has been blocked successfully!', 'success')

        # We commit changes to the database
        conn.commit()

    except Exception as e:
        # If there is an error we flash the error message to the user
        flash(f'Error blocking/unblocking date: {str(e)}', 'error')
        # Rollback the transaction in case of error (important when updating/deleting data)
        conn.rollback()

    finally:
        # Close the cursor and connection to the database
        cursor.close()
        conn.close()
    
    # Redirect back to the admin homepage with the same date selected 
    # (this will cause the page to render again but with the change being reflected in the calendar and in the text of the block day button)
    return redirect(url_for('admin.admin_homepage', selected_date=date_str))

@admin.route('/add_accounts', methods=['GET', 'POST'])
def add_accounts():
    # Handle form submission (POST REQ)
    if request.method == 'POST':
        # Retrieve form info
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        permission = request.form.get('permission')
        
        # Make sure all the data was entered and no missing values
        if not name or not email or not password or not permission:
            flash('All fields are required.', 'error')
            return render_template('add_accounts.html')

        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Check if email already exists (Cant create accounts with same email since email uniqu)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Flash error msg that the email is taken and re-render the form.
                flash('Email already registered', 'error')
                return render_template('add_accounts.html')
            
            # If all info in the form is entered and the email is unique, we add it to database
            cursor.execute(
                "INSERT INTO users (name, email, password, permission) VALUES (%s, %s, %s, %s)",
                (name, email, password, permission)
            )
            conn.commit()
            
            # Flash msg that it was added
            flash('User account created successfully!', 'success')
            return redirect(url_for('admin.add_accounts'))
            
        except Exception as e:
            # Flash error msg containing the exception
            flash(f'Error creating account: {str(e)}', 'error')
            # Render the page again for the user
            return render_template('add_accounts.html')
        finally:
            # Close database connection and cursor when finished with query logic.
            cursor.close()
            conn.close()
    
    # Display the form for every GET req
    return render_template('add_accounts.html')

@admin.route('/edit_account/<int:user_id>', methods=['GET','POST'])
def edit_account(user_id):
    
    # Connect to database to retrieve the record of current user for GET requests and
    # execute queries for the POST requests.
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Use the passed in user_id to retrieve the user record
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user_record = cursor.fetchone() # Store user_record (pass it in each time you render the page again)

        if request.method == 'POST':
            # Get form data
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            permission = request.form['permission']
            
            # If the user attempts to make a change but hasn't modified any form data notify them
            # that no modifications where made and render the page again.
            if name == user_record['name'] and email == user_record['email'] and password == user_record['password'] and permission == user_record['permission']:
                flash('No modifications where made', 'warning')
                return render_template('edit_accounts.html', user_id=user_id, user_record=user_record)

            # Otherwise, execute a query to count the number of users with a matching email as the one inputted by the user in the form
            cursor.execute(
                "SELECT COUNT(*) as count FROM users WHERE email = %s AND user_id != %s", 
                (email, user_id)
            )
            result = cursor.fetchone()

            # Make sure no other accounts exists with the entered email (emails must be unique)
            if result['count'] > 0:
                # Indicate to user that the email they want to update this record with is already in use
                flash('Email already in use by another user', 'warning')
                return render_template('edit_accounts.html', user_id=user_id, user_record=user_record)
            
            # If all test cases are passed (ie: data was modificated, no duplicate email exists) then run the update query on the 
            cursor.execute(
                "UPDATE users SET name = %s, email = %s, permission = %s, password = %s WHERE user_id = %s",
                (name, email, permission, password, user_id)
            )

            # Commit the changes made into the database
            conn.commit()
            # Alert user of successful update
            flash('User updated successfully', 'success')
            # Return user back to manage_accounts page
            return redirect(url_for('admin.manage_accounts'))
    
    except Exception as e:
        # Flash any exceptions that may arise during the process (ex: database crashes)
        flash(f'Error processing account: {str(e)}', 'error')
    finally:
        # Always got to close cursor and database connection
        cursor.close()
        conn.close()
    
    # render template with user_id and user_record in the case of GET requests or exceptions
    return render_template('edit_accounts.html', user_id=user_id, user_record=user_record)

@admin.route('/inbox', methods=['GET'])
def inbox():
    # Going to show employee name, request type, shift date, start time, end time, and reason for each shift change request
    # Only going to show the messages that haven't been read by the admin
    # Going to show messages in order of date
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get the selected request ID from URL parameters
    request_id = request.args.get('request_id')
    
    try:
        # Get all columns of data required to show the change requests
        cursor.execute("""
            SELECT r.request_id, u.name, r.request_type, s.shift_date, s.start_time, s.end_time, r.reason, r.read_status, u.email
            FROM shift_change_requests r 
            JOIN shifts s ON r.shift_id = s.shift_id
            JOIN users u ON r.employee_id = u.user_id
            WHERE r.read_status = FALSE
            ORDER BY s.shift_date ASC, s.start_time ASC
        """)
       
        requests = cursor.fetchall()

        # For each request we need to format the shift time and shift date so we can display it in a better way on the page
        for req in requests:
            req['start_time'] = format_time(req['start_time'])
            req['end_time'] = format_time(req['end_time'])
            req['shift_date'] = req['shift_date'].strftime('%B %d, %Y')
        
        # This is handling when the admin clicks on the inbox, that the first request_id is being selected 
        # as no request_id is passed in
        if not request_id and requests:
            request_id = requests[0]['request_id']

        # This is to initialize the current_request variable to None
        current_request = None
        # This is the request_id that has been defaulted to previously
        if request_id:
            # This is being used to create a list where requests where the ID matches our request_id, some type matching is done
            matching_requests = [req for req in requests if str(req['request_id']) == str(request_id)]
            # If there are any matching requests, we set the current_request to only one in the list
            if matching_requests:
                current_request = matching_requests[0]

    except Exception as e:
        # Alert user of any error and render the page without requests in the case of error
        flash(f'Error fetching inbox messages: {str(e)}', 'error')
        # Set the current_request to None and requests to an empty list in case of error
        requests = []
        current_request = None
    finally:
        # close cursor and database connection
        cursor.close()
        conn.close()
    
    # Render the inbox page with all shift change requests and the current_request that it is on
    return render_template('inbox.html', requests=requests, current_request=current_request, current_request_id=request_id)

@admin.route('/mark_as_read/<int:request_id>', methods=['POST'])
def mark_as_read(request_id):
    # Going to flip value of read_status to true if user clicks "market as read"
    # Going to alert user if it is a succcess or if any error occur

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Update the read_status in the shift_change_requests table for the request_id passed into the route
        cursor.execute("UPDATE shift_change_requests SET read_status = TRUE WHERE request_id = %s", 
                      (request_id,))
        #gets email of the employee who made the request
        cursor.execute("""
            SELECT u.email, s.shift_date
            FROM shift_change_requests r
            JOIN shifts s ON r.shift_id = s.shift_id
            JOIN users u ON r.employee_id = u.user_id
            WHERE r.request_id = %s
        """, (request_id,))
        
        employee = cursor.fetchone()

        display_date = employee['shift_date'].strftime('%A, %B %d')

        if employee and employee['email']:
            msg = Message(
                subject="Shift Change Request Acknowledged",
                recipients=[employee['email']]
            )
            msg.body = f"Hello your shift change request on { display_date } has been acknowledged by the admin.\n\nThank you."

            try:
                mail.send(msg)
                print(f"Email Sent")
            except Exception as e:
                print(f"Failed to send email: {e}")
        
        # commit the change and alert user of success
        conn.commit()
        flash('Request marked as read', 'success')

    except Exception as e:
        # Alert user of any error
        flash(f'Error marking request as read: {str(e)}', 'error')

    finally:
        # close cursor and db connection
        cursor.close()
        conn.close()

    # re-render the inbox page (this time the request marked as read will not be shown to the admin)
    return redirect(url_for('admin.inbox'))

@admin.route('/manage_shift/<selected_date>', methods=['GET'])
def manage_shift(selected_date):
    # Convert string date to datetime object
    shift_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()
    
    # Format date for display
    display_date = shift_date.strftime('%A, %B %d')
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get all shifts for the selected date store the shift_id, employee_id, start_time, end_time, and username in each record
        cursor.execute("""
            SELECT s.shift_id, s.employee_id, s.start_time, s.end_time, u.name as employee_name
            FROM shifts s
            JOIN users u ON s.employee_id = u.user_id
            WHERE s.shift_date = %s
            ORDER BY s.start_time
        """, (shift_date,))
        
        shifts = cursor.fetchall()
        
        # Format times for display and form values
        for shift in shifts:
            # Get raw datetime.timedelta objects for form handling (this will require formating)
            start_time = shift['start_time']
            end_time = shift['end_time']
            
            # Format for display using the format_time method
            shift['formatted_start_time'] = format_time(start_time) 
            shift['formatted_end_time'] = format_time(end_time)
            
            # After we use the method, it will have the form '2:00 PM'
            # We want to segment the time and the period so we split it on the delimiter
            start_components = shift['formatted_start_time'].split(' ')
            end_components = shift['formatted_end_time'].split(' ')

            # We store the time component and the period components.
            shift['start_time'] = start_components[0]
            shift['start_period'] = start_components[1]

            shift['end_time'] = end_components[0]
            shift['end_period'] = end_components[1]

        # Get all employee names so we can show them in the dropdown menue
        # Also get the user_id so we know what the user_id is if the admin decides to modify an appointment
        cursor.execute(
            """
            SELECT user_id, name
            FROM users
            WHERE permission = 'employee'
            """
        )
        
        employees = cursor.fetchall()
        
    except Exception as e:
        # In case of error, display error and return empty shifts and employees lists
        flash(f'Error fetching shift data: {str(e)}', 'error')
        shifts = []
        employees = []
    
    finally:
        cursor.close()
        conn.close()
    
    # render the page with the display date, the shifts, and the employees
    # pass the selected_date back so we can continue to utilize it
    return render_template('manage_shifts.html', 
                          selected_date=selected_date,
                          display_date=display_date,
                          shifts=shifts,
                          employees=employees)

@admin.route('/update_shift/<int:shift_id>/<selected_date>', methods=['POST'])
def update_shift(shift_id, selected_date):
    # Get form data (any of these are subject to be modified/updated)
    employee_id = request.form.get('employee_id')
    start_time = request.form.get('start_time')

    start_period = request.form.get('start_period')
    end_time = request.form.get('end_time')
    end_period = request.form.get('end_period')

    # Initialize connection and cursor as None, this is a placeholder cursor and connection
    conn = None
    cursor = None
    
    try:
        # Since we will be updating the data in the database, we need to convert the format of the start time and endtime
        # Currently the times are formatted as (H:M period [AM/PM])
        # We will convert back into SQL TIME strings (formatted as H:M:S)
        start_datetime = datetime.datetime.strptime(f"{start_time} {start_period}", "%I:%M %p")
        end_datetime = datetime.datetime.strptime(f"{end_time} {end_period}", "%I:%M %p")

        # Format as SQL TIME strings
        formatted_start_time = start_datetime.strftime("%H:%M:%S")
        formatted_end_time = end_datetime.strftime("%H:%M:%S")
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update shift in database using the SQL TIME formatted times for the shift
        cursor.execute("""
            UPDATE shifts 
            SET employee_id = %s, start_time = %s, end_time = %s
            WHERE shift_id = %s
        """, (employee_id, formatted_start_time, formatted_end_time, shift_id))
        
        # Commit changes and alert user of success
        conn.commit()
        flash('Shift updated successfully', 'success')

    except Exception as e:
        # In case of error flash message to user
        flash(f'Error updating shift: {str(e)}', 'error')

    finally:
        # Close cursor and connection if they were opened, this is to make sure it actually contained a cursor object and connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    # Render page again passing the selected_date so we can continue to utilize it
    return redirect(url_for('admin.manage_shift', selected_date=selected_date))

@admin.route('/add_shift', methods=['POST'])
def add_shift():
    # Get form data (this info will be added to the shifts table)
    employee_id = request.form.get('employee_id')
    shift_date = request.form.get('shift_date')
    
    start_time = request.form.get('start_time')
    start_period = request.form.get('start_period')

    end_time = request.form.get('end_time')
    end_period = request.form.get('end_period')

    # Initialize connection and cursor as None, this is a placeholder cursor and connection
    conn = None
    cursor = None
    
    try:
        # Parse dates and times so it conforms to the SQL TIME structure
        shift_date_obj = datetime.datetime.strptime(shift_date, '%Y-%m-%d').date()

        start_datetime = datetime.datetime.strptime(f"{start_time} {start_period}", "%I:%M %p")
        end_datetime = datetime.datetime.strptime(f"{end_time} {end_period}", "%I:%M %p")

        # Format as SQL TIME string
        formatted_start_time = start_datetime.strftime("%H:%M:%S")
        formatted_end_time = end_datetime.strftime("%H:%M:%S")
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add shift to database
        cursor.execute("""
            INSERT INTO shifts (employee_id, shift_date, start_time, end_time)
            VALUES (%s, %s, %s, %s)
        """, (employee_id, shift_date_obj, formatted_start_time, formatted_end_time))
        
        # commit changes and alert user of succes
        conn.commit()
        flash('New shift added successfully', 'success')

    except Exception as e:
        # In case of error, flash msg
        flash(f'Error adding shift: {str(e)}', 'error')
    
    finally:
        # Close cursor and connection if they were opened, this is to make sure it actually contained a cursor object and connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    
    # Render the page again passing in the selected_date
    return redirect(url_for('admin.manage_shift', selected_date=shift_date))

@admin.route('/delete_shift/<int:shift_id>/<selected_date>', methods=['POST'])
def delete_shift(shift_id, selected_date):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Delete the shift change requests associated with the shift_id, if not deleted will cause foreign key error
        cursor.execute("DELETE FROM shift_change_requests WHERE shift_id = %s", (shift_id,))
       
        # Delete the shift with the passed in shift_id
        cursor.execute("DELETE FROM shifts WHERE shift_id = %s", (shift_id,))
        
        # Commit the change and alert the user of sucess
        conn.commit()
        flash('Shift deleted successfully', 'success')

        # Render the page again with the selected date
        return redirect(url_for('admin.manage_shift', selected_date=selected_date))
    except Exception as e:
        # In case of error flash the error msg
        flash(f'Error deleting shift: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    # In case of error, we re-render the page so that the flash msg is displayed
    return redirect(url_for('admin.manage_shift', selected_date=selected_date))

@admin.route('/manage_bookings', methods=['GET', 'POST'])
def manage_bookings():
    # each time we enter this route we need to update the bookings table so appointment status are up to date
    update_appointment_statuses() 

    # Set default values for the parameters (this is the default filter for when user loads up page)
    status_filter = 'all' 
    date_filter = None
    service_filter = 'all'
    rating_filter = 'any'
    name_filter = None

    # If it is a POST method, that means the filter settings may have changed, so we retrieve the new filter settings from form
    if request.method == "POST":
        status_filter = request.form.get('status', 'all')
        date_filter = request.form.get('date', None)
        service_filter = request.form.get('service', 'all')
        rating_filter = request.form.get('rating', 'any')
        name_filter = request.form.get('searchname', None)
    # This is the GET method for when the admin clicks on the modify bookings button, to have the filter loaded with the selected date
    else:
        date_filter = request.args.get('selected_date', None)

    # We need to query the database for the data based on the current filter settings:  
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Start building the base query, we will display the date, start_time, end_time, name, service type, payment method, appointment status, and comments
        # We need to join the necessary tables to retrieve this data and include a WHERE clause so we can append additional queries
        # Based on filter settings that may have been changed in a POST request
        query = """
            SELECT b.booking_id, ts.slot_date, ts.start_time, ts.end_time,
                   u.name as customer_name, bt.type_name as service_type,
                   pt.payment_method, b.appointment_status,
                   IFNULL(r.rating, 0) as rating,
                   comment
            FROM bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            JOIN users u ON b.customer_id = u.user_id
            JOIN booking_types bt ON b.type_id = bt.type_id
            JOIN payment_transactions pt ON b.transaction_id = pt.transaction_id
            LEFT JOIN reviews r ON b.booking_id = r.booking_id
            WHERE 1=1
        """

        # We will include all the additional filters in the new_filter list
        new_filter = []

        # If the status_filter != all then it means the user entered a new filter 
        # We append the statement to the where clause and store the new status_filter in the list
        if status_filter != 'all':
            query += " AND b.appointment_status = %s"
            new_filter.append(status_filter)
        
        # If the date_filter is not None then that means the user specified a date
        # We append the where clause with to search only for the specified date and store the new date_filter in the list
        if date_filter:
            query += " AND ts.slot_date = %s"
            new_filter.append(date_filter)
        
        # If the service_filter != all then that means the user specified a service type 
        # We append to the where clause the condition that the service type matches and store the new service_filter in the list
        if service_filter != 'all':
            query += " AND bt.type_name = %s"
            new_filter.append(service_filter)
        
        # If the rating_filter != any then it was changed from the default 
        # We specify in the query to search only for the necessary rating and append the integer value of the new rating_filter
        if rating_filter != 'any':
            query += " AND (r.rating >= %s)"
            new_filter.append(int(rating_filter))
        
        # If name_filter isn't none then we search for any name with contains the entered text
        # and we append %name_filter% to the list (we need to have %% due to sql syntax when using LIKE)
        # anything before %name_filter% anything after
        if name_filter:
            query += " AND u.name LIKE %s"
            new_filter.append(f"%{name_filter}%")
        
        # We will order the results by date in descending order (so the newest bookings appear at the top)
        # And start time in ascending order so the earliest times appear first
        query += " ORDER BY ts.slot_date DESC, ts.start_time ASC"
        
        # We execute the query and pass in the values stored in the new_filters list (these are specified by user)
        cursor.execute(query, new_filter)
        bookings = cursor.fetchall()

        # Format dates, times, and payment_method
        for booking in bookings:

            # Override the old slot_date (datatype DATE) with the formatted version
            if booking['slot_date']:
                booking['slot_date'] = booking['slot_date'].strftime('%B %d, %Y')
            
            # Override the old start/end times (datatype TIME) with the formatted versions
            if booking['start_time']:
                booking['start_time'] = format_time(booking['start_time'])
                booking['end_time'] = format_time(booking['end_time'])
            
            # Format payment method to either in-store or online (don't specify the service used for online payment since not required)
            if booking['payment_method'] == 'in_store':
                booking['payment_method'] = 'In-store'
            else:
                booking['payment_method'] = 'Online'
                
            # Format stars for ratings
            rating_value = booking['rating']
            if rating_value > 0: # If user left a rating we create the number of dark stars and fill the rest of the space with empty stars
                booking['rating'] = '★' * rating_value 
                booking['rating'] = booking['rating'] + '☆' * (5 - rating_value)
            else: # If user left no rating we store a string to indicate that
                booking['rating'] = 'No rating'

    except Exception as e:
        # If we get an error we display error and return a empty bookings list
        flash(f'Error fetching bookings: {str(e)}', 'error')
        bookings = []
    
    finally:
        cursor.close()
        conn.close()

    # We render the page with each of the filters and the bookings dictionary (With contains the query result and necessary data to display for the admin)
    return render_template('manage_bookings.html', 
                           status_filter = status_filter,
                           date_filter = date_filter,
                           service_filter = service_filter,
                           rating_filter = rating_filter,
                           name_filter = name_filter,
                           bookings = bookings)

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

@admin.route('/modify_bookings/<int:booking_id>', methods=['GET', 'POST'])
def modify_bookings(booking_id):
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Fetch the booking details from database using booking_id
        cursor.execute("""
            SELECT b.booking_id, b.customer_id, u.email, b.type_id, pt.transaction_id, ts.slot_id, ts.slot_date, ts.start_time, ts.end_time,
                   u.name as customer_name, bt.type_name as service_type, bt.price,
                   pt.payment_method, b.appointment_status, pt.amount,
                   pt.stripe_transaction_id as stripe_id
            FROM bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            JOIN users u ON b.customer_id = u.user_id
            JOIN booking_types bt ON b.type_id = bt.type_id
            JOIN payment_transactions pt ON b.transaction_id = pt.transaction_id
            WHERE b.booking_id = %s
        """, (booking_id,))
        
        booking = cursor.fetchone()
        
        if not booking:
            flash('Booking not found', 'error')
            return redirect(url_for('admin.manage_bookings'))

        # Format the start time, end time, and date
        booking['formatted_start_time'] = format_time(booking['start_time'])
        booking['formatted_end_time'] = format_time(booking['end_time'])
        booking['formatted_date'] = booking['slot_date'].strftime('%Y-%m-%d')

        if booking['payment_method'] == 'in_store':
            booking['payment_method'] = 'In-store'
        else:
            booking['payment_method'] = 'Online'

        # Get all the timeslots for the current day
        cursor.execute("""
            SELECT slot_id, start_time, end_time, slot_date, current_bookings, max_bookings
            FROM time_slots
            WHERE slot_date = %s
            AND current_bookings < max_bookings
        """, (booking['slot_date'],))

        available_timeslots = cursor.fetchall()

        cursor.execute("""
            SELECT slot_id, start_time, end_time, slot_date, current_bookings, max_bookings
            FROM time_slots
            WHERE slot_date = %s
            AND slot_id = %s
        """, (booking['slot_date'], booking['slot_id']))

        current_timeslot = cursor.fetchone()
        current_timeslot['formatted_start_time'] = format_time(current_timeslot['start_time'])
        current_timeslot['formatted_end_time'] = format_time(current_timeslot['end_time'])
        current_timeslot['availability'] = current_timeslot['max_bookings'] - current_timeslot['current_bookings']

        if current_timeslot['availability'] == 0:
            current_timeslot['availability'] = "Full"
    
        # Format the start time and end time for each timeslot
        for slot in available_timeslots:
            slot['formatted_start_time'] = format_time(slot['start_time'])
            slot['formatted_end_time'] = format_time(slot['end_time'])
            slot['availability'] = slot['max_bookings'] - slot['current_bookings']
            
        # Get service types for dropdown
        cursor.execute("SELECT type_id, type_name, price FROM booking_types")
        service_types = cursor.fetchall()

        # If it is a POST request we need to update the values
        if request.method == 'POST':
            # Get form data (the new timeslot, new service type, new payment method, new stripe id)
            new_timeslot_id = request.form.get('timeslot')
            new_service_type = request.form.get('service_type')
            new_payment_method = request.form.get('payment_method')
            new_stripe_id = request.form.get('stripe_id', None)
            
            # Check if there was a change in the timeslot id 
            if int(new_timeslot_id) != booking['slot_id']:
                # If there is a change in the timeslot id then a new timeslot was chosen so we decrement current bookings in the old timeslot
                cursor.execute("""
                    UPDATE time_slots
                    SET current_bookings = current_bookings - 1
                    WHERE slot_id = %s
                """, (booking['slot_id'],))
                
                # And increment the current bookings in the new timeslot
                cursor.execute("""
                    UPDATE time_slots
                    SET current_bookings = current_bookings + 1
                    WHERE slot_id = %s
                """, (new_timeslot_id,))
            
            # The form returns the actual name of the service, we need the id and the price of the service
            cursor.execute("""
                SELECT type_id, price FROM booking_types
                WHERE type_name = %s
            """, (new_service_type,))
            
            service_type_result = cursor.fetchone()
            
            new_service_type_id = service_type_result['type_id']
            new_price = service_type_result['price']
            
            # Check if we're changing the service type
            if new_service_type_id != booking['type_id']:
                # Update the payment_transactions table with the price of the new service
                cursor.execute("""
                    UPDATE payment_transactions
                    SET amount = %s
                    WHERE transaction_id = %s
                """, (new_price, booking['transaction_id']))
            
            # Check if payment method has changed or if the stripe id has changed
            payment_update_needed = (new_payment_method != booking['payment_method'])
            stripe_update_needed = (new_stripe_id != booking['stripe_id'] and new_stripe_id is not None)
            
            if payment_update_needed or stripe_update_needed:
                cursor.execute("""
                    UPDATE payment_transactions
                    SET payment_method = %s, stripe_transaction_id = %s
                    WHERE transaction_id = %s
                """, (new_payment_method, new_stripe_id, booking['transaction_id']))
            
            # Finally, update the booking record with the new timeslot id and new service type id
            cursor.execute("""
                UPDATE bookings
                SET slot_id = %s, type_id = %s
                WHERE booking_id = %s
            """, (new_timeslot_id, new_service_type_id, booking_id))
            
            # Commit all changes
            conn.commit()

            email_date = booking['slot_date'].strftime('%A, %B %d')

            msg = Message(
                subject="Booking Modification",
                recipients=[booking['email']]
            )
            msg.body = (f"Hello your booking originally on {email_date} from {current_timeslot['formatted_start_time']} - {current_timeslot['formatted_end_time']} has been modified.\n"
                    f"Log into your account to view the modifications.\n\n"
                    f"Thank You")

            try:
                mail.send(msg)
                print(f"Email Sent")
            except Exception as e:
                print(f"Failed to send email: {e}")


            # If everything was succcesful then the update was valid and we alert that to the user
            flash('Booking updated successfully', 'success')
            return redirect(url_for('admin.manage_bookings'))

    except Exception as e:
        # Rollback transaction in case of error (this makes sure that if the database crashes midway through the process then
        # data integrity is still kept)
        conn.rollback()

        # In case of error, we alert the user and take them back to the manage_bookings page
        flash(f'Error processing booking: {str(e)}', 'error')
        return redirect(url_for('admin.manage_bookings'))
        
    finally:
        cursor.close()
        conn.close()

    # In case of GET request we always render the template with the booking information and timeslot information
    return render_template('modify_bookings.html', 
                           booking_id=booking_id,
                           booking=booking,
                           available_timeslots=available_timeslots,
                           current_timeslot=current_timeslot,
                           service_types=service_types)
@admin.route('/get_available_timeslots/<date>', methods=['GET'])
def get_available_timeslots(date):
    try:
        # Convert string date to datetime object
        date_obj = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        
        # Connect to database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get available timeslots for the selected date
        cursor.execute("""
            SELECT slot_id, start_time, end_time, current_bookings, max_bookings
            FROM time_slots
            WHERE slot_date = %s
            ORDER BY start_time
        """, (date_obj,))
        
        timeslots = cursor.fetchall()
        
        # Format the start time and end time for display and calculate the availability
        for slot in timeslots:
            slot['formatted_start_time'] = format_time(slot['start_time'])
            slot['formatted_end_time'] = format_time(slot['end_time'])
            slot['availability'] = slot['max_bookings'] - slot['current_bookings']
        
        # Store all available timeslots for the formatted date
        available_timeslots = [slot for slot in timeslots if slot['availability'] > 0]
        
        # Render just the options HTML for the timeslot dropdown
        return render_template('timeslot_options.html', timeslots=available_timeslots)
    
    except Exception as e:
        return f"<option disabled selected>Error: {str(e)}</option>"  
    finally:
        cursor.close()
        conn.close()

@admin.route('/delete_booking/<int:booking_id>', methods=['POST'])
def delete_booking(booking_id):
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:

        # Get the slot record and transaction record that will be deleted alongside the booking record
        cursor.execute("""
            SELECT b.slot_id, b.transaction_id 
            FROM bookings b
            WHERE b.booking_id = %s
        """, (booking_id,))
        
        booking = cursor.fetchone()
        
        # Used to connect appointment to customer and done at this part before being updated
        cursor.execute("""
        SELECT b.booking_id, b.customer_id, b.type_id, pt.transaction_id, ts.slot_id, ts.slot_date, ts.start_time, ts.end_time,
                u.name as customer_name, u.email, bt.type_name as service_type, bt.price,
                pt.payment_method, b.appointment_status, pt.amount,
                pt.stripe_transaction_id as stripe_id
        FROM bookings b
        JOIN time_slots ts ON b.slot_id = ts.slot_id
        JOIN users u ON b.customer_id = u.user_id
        JOIN booking_types bt ON b.type_id = bt.type_id
        JOIN payment_transactions pt ON b.transaction_id = pt.transaction_id
        WHERE b.booking_id = %s
        """, (booking_id,))
        result = cursor.fetchone()
        if result:
            # Is used to locate specific customer to email and provide the day and time
            customer_email = result['email']
            customer_name = result['customer_name']
            customer_day = result['slot_date'].strftime('%A, %B %d')
            customer_time_start = format_time(result['start_time'])
            customer_time_end = format_time(result['end_time'])
        else:
            flash("Unable to find name or email of customer")

        # Decrement the current_bookings count in the time_slots table corresponding to the booking
        cursor.execute("""
            UPDATE time_slots
            SET current_bookings = current_bookings - 1
            WHERE slot_id = %s
        """, (booking['slot_id'],))

        # Delete any review if it exists for this booking, this is required so it doesn't yield a foreign key error
        cursor.execute("DELETE FROM reviews WHERE booking_id = %s", (booking_id,))

        # Delete the booking record before the payment record since it has foreign key constraint
        cursor.execute("DELETE FROM bookings WHERE booking_id = %s", (booking_id,))
        
        # Delete the payment record that corresponds to the booking
        cursor.execute("DELETE FROM payment_transactions WHERE transaction_id = %s", (booking['transaction_id'],))
        
        # Commit changes
        conn.commit()
        
        # If it was a success, indicate to user
        flash('Booking deleted successfully', 'success')
        subject = 'Booking removed'
        body = (f"Hi {customer_name},\n\n Your booking on {customer_day}, from {customer_time_start} - {customer_time_end} has been removed.")
        send_email(customer_email, subject, body)
        
    except Exception as e:
        # If there is any error, rollback and display error
        conn.rollback()
        flash(f'Error deleting booking: {str(e)}', 'error')
        
    finally:
        cursor.close()
        conn.close()
    
    # Re-render the manage_bookings page
    return redirect(url_for('admin.manage_bookings'))

# Method to send email
def send_email(to, subject, body):
    msg = Message(subject=subject,
                  recipients=[to],  # Recipient emails
                  body=body)  # The content of the email
    try:
        mail.send(msg)  # Sends email
    except Exception as e:
        flash(f'Unable to send email: {str(e)}', 'error')

@admin.route('/manage_timeslots/<selected_date>', methods=['GET'])
def manage_timeslots(selected_date):
    # Convert string date to date object (make it date object for query)
    slot_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()
    
    # Format date for display in page
    display_date = slot_date.strftime('%A, %B %d')
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get all timeslots for the selected date
        cursor.execute("""
            SELECT slot_id, start_time, end_time, max_bookings, current_bookings
            FROM time_slots
            WHERE slot_date = %s
            ORDER BY start_time
        """, (slot_date,))
        
        timeslots = cursor.fetchall()
        
        for slot in timeslots:
            # Format times for display into 12hr format
            slot['formatted_start_time'] = format_time(slot['start_time'])
            slot['formatted_end_time'] = format_time(slot['end_time'])
            
            # Calculate availability for each slot
            slot['availability'] = slot['max_bookings'] - slot['current_bookings']
            
            # Segment the time and period for the formatted times so we can display them
            start_components = slot['formatted_start_time'].split(' ')
            end_components = slot['formatted_end_time'].split(' ')
            
            slot['start_time_display'] = start_components[0]
            slot['start_period'] = start_components[1]
            
            slot['end_time_display'] = end_components[0]
            slot['end_period'] = end_components[1]
            
    except Exception as e:
        # When error occurs, return empty timeslots list and indicate error to user
        flash(f'Error fetching timeslots: {str(e)}', 'error')
        timeslots = []
    
    finally:
        cursor.close()
        conn.close()
    
    # Render page with the selected date, display date, and the list of all the timeslots for the selected date
    return render_template('manage_timeslots.html',
                          selected_date=selected_date,
                          display_date=display_date,
                          timeslots=timeslots)

@admin.route('/delete_timeslot/<int:slot_id>/<selected_date>', methods=['POST'])
def delete_timeslot(slot_id, selected_date):

    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if the timeslot has any bookings (we don't want to delete timeslots with bookings)
        cursor.execute("SELECT current_bookings FROM time_slots WHERE slot_id = %s", (slot_id,))
        result = cursor.fetchone()
        
        # If there are currently bookings for the selected timeslot, then we indicate to admin that this timeslot
        # Cant be deleted
        if result and result['current_bookings'] > 0:
            flash('Cannot delete a timeslot that has bookings', 'error')
        else:
            # Otherwise if there are no bookings for this timeslot, we just delete the timeslot, commit the change, and indicate the admin it was successful
            cursor.execute("DELETE FROM time_slots WHERE slot_id = %s", (slot_id,))
            conn.commit()
            flash('Timeslot deleted successfully', 'success')
    
    except Exception as e:
        # In cash of error when deleting timeslot, flash error
        flash(f'Error deleting timeslot: {str(e)}', 'error')
    
    finally:
        cursor.close()
        conn.close()
    
    # Return the selected_date back to the page so it can be rendered and utilized in the other routes
    return redirect(url_for('admin.manage_timeslots', selected_date=selected_date))

@admin.route('/generate_default_timeslots/<selected_date>', methods=['POST'])
def generate_default_timeslots(selected_date):

    # Convert string date to date object (make it date object for query)
    slot_date = datetime.datetime.strptime(selected_date, '%Y-%m-%d').date()
    
    # use the .weekday() method for date object to determine if its a weekend or weekday
    # This method returns a 5-6 for weekends and 0-4 for weekdays
    weekday = slot_date.weekday()  
    
    if weekday < 5:  # Weekday
        # Set start hour to 9am and end hour to 5pm
        start_hour = 9  # 9AM
        end_hour = 17   # 5PM
    else:  # Weekend
        # Set start hour to 10am and end hour to 4pm
        start_hour = 10  # 10AM
        end_hour = 16   # 4PM

    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        
        # Create a datetime object by combining the slot_date and the start/end hour so we can increment the 
        # Minutes during each iteration of the while loop
        current_time = datetime.datetime.combine(slot_date, datetime.time(start_hour, 0))
        end_time = datetime.datetime.combine(slot_date, datetime.time(end_hour, 0))
        
        # Keep track of slots added and skipped (We will skip slots that already exist)
        slots_added = 0
        slots_skipped = 0
        
        # Generate 30-minute slots until end_time
        while current_time < end_time:
            # Format time to conform to database TIME format
            start_time_str = current_time.strftime("%H:%M:%S")
            
            # Calculate end time (30 minutes later)
            slot_end_time = current_time + datetime.timedelta(minutes=30)
            # Format time to conform to database TIME format
            end_time_str = slot_end_time.strftime("%H:%M:%S")
            
            # Check if this timeslot already exists
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM time_slots 
                WHERE slot_date = %s AND start_time = %s
            """, (slot_date, start_time_str))
            
            result = cursor.fetchone()
            
            # If the timeslot doesn't already exist in databse, we create it and increment slot_addded
            if result['count'] == 0:
                cursor.execute("""
                    INSERT INTO time_slots (slot_date, start_time, end_time, max_bookings, current_bookings)
                    VALUES (%s, %s, %s, %s, 0)
                """, (slot_date, start_time_str, end_time_str, 2))
                slots_added += 1
            else:
                # Otherwise, if it exists, we skip adding it and increment slots_skipped
                slots_skipped += 1
            
            # We move to the next 30-minute slot and repeat the process of checking if it needs to be added or not
            current_time = slot_end_time
        
        # We commit the change (if slot was added)
        conn.commit()
        
        # If a slot was added, we indicate this information to the user and display how many slots where added and how
        # many slots where skipped for the selected_date
        if slots_added > 0:
            flash(f'Successfully generated {slots_added} timeslots. Skipped {slots_skipped} existing timeslots.', 'success')
        else:
            # Otherwise, if no slot was added, we tell the admin of how many slots were skipped
            flash(f'No new timeslots added. {slots_skipped} timeslots already exist.', 'info')
    
    except Exception as e:
        # In case of error, we flash error msg to user
        flash(f'Error generating timeslots: {str(e)}', 'error')
    
    finally:
        cursor.close()
        conn.close()
    
    # We render the page again with the selected_date
    return redirect(url_for('admin.manage_timeslots', selected_date=selected_date))

@admin.route('/analytics_dashboard', methods=['GET'])
def analytics_dashboard():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

     
        # Query for cancellation amount
    cursor.execute("""
        SELECT COUNT(booking_id)
        FROM bookings
        """)
    total_booking = cursor.fetchall()

        # Query for cancellation amount
    cursor.execute("""
        SELECT COUNT(appointment_status)
        FROM bookings
        WHERE appointment_status = "cancel"
        """)
    total_cancel = cursor.fetchall()

    
    for row in total_cancel:
        total_cancel_amount = total_cancel[0]["COUNT(appointment_status)"]
    for row in total_booking:
        total_amount = total_booking[0]["COUNT(booking_id)"]

    if total_amount != 0:
        appointment_cancellation_rate = round((total_cancel_amount / total_amount) * 100, 2)
    else:
        appointment_cancellation_rate = 0

    # Query for most popular days
    cursor.execute("""
        SELECT slot_date, COUNT(*) AS popular_date
        FROM time_slots
        WHERE current_bookings > 0
        GROUP BY slot_date
        ORDER BY popular_date DESC, slot_date DESC
        LIMIT 1
    """)
    unformated_popular_day_date = cursor.fetchall()
    # Check if there's a result for popular day
    if unformated_popular_day_date:
        popular_day_date = unformated_popular_day_date[0]["slot_date"]
        popular_day = popular_day_date.strftime("%A")
    else:
        popular_day = "N/A"

    # Query for least popular days
    cursor.execute("""
        SELECT slot_date, COUNT(*) AS less_popular_date
        FROM time_slots
        WHERE current_bookings > 0
        GROUP BY slot_date
        ORDER BY less_popular_date ASC, slot_date ASC
        LIMIT 1
    """)
    less_popular_day_date = cursor.fetchall()
    # Check if there's a result for less popular day
    if less_popular_day_date:
        unpopular_day_date = less_popular_day_date[0]["slot_date"]
        unpopular_day = unpopular_day_date.strftime("%A")
    else:
        unpopular_day = "N/A"

    # Query for most popular time slot
    cursor.execute("""
        SELECT start_time, end_time, COUNT(*) as popular_timing
        FROM time_slots
        WHERE current_bookings > 0
        GROUP BY start_time, end_time
        ORDER BY popular_timing DESC
        LIMIT 1
    """)
    unformated_popular_time_slot = cursor.fetchall()
    # Converts database format of time into hours/minutes/AM or PM
    #(1900,1,1) was used as a base so that the value works as a datetime object. As long as the values aren't 0 then any other examples work
    if unformated_popular_time_slot:
        popular_start_time_index = unformated_popular_time_slot[0]['start_time']
        popular_end_time_index = unformated_popular_time_slot[0]['end_time']
        popular_start_time_datetimeformat = datetime.datetime(1900, 1, 1) + popular_start_time_index
        format_popular_start_time_slot = popular_start_time_datetimeformat.strftime("%I:%M %p")
        popular_end_time_datetimeformat = datetime.datetime(1900, 1, 1) + popular_end_time_index
        format_popular_end_time_slot = popular_end_time_datetimeformat.strftime("%I:%M %p")
    else:
        format_popular_start_time_slot = "N/A"
        format_popular_end_time_slot = "N/A"

    # Query for less popular time slot
    cursor.execute("""
        SELECT start_time, end_time, COUNT(*) as less_popular_timing
        FROM time_slots
        WHERE current_bookings > 0
        GROUP BY start_time, end_time
        ORDER BY less_popular_timing ASC
        LIMIT 1
    """)
    unformated_less_popular_time_slot = cursor.fetchall()
    # Converts database format of time into hours/minutes/AM or PM
    if unformated_less_popular_time_slot:
        unpopular_start_time_index = unformated_less_popular_time_slot[0]['start_time']
        unpopular_end_time_index = unformated_less_popular_time_slot[0]['end_time']
        unpopular_start_time_datetimeformat = datetime.datetime(1900, 1, 1) + unpopular_start_time_index
        format_less_popular_start_time_slot = unpopular_start_time_datetimeformat.strftime("%I:%M %p")
        unpopular_end_time_datetimeformat = datetime.datetime(1900, 1, 1) + unpopular_end_time_index
        format_less_popular_end_time_slot = unpopular_end_time_datetimeformat.strftime("%I:%M %p")
    else:
        format_less_popular_start_time_slot = "N/A"
        format_less_popular_end_time_slot = "N/A"

    # Average satisfaction score
    cursor.execute("SELECT AVG(rating) AS avg_rating FROM reviews WHERE rating IS NOT NULL")
    result = cursor.fetchone()
    avg_rating = round(result['avg_rating'], 2) if result['avg_rating'] else "No ratings yet"

    # Revenue from Head Check
    cursor.execute("""
        SELECT SUM(pt.amount) AS total_revenue
        FROM bookings b
        JOIN booking_types bt ON b.type_id = bt.type_id
        JOIN payment_transactions pt ON b.transaction_id = pt.transaction_id
        WHERE bt.type_name = 'lice check'
    """)
    head_check_revenue = cursor.fetchone()['total_revenue'] or 0

    # Revenue from Lice Removal
    cursor.execute("""
        SELECT SUM(pt.amount) AS total_revenue
        FROM bookings b
        JOIN booking_types bt ON b.type_id = bt.type_id
        JOIN payment_transactions pt ON b.transaction_id = pt.transaction_id
        WHERE bt.type_name = 'lice removal'
    """)
    lice_removal_revenue = cursor.fetchone()['total_revenue'] or 0


    cursor.close()
    conn.close()
   
   # Formated this part per line because it was hard to read
    return render_template('analytics_dashboard.html', 
                           appointment_cancellation_rate=appointment_cancellation_rate, 
                           popular_day=popular_day, 
                           unpopular_day=unpopular_day, 
                           format_popular_end_time_slot=format_popular_end_time_slot, 
                           format_popular_start_time_slot=format_popular_start_time_slot, 
                           format_less_popular_start_time_slot=format_less_popular_start_time_slot,
                           format_less_popular_end_time_slot=format_less_popular_end_time_slot,
                           total_amount=total_amount,
                           lice_removal_revenue=lice_removal_revenue,
                            head_check_revenue=head_check_revenue,
                            avg_rating=avg_rating
                           )

# Inbox can be redirect to messages and the email will automatically be selected to email drop down to be responded to
# Sends message that has a subject and body to email
@admin.route('/admin_message', methods=['GET', 'POST'])
def message():
    try:
        # This is for the email admin is responding to an email from inbox
        selected_email = request.args.get('selected_email')
        title = request.form.get('subject')
        message = request.form.get('body')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Gets all possible emails admin can message to (excluding self)
        cursor.execute("""
            SELECT email
            FROM users
            WHERE users.permission = 'admin' OR users.permission = 'employee'
        """)
        emails = cursor.fetchall()

        # Get user session information to do the following:
        # Remove email user used to login in from potential emails to send
        # Obtain user session id to fill into table
        current_user_id = session.get('user_id')
        current_user_email = session.get('email')
        emailslist = [row['email'] for row in emails if row['email'] != current_user_email]

        # For sending message and then storing the message
        if request.method == 'POST':
            if not title or not message or not selected_email:
                flash('Please fill in all fields!')
                return redirect(url_for('admin_message.html'))
            else:
                notification_id_count = notification_id_count + 1
                cursor.execute("""
                INSERT INTO shift_change_requests 
                (notification_id, user, title, message) 
                VALUES (%s, %s, %s, %s)
                """, 
                (notification_id_count, current_user_id, title, message)
                )
                flash('Message submitted successfully', 'success')

    except Exception as e:
        # In case of error
        flash(f'Error sending message: {str(e)}', 'error')
    
    finally:
        cursor.close()
        conn.close()
    return render_template('admin_message.html', emailslist = emailslist, selected_email=selected_email)