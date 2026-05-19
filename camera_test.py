
import cv2
from config import CAMERA_INDICES, FRAME_WIDTH, FRAME_HEIGHT

print("Camera Test - Find your laptop webcam")
print("Press 0, 1, 2, 3 to switch camera index. Press 'q' to quit.")
print("-" * 50)


def is_likely_bad_green_frame(frame):
    if frame is None or frame.size == 0:
        return True
    mean_bgr = frame.mean(axis=(0, 1))
    b, g, r = float(mean_bgr[0]), float(mean_bgr[1]), float(mean_bgr[2])
    return g > 1.6 * max(r, 1.0) and g > 1.6 * max(b, 1.0) and g > 60


def open_camera(camera_idx):
    for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_ANY):
        cap_local = cv2.VideoCapture(camera_idx, backend)
        if not cap_local.isOpened():
            continue

        cap_local.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        cap_local.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        cap_local.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        for fourcc in ("MJPG", "YUY2"):
            cap_local.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
            for _ in range(3):
                ok, _ = cap_local.read()
                if not ok:
                    break
            ok, frame = cap_local.read()
            if ok and frame is not None and not is_likely_bad_green_frame(frame):
                print(f"Opened camera {camera_idx} with backend={backend}, format={fourcc}")
                return cap_local

        cap_local.release()

    return None

idx = CAMERA_INDICES[0]
cap = open_camera(idx)
if cap is None:
    for i in CAMERA_INDICES:
        cap = open_camera(i)
        if cap is not None and cap.isOpened():
            idx = i
            break

if cap is None or not cap.isOpened():
    print("No camera found!")
    exit(1)

print(f"Starting with camera index {idx}")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    cv2.putText(frame, f"Camera index: {idx}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(frame, "Press 0,1,2,3 to switch | q to quit", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.imshow("Camera Test", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    if key in (ord('0'), ord('1'), ord('2'), ord('3')):
        new_idx = int(chr(key))
        cap.release()
        cap = open_camera(new_idx)
        if cap is not None and cap.isOpened():
            idx = new_idx
            print(f"Switched to camera index {idx}")
        else:
            print(f"Camera {new_idx} failed to open cleanly")

cap.release()
cv2.destroyAllWindows()
print(f"\nUse CAMERA_INDICES = [{idx}, ...] in config.py for laptop camera")
