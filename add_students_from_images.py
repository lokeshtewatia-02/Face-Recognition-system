

import os
import mysql.connector
from db_config import get_connection
from config import IMAGES_FOLDER

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')


def student_exists(cursor, student_id):
    """Check if a student with the given ID exists in the students table."""
    try:
        cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
        return cursor.fetchone() is not None
    except mysql.connector.Error as e:
        print(f"Error checking student {student_id}: {e}")
        raise


def add_student(cursor, conn, student_id, name, course):
    """Insert a new student into the students table."""
    try:
        cursor.execute("""
            INSERT INTO students (id, name, major, starting_year, total_attendance, standing, year, last_attendance_time)
            VALUES (%s, %s, %s, NULL, 0, 'Good', NULL, NULL)
        """, (student_id, name, course))
        conn.commit()
        return True
    except mysql.connector.Error as e:
        print(f"Error inserting student {student_id}: {e}")
        conn.rollback()
        return False


def get_student_ids_from_images():
    """Get unique student IDs from image filenames in Images/ folder."""
    if not os.path.exists(IMAGES_FOLDER):
        print(f"Error: Images folder not found at '{IMAGES_FOLDER}'")
        return []

    student_ids = set()
    for filename in os.listdir(IMAGES_FOLDER):
        ext = os.path.splitext(filename)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            student_id = os.path.splitext(filename)[0]
            if student_id:
                student_ids.add(student_id)

    return sorted(student_ids)


def main():
    print("=" * 50)
    print("  Add Students from Images to MySQL")
    print("=" * 50)

    # Get student IDs from images
    student_ids = get_student_ids_from_images()
    if not student_ids:
        print("No image files (.png, .jpg) found in Images/ folder.")
        return

    print(f"\nFound {len(student_ids)} image(s): {', '.join(student_ids)}")

    try:
        conn = get_connection()
        cursor = conn.cursor()

        added = 0
        skipped = 0

        for student_id in student_ids:
            if student_exists(cursor, student_id):
                print(f"  [SKIP] {student_id} - already in database")
                skipped += 1
            else:
                print(f"\n  [NEW] Student ID: {student_id}")
                name = input("       Enter Name: ").strip()
                course = input("       Enter Course: ").strip()

                if not name or not course:
                    print(f"       Skipped - Name and Course are required.")
                    continue

                if add_student(cursor, conn, student_id, name, course):
                    print(f"       Added: {name} ({course})")
                    added += 1

        cursor.close()
        conn.close()

        print("\n" + "-" * 50)
        print(f"Done. Added: {added}, Skipped: {skipped}")

    except mysql.connector.Error as e:
        print(f"\nMySQL Error: {e}")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    main()
