
import os

# Project root directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Resource paths
IMAGES_FOLDER = os.path.join(BASE_DIR, 'Images')
RESOURCES_FOLDER = os.path.join(BASE_DIR, 'Resources')
BACKGROUND_IMAGE = os.path.join(RESOURCES_FOLDER, 'background.png')
MODES_FOLDER = os.path.join(RESOURCES_FOLDER, 'Modes')
ENCODE_FILE = os.path.join(BASE_DIR, 'EncodeFile.p')

# Face recognition settings
FACE_MATCH_TOLERANCE = 0.5
ATTENDANCE_COOLDOWN_SECONDS = 30

MODE1_IMAGE_SECONDS = 3.0
MODE2_IMAGE_SECONDS = 0.35

# Camera settings

# Try external webcam first (often index 1), then built-in camera (index 0).
CAMERA_INDICES = [0, 1]
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
