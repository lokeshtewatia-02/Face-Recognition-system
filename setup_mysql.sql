-- MySQL Setup Script for Face Recognition Attendance System
-- Run this in MySQL if you need to manually create the database/tables

CREATE DATABASE IF NOT EXISTS attendance_db;
USE attendance_db;

CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(255) PRIMARY KEY,
    password VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    major VARCHAR(255),
    starting_year INT,
    total_attendance INT DEFAULT 0,
    standing VARCHAR(50),
    year INT,
    last_attendance_time DATETIME
);

-- Example: Add a student (ID must match image filename in Images folder, e.g. 1.png or 1.jpg)
-- INSERT INTO students (id, name, major, starting_year, total_attendance, standing, year, last_attendance_time)
-- VALUES ('1', 'John Doe', 'Computer Science', 2023, 0, 'Good', 2, NULL);
