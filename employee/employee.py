from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from db import get_db_connection
import calendar
import datetime

employee = Blueprint('employee', __name__, template_folder='templates', static_folder='static')

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


@employee.route('/homepage', methods=['GET', 'POST'])
def employee_homepage():
    # Render homepage for employee, including the calendar, buttons, bookings, shifts, etc...

    # Get name and id from session to use in display and query
    name = session.get('name')
    user_id = session.get('user_id')
    
    # Using .today(), get current date infomation and the object in the today variable so we can access individual components of the current day
    today = datetime.date.today()

    # Retrieve the selected_date argument from the form request if it exists
    selected_date_str = request.args.get('selected_date')
    if selected_date_str:
        # If selected_date exists use the provided date from the request
        selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    else:
        # No date provided so we find the next shift day
        next_shift_date = get_next_shift_date(user_id, today)
        if next_shift_date:
            selected_date = next_shift_date
        else:
            # If no upcoming shifts, default to today
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
    calendar_weeks = generate_calendar(user_id, current_year, current_month, selected_date)
    
    # Get shifts and bookings for the selected_date (Used for displaying shift and bookings for selected_date)
    shift = get_shift_for_date(selected_date, user_id)
    if shift:
        # If there is a shift for that day, show bookings
        bookings = get_bookings_for_date(selected_date, shift['military_start_time'], shift['military_end_time'])
    else:
        # Otherwise return empty list
        bookings = []
    
    # Finaally we pass in all the data required to render the homepage components (calendar, shifts, bookings, etc)
    return render_template('employee_homepage.html', 
                          name=name, # Displayed on the top right of the page
                          calendar_weeks=calendar_weeks, # Calendar object which contains all the days information stored as dictonaries.
                          selected_date=selected_date.strftime('%Y-%m-%d'), # The selected date in the format YYYY-MM-DD (ie date object)
                          display_date=display_date, # The selected date in the format (ie: Monday, January 01) shown on the right side of the page
                          current_month=current_month, # The current month number (1-12)
                          current_year=current_year, # The current year (YYYY)
                          current_month_name=current_month_name, # The current month name (ie: January)
                          shift=shift, # The shift data for the selected_date (shown on the right)
                          bookings=bookings) # List of dictionaries containing bookings for the selected_date (shown on the right)

def generate_calendar(user_id, year, month, selected_date):
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

    # Get blocked dates for this month (will use this to determine the css class styling later on)
    blocked_dates = get_blocked_dates(year, month)
    
    # Get the day of the week for the first day (0 = Monday, 6 = Sunday) For instance, March 1, 2025 is a Saturday so it will return 5
    first_weekday = first_day.weekday()
    
    # Our calendar headings for the weekday will be 0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday
    # So we need to adjust the first_weekday to match this format
    # Adjust for Sunday as the first day of the week (0 = Sunday, 6 = Saturday)
    first_weekday = (first_weekday + 1) % 7
    
    # Get shift dates for this month (will use this to determine the css class styling later on)
    shifts = get_shifts(user_id, year, month)
    
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
                
                # Determine class based on date and shifts
                if date_str in shifts and date_str not in blocked_dates:
                    # Check if its a past day if it is mark as completed
                    if current_date < today:
                        day_class = 'completed-day'

                    # Check if its current day and that the end time < current time if it is then mark as completed
                    # Otherwise mark it as a workday
                    elif current_date == today:
                        shift_completed = is_shift_completed(user_id, today)
                        if shift_completed:
                            day_class = 'completed-day'
                        else:
                            day_class = 'work-day'
                    # If its a future shift then mark as workday
                    else:
                        
                        day_class = 'work-day'
                # If its a blocked date mark as blocked date
                elif date_str in blocked_dates:
                    day_class = 'blocked-date'
                # Otherwise its just an off day
                else:
                    day_class = 'off-day'
                
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

