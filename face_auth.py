import cv2
import pickle
import os
import numpy as np
import mediapipe as mp

DB_FILE = "faces_db.pkl"

_fd = None

def _get_face_detector():
    global _fd
    if _fd is None:
        _fd = mp.solutions.face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)
    return _fd

def _extract_face_roi(frame):
    detector = _get_face_detector()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = detector.process(rgb)
    if not result.detections:
        return None
    det = result.detections[0]
    bbox = det.location_data.relative_bounding_box
    h, w, _ = frame.shape
    x = max(0, int(bbox.xmin * w))
    y = max(0, int(bbox.ymin * h))
    bw = int(bbox.width * w)
    bh = int(bbox.height * h)
    roi = frame[max(0,y):min(h,y+bh), max(0,x):min(w,x+bw)]
    if roi.size == 0:
        return None
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (200, 200))
    return gray


def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def save_db(db):
    with open(DB_FILE, "wb") as f:
        pickle.dump(db, f)


def register_face(frame, username):

    roi = _extract_face_roi(frame)
    if roi is None:
        return False, "No face detected"
    db = load_db()
    images = db.get(username, [])
    images.append(roi.copy())
    db[username] = images
    save_db(db)
    return True, "Face registered successfully"


def recognize_face(frame):

    db = load_db()

    if len(db) == 0:
        return "NO_DB"

    roi = _extract_face_roi(frame)
    if roi is None:
        return "NO_FACE"
    
    X = []
    y = []
    labels = {}
    idx = 0
    for username, imgs in db.items():
        if isinstance(imgs, list):
            for im in imgs:
                if isinstance(im, np.ndarray):
                    X.append(im)
                    y.append(idx)
            labels[idx] = username
            idx += 1
    if len(X) == 0:
        return None
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(X, np.array(y, dtype=np.int32))
        label, confidence = recognizer.predict(roi)
        if confidence < 60 and label in labels:
            return labels[label]
    except Exception:
        best_name = None
        best_score = None
        for username, imgs in db.items():
            if isinstance(imgs, list) and len(imgs) > 0 and isinstance(imgs[0], np.ndarray):
                avg = np.mean(np.stack(imgs), axis=0)
                dist = np.mean((roi.astype(np.float32) - avg.astype(np.float32)) ** 2)
                if best_score is None or dist < best_score:
                    best_score = dist
                    best_name = username
        if best_score is not None and best_score < 2000:
            return best_name
    return None
