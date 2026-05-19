import os
import time
import pickle
import numpy as np
import cv2
import face_recognition
import cvzone
import mysql.connector
from datetime import datetime       


from db_config import get_connection
from config import (
    BASE_DIR, BACKGROUND_IMAGE, MODES_FOLDER, ENCODE_FILE, IMAGES_FOLDER,
    FACE_MATCH_TOLERANCE, ATTENDANCE_COOLDOWN_SECONDS, CAMERA_INDICES,
    FRAME_WIDTH, FRAME_HEIGHT, MODE1_IMAGE_SECONDS, MODE2_IMAGE_SECONDS,
)

cap = None
chosen_camera_idx = None
chosen_backend = cv2.CAP_ANY


def is_likely_bad_green_frame(frame):
    """Detect common webcam decode failure where frame is mostly green."""
    if frame is None or frame.size == 0:
        return True
    mean_bgr = frame.mean(axis=(0, 1))
    b, g, r = float(mean_bgr[0]), float(mean_bgr[1]), float(mean_bgr[2])
    return g > 1.6 * max(r, 1.0) and g > 1.6 * max(b, 1.0) and g > 60


def open_camera_with_fallback(camera_idx, backend):
    cap_local = cv2.VideoCapture(camera_idx, backend)
    if not cap_local.isOpened():
        return None

    cap_local.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap_local.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    cap_local.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    # Prefer compressed stream first; some webcams show green frames without MJPG.
    for fourcc in ("MJPG", "YUY2"):
        cap_local.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
        for _ in range(3):
            ok, _ = cap_local.read()
            if not ok:
                break
        ok, frame = cap_local.read()
        if ok and frame is not None and not is_likely_bad_green_frame(frame):
            return cap_local

    cap_local.release()
    return None


for idx in CAMERA_INDICES:
    # On Windows, MSMF backend can fail with "can't grab frame".
    # Prefer DirectShow first for reliability.
    candidates = [
        (idx, cv2.CAP_DSHOW),
        (idx, cv2.CAP_MSMF),
        (idx, cv2.CAP_ANY),
    ]
    for cam_idx, backend in candidates:
        cap = open_camera_with_fallback(cam_idx, backend)
        if cap is not None and cap.isOpened():
            chosen_camera_idx = cam_idx
            chosen_backend = backend
            print(f"Using camera index {cam_idx} (backend={backend})")
            break
        cap = None
    if cap is not None and cap.isOpened():
        break
if cap is None or not cap.isOpened():
    print("Error: No camera found. Check config.py CAMERA_INDICES")
    exit(1)

imgBackground = cv2.imread(BACKGROUND_IMAGE)
if imgBackground is None:
    print(f"Error: Could not find background at '{BACKGROUND_IMAGE}'")
    exit(1)

if not os.path.exists(MODES_FOLDER):
    print(f"Error: Folder '{MODES_FOLDER}' not found.")
    exit(1)

modePathList = os.listdir(MODES_FOLDER)
imgModeList = [cv2.imread(os.path.join(MODES_FOLDER, p)) for p in modePathList]
imgModeList = [m for m in imgModeList if m is not None]

if not imgModeList:
    print("Error: No valid mode images found.")
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
mode1_start_time = None
mode2_start_time = None
db_status_message = None


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


try:
    while True:
        success, img = cap.read()
        if not success:
            print("Failed to capture from camera. Retrying...")
            # Try to recover once by reopening the chosen camera.
            try:
                cap.release()
            except Exception:
                pass
            cap = open_camera_with_fallback(chosen_camera_idx if chosen_camera_idx is not None else 0, chosen_backend)
            if cap is None:
                cap = open_camera_with_fallback(chosen_camera_idx if chosen_camera_idx is not None else 0, cv2.CAP_ANY)
            success, img = cap.read() if cap is not None else (False, None)
            if not success:
                print("Failed to capture from camera.")
                break

        if is_likely_bad_green_frame(img):
            print("Bad green frame detected. Reinitializing camera...")
            try:
                cap.release()
            except Exception:
                pass
            cap = open_camera_with_fallback(chosen_camera_idx if chosen_camera_idx is not None else 0, chosen_backend)
            if cap is None:
                cap = open_camera_with_fallback(chosen_camera_idx if chosen_camera_idx is not None else 0, cv2.CAP_ANY)
            success, img = cap.read() if cap is not None else (False, None)
            if not success or img is None or is_likely_bad_green_frame(img):
                print("Camera stream still invalid. Try different CAMERA_INDICES in config.py")
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

                            if studentInfo['last_attendance_time']:
                                dt_obj = datetime.strptime(studentInfo['last_attendance_time'], "%Y-%m-%d %H:%M:%S")
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
                                mode1_start_time = time.monotonic()
                            else:
                                modeType = 3
                                counter = 0
                                mode1_start_time = None
                                mode2_start_time = None
                                imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
                        else:
                            modeType = 3
                            counter = 0
                            mode1_start_time = None
                            mode2_start_time = None
                            studentInfo = {"name": "Not in DB", "major": "-"}
                            imgStudent = None
                            imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
                    except mysql.connector.Error as exc:
                        print(f"Database error: {exc}")
                        db_status_message = "Database unavailable"
                        studentInfo = {}
                        imgStudent = None
                        modeType = 1
                        mode1_start_time = time.monotonic()
                        mode2_start_time = None
                    finally:
                        if conn:
                            conn.close()

                if modeType != 3:
                    if (
                        mode1_start_time is not None
                        and mode2_start_time is None
                        and modeType == 1
                        and (time.monotonic() - mode1_start_time) >= MODE1_IMAGE_SECONDS
                    ):
                        modeType = 2
                        mode2_start_time = time.monotonic()

                mode2_just_finished = False
                if (
                    mode2_start_time is not None
                    and modeType == 2
                    and (time.monotonic() - mode2_start_time) >= MODE2_IMAGE_SECONDS
                ):
                    counter = 0
                    modeType = 0
                    studentInfo = {}
                    imgStudent = None
                    mode1_start_time = None
                    mode2_start_time = None
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]
                    mode2_just_finished = True

                if not mode2_just_finished:
                    imgBackground[44:44 + 633, 808:808 + 414] = imgModeList[modeType]

                    if modeType == 1 and db_status_message:
                        cv2.putText(imgBackground, db_status_message, (850, 430),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.8, (0, 0, 255), 2)
                        cv2.putText(imgBackground, "Check MySQL credentials", (835, 470),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.55, (50, 50, 50), 1)
                    elif modeType == 1 and studentInfo:
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
        else:
            modeType = 0
            counter = 0
            db_status_message = None
            mode1_start_time = None
            mode2_start_time = None

        cv2.imshow("Face Attendance", imgBackground)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\nProgram interrupted. Cleaning up...")

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Camera released.")