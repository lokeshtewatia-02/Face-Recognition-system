"""
Utility script to add students to MySQL database.
Student ID must match the image filename in Images/ folder (e.g., 1.png, 2.jpg)
"""

from db_config import get_connection

def add_student(student_id, name, major, starting_year, standing="Good", year=1):
    """Add a new student to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO students (id, name, major, starting_year, total_attendance, standing, year, last_attendance_time)
            VALUES (%s, %s, %s, %s, 0, %s, %s, NULL)
        """, (student_id, name, major, starting_year, standing, year))
        conn.commit()
        print(f"Student '{name}' (ID: {student_id}) added successfully.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Add Student to Face Attendance System")
    print("Ensure the student's image exists in Images/ folder (e.g., Images/1.png)")
    print("-" * 40)
    student_id = input("Student ID (must match image filename): ").strip()
    name = input("Name: ").strip()
    major = input("Major: ").strip()
    starting_year = int(input("Starting Year (e.g., 2023): "))
    standing = input("Standing (default: Good): ").strip() or "Good"
    year = int(input("Year (1, 2, 3, 4): ") or "1")
    add_student(student_id, name, major, starting_year, standing, year)
