"""
Create/verify required DB schema and seed students from Images filenames.

This script:
1) Ensures attendance_db and required tables exist (via init_database helpers)
2) Reads student IDs from Images/*.png|*.jpg|*.jpeg
3) Inserts missing students with default details
"""

import os

from config import IMAGES_FOLDER
from db_config import get_connection
from init_database import create_database, create_tables, ensure_default_user

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")


def get_student_ids_from_images():
    student_ids = set()
    if not os.path.isdir(IMAGES_FOLDER):
        return []

    for filename in os.listdir(IMAGES_FOLDER):
        ext = os.path.splitext(filename)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            student_id = os.path.splitext(filename)[0].strip()
            if student_id:
                student_ids.add(student_id)
    return sorted(student_ids)


def upsert_students(student_ids):
    conn = get_connection(use_database=True)
    added = 0
    skipped = 0
    try:
        cur = conn.cursor()
        for student_id in student_ids:
            cur.execute("SELECT id FROM students WHERE id=%s", (student_id,))
            if cur.fetchone():
                skipped += 1
                continue

            # Default details; you can edit later from app/tools.
            cur.execute(
                """
                INSERT INTO students
                (id, name, major, starting_year, total_attendance, standing, year, last_attendance_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL)
                """,
                (student_id, student_id, "IT", 2023, 0, "Good", 1),
            )
            added += 1
        conn.commit()
    finally:
        conn.close()
    return added, skipped


def main():
    print("Preparing database and seeding students...")
    create_database()
    create_tables()
    ensure_default_user()

    student_ids = get_student_ids_from_images()
    if not student_ids:
        print("No student images found in Images folder.")
        return

    added, skipped = upsert_students(student_ids)
    print(f"Done. Found={len(student_ids)} Added={added} Skipped={skipped}")


if __name__ == "__main__":
    main()
