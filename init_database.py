"""
Initialize MySQL database schema for the Face Attendance project.

Usage (PowerShell):
  $env:MYSQL_HOST="localhost"
  $env:MYSQL_PORT="3306"
  $env:MYSQL_USER="root"
  $env:MYSQL_PASSWORD="your_password"
  $env:MYSQL_DATABASE="attendance_db"
  .\.venv\Scripts\python.exe .\init_database.py
"""

import hashlib

import mysql.connector

from db_config import DB_CONFIG, get_connection


def _connect_without_database():
    config = dict(DB_CONFIG)
    config.pop("database", None)
    return mysql.connector.connect(**config)


def create_database():
    db_name = DB_CONFIG["database"]
    conn = _connect_without_database()
    try:
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    finally:
        conn.close()


def create_tables():
    conn = get_connection(use_database=True)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(255) PRIMARY KEY,
                password VARCHAR(255) NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(255),
                major VARCHAR(255),
                starting_year INT,
                total_attendance INT DEFAULT 0,
                standing VARCHAR(50),
                year INT,
                last_attendance_time DATETIME
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def ensure_default_user():
    username = "root"
    password = "lokesh@2003"
    hashed = hashlib.sha256(password.encode()).hexdigest()

    conn = get_connection(use_database=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE username=%s", (username,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, hashed),
            )
            conn.commit()
            print(f"Created app login user '{username}' in users table.")
        else:
            print(f"App login user '{username}' already exists.")
    finally:
        conn.close()


def main():
    print("Initializing database...")
    try:
        create_database()
        create_tables()
        ensure_default_user()
    except mysql.connector.Error as exc:
        if getattr(exc, "errno", None) == 1045:
            print(
                "MySQL authentication failed. Set valid credentials and rerun.\n"
                "PowerShell example:\n"
                "  $env:MYSQL_HOST='localhost'\n"
                "  $env:MYSQL_PORT='3306'\n"
                "  $env:MYSQL_USER='root'\n"
                "  $env:MYSQL_PASSWORD='your_real_mysql_password'\n"
                "  $env:MYSQL_DATABASE='attendance_db'\n"
                "  .\\.venv\\Scripts\\python.exe .\\init_database.py"
            )
            raise
        raise
    print("Database setup completed successfully.")


if __name__ == "__main__":
    main()
