-- Starting up database
CREATE DATABASE easybook;
USE easybook;

-- Making admin account
INSERT INTO users (name, email, password, permission) 
VALUES ('admin', 'admin@gmail.com', 'admin', 'admin');

-- Users table: Record of all users
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    permission ENUM('customer', 'employee', 'admin') NOT NULL
);

-- Block days table: Record of closed days
CREATE TABLE block_days (
    day_id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    set_by INT NOT NULL,
    FOREIGN KEY (set_by) REFERENCES users(user_id)
);

-- Shifts table: Record of employee shifts
CREATE TABLE shifts (
    shift_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    shift_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES users(user_id)
);

-- Shift change requests table: Employee requests for shift change
CREATE TABLE shift_change_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    shift_id INT NOT NULL,
    request_type ENUM('swap', 'cancel', 'change_hours', 'other') NOT NULL,
    reason TEXT NOT NULL,
    read_status BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (employee_id) REFERENCES users(user_id),
    FOREIGN KEY (shift_id) REFERENCES shifts(shift_id)
);

-- Booking types table: Types of services offered
CREATE TABLE booking_types (
    type_id INT AUTO_INCREMENT PRIMARY KEY,
    type_name VARCHAR(100) NOT NULL,
    price DECIMAL(10, 2) NOT NULL
);

-- Payment transactions table: Records of payments
CREATE TABLE payment_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    payment_method ENUM('in_store', 'stripe') NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    stripe_transaction_id VARCHAR(255)
);

-- Time slots table: record of all time slots
CREATE TABLE time_slots (
    slot_id INT AUTO_INCREMENT PRIMARY KEY,
    slot_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    max_bookings INT NOT NULL DEFAULT 2,
    current_bookings INT NOT NULL DEFAULT 0,
    UNIQUE KEY unique_time_slot (slot_date, start_time)
);

-- Bookings table: Customer bookings
CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    type_id INT NOT NULL,
    transaction_id INT NOT NULL UNIQUE,
    slot_id INT NOT NULL,
    appointment_status ENUM('current', 'past', 'cancel') NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES users(user_id),
    FOREIGN KEY (type_id) REFERENCES booking_types(type_id),
    FOREIGN KEY (transaction_id) REFERENCES payment_transactions(transaction_id),
    FOREIGN KEY (slot_id) REFERENCES time_slots(slot_id)
);

-- Reviews table: Record of customer feedback
CREATE TABLE reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    customer_id INT NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    FOREIGN KEY (customer_id) REFERENCES users(user_id)
);

-- Notifications table: Record of system notifications
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    notification_type ENUM('reminder', 'appointment_canceled') NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

