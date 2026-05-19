
import os

import mysql.connector

# MySQL connection settings
DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'root'),
    # Default to provided local MySQL password; env var can still override.
    'password': os.getenv('MYSQL_PASSWORD', 'lokesh@2003'),
    'database': os.getenv('MYSQL_DATABASE', 'attendance_db'),
    'autocommit': True,
    'charset': 'utf8mb4'
}


def get_connection(use_database=True):
    """Returns a MySQL database connection."""
    def _connect(password: str):
        base = dict(DB_CONFIG)
        base["password"] = password
        if use_database:
            return mysql.connector.connect(**base)
        config = {k: v for k, v in base.items() if k != 'database'}
        return mysql.connector.connect(**config)

    try:
        return _connect(DB_CONFIG.get("password", ""))
    except mysql.connector.Error as exc:
        # Make auth failures actionable for users running the script.
        if getattr(exc, "errno", None) == 1045:
            raise RuntimeError(
                "MySQL authentication failed.\n"
                f"- host: {DB_CONFIG.get('host')}:{DB_CONFIG.get('port')}\n"
                f"- user: {DB_CONFIG.get('user')}\n\n"
                "Fix: set your MySQL credentials using environment variables:\n"
                "  MYSQL_HOST=localhost\n"
                "  MYSQL_PORT=3306\n"
                "  MYSQL_USER=<your_user>\n"
                "  MYSQL_PASSWORD=<your_password>\n"
                "  MYSQL_DATABASE=attendance_db\n"
            ) from exc
        raise
