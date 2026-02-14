import cv2
import mediapipe as mp
import easyocr
import numpy as np

# 1. Initialize AI Models
print("⏳ Loading AI Models...")

# Face Detector (MediaPipe)
mp_face_detection = mp.solutions.face_detection
face_detector = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)

# Text Detector (EasyOCR)
reader = easyocr.Reader(['en'], gpu=False, quantize=False)

print("✅ AI Models Loaded!")

def process_image(input_path, output_path):
    """
    Detects faces and text/handwriting.
    Draws BOUNDING BOXES only (Green for Faces, Red for Text).
    NO LABELS. NO BLURRING.
    """
    
    # A. Load Image
    img = cv2.imread(input_path)
    if img is None:
        return False, "Could not load image"
    
    height, width, _ = img.shape
    detections_count = 0

    # ---------------------------------------------------------
    # B. DETECT FACES (MediaPipe)
    # ---------------------------------------------------------
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = face_detector.process(img_rgb)

    if results.detections:
        for detection in results.detections:
            detections_count += 1
            
            # Get bounding box
            bboxC = detection.location_data.relative_bounding_box
            x = int(bboxC.xmin * width)
            y = int(bboxC.ymin * height)
            w = int(bboxC.width * width)
            h = int(bboxC.height * height)

            # Safety check
            x, y = max(0, x), max(0, y)
            w, h = min(w, width - x), min(h, height - y)

            # VISUALIZE: Draw GREEN box only (No Text Label)
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)

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
        detections_count += 1
        
        # In paragraph mode, result is [[pts], "text_string"]
        bbox = result[0] 
        
        # Convert 4 corner points to x, y, w, h
        (tl, tr, br, bl) = bbox
        x = int(min(tl[0], bl[0]))
        y = int(min(tl[1], tr[1]))
        x_max = int(max(tr[0], br[0]))
        y_max = int(max(bl[1], br[1]))
        
        w = x_max - x
        h = y_max - y
        
        # VISUALIZE: Draw RED box only (No Text Label)
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 0, 255), 2)

    # ---------------------------------------------------------
    # D. Save Annotated Image
    # ---------------------------------------------------------
    cv2.imwrite(output_path, img)
    
    return True, f"Detection Complete: Found {detections_count} regions."