def is_shift_completed(user_id, date):
    """
    Check if the shift for a given employee on a given date is completed (end time has passed)
    Returns True if completed, False otherwise
    """
    # Need to check for a given employee and given date if the shift is completed on the date 
    # (ie endtime of shift < current time)

    # Get current time
    now = datetime.datetime.now().time()
    
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get the shift for the current day for this employee and get the end_time
        cursor.execute("""
            SELECT end_time 
            FROM shifts 
            WHERE employee_id = %s AND shift_date = %s
        """, (user_id, date))
        
        result = cursor.fetchone()
        
        if result:
            # We need to convert the end_time from deltatime (given from database)
            # into a datetime.time object so we can compare it
            end_time_seconds = result['end_time'].total_seconds()
            end_hours = int(end_time_seconds // 3600)
            end_minutes = int((end_time_seconds % 3600) // 60)
            end_seconds = int(end_time_seconds % 60)
            
            shift_end_time = datetime.time(hour=end_hours, minute=end_minutes, second=end_seconds)
            
            # Return True if current time is past the end time
            return now > shift_end_time

        # Otherwise we return false to indicate the shift is not completed yet
        return False
    
    except Exception as e:
        print(f"Error checking if shift is completed: {str(e)}")
        return False
    
    finally:
        cursor.close()
        conn.close()

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

def get_next_shift_date(user_id, from_date):
    # Finds next upcoming shift date for an employee starting from from_date
    # Returns a date object or None if no upcoming shifts
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    next_shift = None
    
    try:
        # Query shifts table for the next shift date
        cursor.execute(
            """
            SELECT shift_date
            FROM shifts
            WHERE employee_id = %s
            AND shift_date >= %s
            ORDER BY shift_date ASC
            LIMIT 1
            """, 
            (user_id, from_date.strftime('%Y-%m-%d'))
        )
        
        result = cursor.fetchone()

        # If we get a result, we assign next_shift to the next shift date
        if result:
            next_shift = result['shift_date']
    
    except Exception as e:
        flash(f'Error finding next shift: {str(e)}', 'error')
    
    finally:
        cursor.close()
        conn.close()
    
    # Return the next shift date as a datetime.date object
    # If no next shift is found, return None
    return next_shift

def get_shifts(user_id, year, month):
    # Query the database for all shifts for a specific employee in the given month and year.
    # Return a list of shift dates (as strings in 'YYYY-MM-DD' format)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Create date boundaries for the query
    # First day of the month
    start_date = datetime.date(year, month, 1).strftime('%Y-%m-%d')
    
    # First day of the next month
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1).strftime('%Y-%m-%d')
    else:
        end_date = datetime.date(year, month + 1, 1).strftime('%Y-%m-%d')
    
    shift_dates = []
    
    try:
        # Query all shifts for this employee in the specified month
        cursor.execute(
            """
            SELECT DISTINCT shift_date, end_time
            FROM shifts 
            WHERE employee_id = %s 
            AND shift_date >= %s 
            AND shift_date < %s
            """, 
            (user_id, start_date, end_date)
        )
        
        # Convert all dates to string format for easy comparison in generate_calendar
        shift_dates = [row['shift_date'].strftime('%Y-%m-%d') for row in cursor.fetchall()]
        
    except Exception as e:
        flash(f'Error fetching shifts: {str(e)}', 'error')
    
    finally:
        cursor.close()
        conn.close()
    
    # Return the list of all the employee's shift dates in the specified month
    # The dates are in the format YYYY-MM-DD
    return shift_dates

def get_shift_for_date(date, user_id):
    # Get the shift data for the employee on a specific day

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try: 
        # Query database to check if the shift for that date exists
        cursor.execute(
            """
            SELECT shift_id, start_time, end_time
            FROM shifts
            WHERE shift_date = %s
            AND employee_id = %s
            ORDER BY start_time
            """, 
            (date, user_id,)
        )
        
        shift = cursor.fetchone()
        
        if shift:
            # If the shift exists, we store the start and end times for that shift so we can
            # Use it in the query to check for the bookings during those start and end times for that day
            shift['military_start_time'] = shift['start_time']
            shift['military_end_time'] = shift['end_time']

            # Also, we need to convert the start_time and end_time to a 12-hour format so we can 
            # display it on the calender.
            shift['formatted_start_time'] = format_time(shift['start_time'])
            shift['formatted_end_time'] = format_time(shift['end_time'])
        else:
            # If no shift is found for that day, we return a empty list
            shift = []

    except Exception as e:
        flash(f'Error fetching shifts: {str(e)}', 'error')
        # In the case of an error, we return am empty list as well
        shift = [] 

    finally:
        cursor.close()
        conn.close()

    # We return the shift object which contains the start_time, end_time, formatted_start_time, and formatted_end_time
    return shift

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

def get_bookings_for_date(date, start_time, end_time):
    # Get all bookings for the selected date and time range

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # We query the database joining the bookings, time_slots, users, booking_types, and payment_transaction tables
        # so that we can get the bookings within the time range and have the data to display for the user.
        cursor.execute(
            """
            SELECT ts.start_time, ts.end_time, 
                u.name as customer_name, bt.type_name as service_type,
                pt.payment_method
            FROM bookings b
            JOIN time_slots ts ON b.slot_id = ts.slot_id
            JOIN users u ON b.customer_id = u.user_id
            JOIN booking_types bt ON b.type_id = bt.type_id
            JOIN payment_transactions pt ON b.transaction_id = pt.transaction_id
            WHERE ts.slot_date = %s AND b.appointment_status != 'cancel'
            AND ts.start_time >= %s AND ts.end_time <= %s
            ORDER BY ts.start_time
            """, 
            (date, start_time, end_time)
        )

        bookings = cursor.fetchall()
        
        if bookings:
            # If we have bookings, we need to format the start_time and end_time to a 12-hour format so we can display it
            for booking in bookings:
                booking['start_time'] = format_time(booking['start_time'])
                booking['end_time'] = format_time(booking['end_time'])
                
                # Also we need to format the payment method to a more readable format (client isnt concerned with the form of
                # online payment method)
                if booking['payment_method'] == 'in_store':
                    booking['payment_method'] = 'In-store'
                else:
                    booking['payment_method'] = 'Online'
        else:
            # If there is no booking we return empty list
            bookings = []

    except Exception as e:
        flash(f'Error fetching bookings: {str(e)}', 'error')
        bookings = []

    finally:
        # close cursor n connection
        cursor.close()
        conn.close()
    
    # We return the bookings list which contains all the bookings for the selected date
    # Each booking is a dictionary object containing the start_time, end_time, customer_name, service_type, and payment_method
    return bookings

@employee.route('/shift_change/<display_date>/<current_year>/<shift_id>', methods=['GET', 'POST'])
def shift_change(display_date, current_year, shift_id):
    
    if shift_id == 'none':
            flash("You don't have a shift on this day", 'warning')
            return redirect(url_for('employee.employee_homepage'))

    # For post requests we need to insert the change request into the database so it comes into admin inbox
    if request.method == 'POST':
        # We get form data
        change_type = request.form.get('change_type')
        reason = request.form.get('reason')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # To add a record into the shift_change_requests table we need to get the employee_id, shift_id, request_type, and reason

            # Get employee_id from session
            employee_id = session['user_id']
            
            # Insert the shift change request into the database table
            cursor.execute(
                """
                INSERT INTO shift_change_requests 
                (employee_id, shift_id, request_type, reason) 
                VALUES (%s, %s, %s, %s)
                """, 
                (employee_id, shift_id, change_type, reason)
            )
            
            conn.commit()
            
            # If its successful we alert the user and take them back to the homepage
            flash('Shift change request submitted successfully', 'success')
            return redirect(url_for('employee.employee_homepage'))

        except Exception as e:
            # If error occurs we alert the user and reload the page
            flash('Error occured while submitting your request.', 'error')
            return redirect(url_for('employee.shift_change', display_date=display_date, current_year=current_year, shift_id=shift_id))
        
        finally:
            # Close the cursor and connection
            cursor.close()
            conn.close()

    # In the case of a GET request we render the page with the required data
    return render_template('shift_change.html', display_date=display_date, current_year=current_year, shift_id=shift_id)

@employee.route('/message', methods=['GET', 'POST'])
def message():

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Gets all emails employee can message to
        cursor.execute("""
            SELECT email
            FROM users
            WHERE () = 'admin'
        """)
        admin_emails = cursor.fetchall()

    except Exception as e:
        # In case of error, we flash error msg to user
        flash(f'Error generating timeslots: {str(e)}', 'error')
    
    finally:
        cursor.close()
        conn.close()

    # Updates itself when sending messages (Delete later: Not yet done)
    return render_template('employee_message.html')