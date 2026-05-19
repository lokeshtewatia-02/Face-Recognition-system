
import os
import pickle
import numpy as np
import cv2
import face_recognition
import cvzone
import hashlib
from datetime import datetime

from db_config import get_connection
from config import (
    BACKGROUND_IMAGE, MODES_FOLDER, ENCODE_FILE, IMAGES_FOLDER,
    FACE_MATCH_TOLERANCE, ATTENDANCE_COOLDOWN_SECONDS, CAMERA_INDICES,
    FRAME_WIDTH, FRAME_HEIGHT
)

# DATABASE SETUP - MySQL
def init_db():
    """Create database and tables, add default user."""
    conn = get_connection(use_database=False)
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE DATABASE IF NOT EXISTS attendance_db")
        conn.commit()
    finally:
        conn.close()

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(255) PRIMARY KEY,
                password VARCHAR(255) NOT NULL
            )
        ''')
        cursor.execute('''
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
        ''')

        default_user = "root"
        default_pass = "lokesh@2003"
        hashed_pass = hashlib.sha256(default_pass.encode()).hexdigest()

        cursor.execute("SELECT * FROM users WHERE username=%s", (default_user,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (default_user, hashed_pass))
            print(f"Default user '{default_user}' created.")
        conn.commit()
    finally:
        conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def login():
    print("\n" + "=" * 30)
    print("  FACE ATTENDANCE LOGIN")
    print("=" * 30)
    username = input("Username: ").strip()
    password = input("Password: ")
    hashed_input = hash_password(password)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, hashed_input))
        result = cursor.fetchone()
    finally:
        conn.close()

    if result:
        print("\n[✔] Login Successful!\n")
        return True
    print("\n[✘] Invalid Username or Password.")
    return False


if not login():
    exit()

# Load resources
if not os.path.exists(BACKGROUND_IMAGE):
    print(f"Error: '{BACKGROUND_IMAGE}' missing.")
    exit(1)

imgBackground = cv2.imread(BACKGROUND_IMAGE)
if not os.path.exists(MODES_FOLDER):
    print(f"Error: Folder '{MODES_FOLDER}' missing.")
    exit(1)

modePathList = os.listdir(MODES_FOLDER)
imgModeList = [cv2.imread(os.path.join(MODES_FOLDER, p)) for p in modePathList]
imgModeList = [m for m in imgModeList if m is not None]

if not imgModeList:
    print("Error: No valid mode images.")
    exit(1)

print("Loading Encode File ...")
try:
    with open(ENCODE_FILE, 'rb') as f:
        encodeListKnownWithIds = pickle.load(f)
    encodeListKnown, studentIds = encodeListKnownWithIds
    print(f"Encode File Loaded ({len(studentIds)} students)")
except FileNotFoundError:
    print(f"Error: '{ENCODE_FILE}' not found. Run encoded.py first.")
    exit(1)

modeType = 0
counter = 0
current_id = None
imgStudent = None
studentInfo = {}


def get_student_image_path(student_id):
    for ext in ('.png', '.jpg', '.jpeg'):
        path = os.path.join(IMAGES_FOLDER, f"{student_id}{ext}")
        if os.path.exists(path):
            return path
    return None


def format_datetime(dt):
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S") if hasattr(dt, 'strftime') else str(dt)


cap = None
for idx in CAMERA_INDICES:
    cap = cv2.VideoCapture(idx)
    if cap.isOpened():
        cap.set(3, FRAME_WIDTH)
        cap.set(4, FRAME_HEIGHT)
        print(f"Using camera index {idx} (laptop webcam)")
        break
    cap.release()
if cap is None or not cap.isOpened():
    print("Error: No camera found. Check config.py CAMERA_INDICES")
    exit(1)

try:
    while True:
        success, img = cap.read()
        if not success:
            break

        img_small = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        img_small = cv2.cvtColor(img_small, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(img_small)
        face_encodings = face_recognition.face_encodings(img_small, face_locations)

        imgBackground[162:162 + 480, 55:55 + 640] = img
        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

        if face_locations:
            for encode_face, face_loc in zip(face_encodings, face_locations):
                matches = face_recognition.compare_faces(
                    encodeListKnown, encode_face, tolerance=FACE_MATCH_TOLERANCE
                )
                face_distances = face_recognition.face_distance(encodeListKnown, encode_face)
                match_index = np.argmin(face_distances)

                if matches[match_index]:
                    y1, x2, y2, x1 = face_loc
                    y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                    bbox = 55 + x1, 162 + y1, x2 - x1, y2 - y1
                    imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)
                    current_id = studentIds[match_index]

                    if counter == 0:
                        cvzone.putTextRect(imgBackground, "Loading", (275, 400))
                        cv2.imshow("Face Attendance", imgBackground)
                        cv2.waitKey(1)
                        counter = 1
                        modeType = 1

            if counter != 0:
                if counter == 1:
                    conn = None
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT * FROM students WHERE id=%s", (current_id,))
                        row = cursor.fetchone()

                        if row:
                            last_time_str = format_datetime(row[7])
                            studentInfo = {
                                "id": row[0], "name": row[1], "major": row[2],
                                "starting_year": row[3], "total_attendance": row[4],
                                "standing": row[5], "year": row[6], "last_attendance_time": last_time_str
                            }

                            img_path = get_student_image_path(current_id)
                            imgStudent = cv2.imread(img_path) if img_path else None

                            if last_time_str:
                                dt_obj = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
                                seconds_elapsed = (datetime.now() - dt_obj).total_seconds()
                            else:
                                seconds_elapsed = 99999

                            if seconds_elapsed > ATTENDANCE_COOLDOWN_SECONDS:
                                new_attendance = studentInfo['total_attendance'] + 1
                                new_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                cursor.execute(
                                    "UPDATE students SET total_attendance=%s, last_attendance_time=%s WHERE id=%s",
                                    (new_attendance, new_time, current_id)
                                )
                                conn.commit()
                                studentInfo['total_attendance'] = new_attendance
                            else:
                                modeType = 3
                                counter = 0
                                imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
                        else:
                            modeType = 3
                            counter = 0
                            studentInfo = {"name": "Not in DB", "major": "-"}
                            imgStudent = None
                            imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
                    finally:
                        if conn:
                            conn.close()

                if modeType != 3:
                    if 10 < counter < 20:
                        modeType = 2
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                    if counter <= 10 and studentInfo:
                        cv2.putText(imgBackground, str(studentInfo.get('total_attendance', '')), (861, 125),
                                    cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)
                        cv2.putText(imgBackground, str(studentInfo.get('major', '')), (1006, 550),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(imgBackground, str(current_id), (1006, 493),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.5, (255, 255, 255), 1)
                        cv2.putText(imgBackground, str(studentInfo.get('standing', '') or ''), (910, 625),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                        cv2.putText(imgBackground, str(studentInfo.get('year', '') or ''), (1025, 625),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)
                        cv2.putText(imgBackground, str(studentInfo.get('starting_year', '') or ''), (1125, 625),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.6, (100, 100, 100), 1)

                        name_str = str(studentInfo.get('name', ''))
                        (w, _), _ = cv2.getTextSize(name_str, cv2.FONT_HERSHEY_COMPLEX, 1, 1)
                        offset = (414 - w) // 2
                        cv2.putText(imgBackground, name_str, (808 + offset, 445),
                                    cv2.FONT_HERSHEY_COMPLEX, 1, (50, 50, 50), 1)

                        if imgStudent is not None:
                            img_resized = cv2.resize(imgStudent, (216, 216))
                            imgBackground[175:175 + 216, 909:909 + 216] = img_resized

                    counter += 1
                    if counter >= 20:
                        counter, modeType = 0, 0
                        studentInfo, imgStudent = {}, None
                        imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
        else:
            modeType, counter = 0, 0

        cv2.imshow("Face Attendance", imgBackground)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    cap.release()
    cv2.destroyAllWindows()
