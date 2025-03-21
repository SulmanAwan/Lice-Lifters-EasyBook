from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db_connection
import calendar
import datetime

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
                date_str = datetime.date(year, month, day).strftime('%Y-%m-%d')
                
                # We check to see if the current iteration of the date is in the block_dates list
                if date_str in blocked_dates:
                    # If it is then we assign the class to be 'blocked-day' (used for styling)
                    # day_class will be assigned to the class attribute of the day object
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
            SELECT s.start_time, s.end_time, u.name as employee_name
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

@admin.route('/booking_notifications', methods=['GET', 'POST'])
def booking_notifications():
    # TODO: implement booking notifications
    return render_template('admin/booking_notifications.html')

@admin.route('/appointment_history', methods=['GET', 'POST'])
def appointment_history():
    # TODO: implement appointment history
    return render_template('admin/appointment_history.html')

@admin.route('/analytics_dashboard', methods=['GET'])
def analytics_dashboard():
    # TODO: implement dashboard
    return render_template('admin/analytics_dashboard.html')

@admin.route('/manage_shift', methods=['GET', 'POST'])
def manage_shift():
    # TODO: implement manage shift
    return render_template('admin_homepage.html')

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

    try:
        # Get all columns of data required to show the change requests
        cursor.execute("""
            SELECT r.request_id, u.name, r.request_type, s.shift_date, s.start_time, s.end_time, r.reason, r.read_status
            FROM shift_change_requests r 
            JOIN shifts s ON r.shift_id = s.shift_id
            JOIN users u ON r.employee_id = u.user_id
            WHERE r.read_status = FALSE
            ORDER BY s.shift_date ASC, s.start_time ASC
        """)
       
        requests = cursor.fetchall()

        # For each request we need to format the shift time and shift date so we can display it in a better way on the page
        for request in requests:
            request['start_time'] = format_time(request['start_time'])
            request['end_time'] = format_time(request['end_time'])
            request['shift_date'] = request['shift_date'].strftime('%B %d, %Y')

    except Exception as e:
        # Alert user of any error and render the page without requests in the case of error
        flash(f'Error fetching inbox messages: {str(e)}', 'error')
        requests = []
    finally:
        # close cursor and database connection
        cursor.close()
        conn.close()

    # Render the inbox page with the requests
    return render_template('inbox.html', requests=requests)

@admin.route('/mark_as_read/<int:request_id>', methods=['POST'])
def mark_as_read(request_id):
    # Going to flip value of read_status to true if user clicks "market as read"
    # Going to alert user if it is a succcess or if any error occur

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Update the read_status in the shift_change_requests table for the request_id passed into the route
        cursor.execute("UPDATE shift_change_requests SET read_status = TRUE WHERE request_id = %s", 
                      (request_id,))
        
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
