import cv2
import mediapipe as mp
import easyocr
import numpy as np

# 1. Initialize AI Models
print("[*] Loading AI Models...")

# Face Detector (MediaPipe)
mp_face_detection = mp.solutions.face_detection
face_detector = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

# Text Detector (EasyOCR)
reader = easyocr.Reader(['en'], gpu=False, quantize=False)

print("[*] AI Models Loaded!")

def detect_sensitive_regions(input_path):
    """
    Detects faces and text/handwriting.
    Returns a list of bounding boxes: [((x1, y1), (x2, y2)), ...]
    """
    
    # A. Load Image
    img = cv2.imread(str(input_path))
    if img is None:
        return []
    
    height, width, _ = img.shape
    boxes = []

    # ---------------------------------------------------------
    # B. DETECT FACES (MediaPipe)
    # ---------------------------------------------------------
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_detector.process(img_rgb)

    if results.detections:
        for detection in results.detections:
            # Get bounding box
            bboxC = detection.location_data.relative_bounding_box
            x = int(bboxC.xmin * width)
            y = int(bboxC.ymin * height)
            w = int(bboxC.width * width)
            h = int(bboxC.height * height)

            # Safety check
            x, y = max(0, x), max(0, y)
            w, h = min(w, width - x), min(h, height - y)
            
            # Format: ((x1, y1), (x2, y2))
            boxes.append(((x, y), (x + w, y + h)))

    # ---------------------------------------------------------
    # C. DETECT TEXT & HANDWRITING (EasyOCR)
    # ---------------------------------------------------------
    
    # 1. Preprocessing: Increase Contrast (Helps with handwriting)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced_img = clahe.apply(gray)

    # 2. Run OCR with 'paragraph=True' (Groups words into lines)
    text_results = reader.readtext(enhanced_img, paragraph=True, x_ths=1.0, mag_ratio=1.5)

    for result in text_results:
        # In paragraph mode, result is [[pts], "text_string"]
        bbox = result[0] 
        
        # Convert 4 corner points to x, y, w, h
        (tl, tr, br, bl) = bbox
        x = int(min(tl[0], bl[0]))
        y = int(min(tl[1], tr[1]))
        x_max = int(max(tr[0], br[0]))
        y_max = int(max(bl[1], br[1]))
        
        # Format: ((x1, y1), (x2, y2))
        boxes.append(((x, y), (x_max, y_max)))

    return boxes