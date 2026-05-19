import cv2
import face_recognition
import pickle
import os

from config import IMAGES_FOLDER, ENCODE_FILE

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')

print(f"Checking path: {IMAGES_FOLDER}")

if not os.path.exists(IMAGES_FOLDER):
    print(f"Error: Images folder not found at '{IMAGES_FOLDER}'")
    exit(1)


def get_student_images():
    seen_ids = set()
    img_list = []
    student_ids = []

    files = sorted(os.listdir(IMAGES_FOLDER),
                   key=lambda x: (os.path.splitext(x)[0], 0 if x.lower().endswith('.png') else 1))
    for filename in files:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue

        student_id = os.path.splitext(filename)[0]
        if not student_id or student_id in seen_ids:
            continue

        path = os.path.join(IMAGES_FOLDER, filename)
        img = cv2.imread(path)
        if img is not None:
            img_list.append(img)
            student_ids.append(student_id)
            seen_ids.add(student_id)
        else:
            print(f"Could not read: {filename}")

    return img_list, student_ids


def find_encodings(images_list):
    encode_list = []
    for i, img in enumerate(images_list):
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encodings = face_recognition.face_encodings(img_rgb)
        if encodings:
            encode_list.append(encodings[0])
        else:
            print(f"Encoding failed for image {i + 1} (no face detected)")
    return encode_list


img_list, student_ids = get_student_images()

if not img_list:
    print("No valid images found.")
    exit(1)

print(f"Students detected: {student_ids}")

print("Encoding Started ...")
encode_list = find_encodings(img_list)
encode_list_with_ids = [encode_list, student_ids]

with open(ENCODE_FILE, 'wb') as f:
    pickle.dump(encode_list_with_ids, f)

print(f"Encoding Complete. Saved to {ENCODE_FILE}")