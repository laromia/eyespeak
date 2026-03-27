import cv2
import mediapipe as mp
import time
import numpy as np
import os
import urllib.request

class EyeBlinkDetector:
    def __init__(self, blink_threshold=0.15, short_blink_limit=0.4, long_blink_limit=1.2, min_blink_duration=0.2):
        # MediaPipe Tasks API setup
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        self.model_path = os.path.join(os.path.dirname(__file__), 'face_landmarker.task')
        self._ensure_model_exists()
        
        with open(self.model_path, 'rb') as f:
            model_data = f.read()
        
        base_options = python.BaseOptions(model_asset_buffer=model_data)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            num_faces=1
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)
        
        # Vertical landmarks for EAR-like calculation (same indices as solutions API)
        self.LEFT_UPPER = 386
        self.LEFT_LOWER = 374
        self.RIGHT_UPPER = 159
        self.RIGHT_LOWER = 145
        
        self.blink_threshold = blink_threshold
        self.short_blink_limit = short_blink_limit
        self.long_blink_limit = long_blink_limit
        self.min_blink_duration = min_blink_duration
        
        self.is_blinking = False
        self.blink_start_time = 0
        self.last_blink_end_time = time.time()
        self.last_ear = 0.0
        
        # Track last blinks for gesture detection (triple blink to clear)
        self.blink_timestamps = []

    def _ensure_model_exists(self):
        """Download the model if it's not present."""
        if not os.path.exists(self.model_path):
            print(f"Downloading MediaPipe Face Landmarker model to {self.model_path}...")
            url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
            urllib.request.urlretrieve(url, self.model_path)
            print("Download complete.")

    def calculate_ear(self, landmarks, upper_idx, lower_idx):
        """Simple Eye Aspect Ratio calculation using normalized vertical distance.
        Since we are using normalized landmarks, we just take the vertical distance.
        We multiply by a scale factor to make it more intuitive."""
        upper = landmarks[upper_idx]
        lower = landmarks[lower_idx]
        
        # We use the y-coordinate difference. Landmarks are normalized 0-1.
        distance = abs(upper.y - lower.y)
        return distance * 10.0 # Scaling to make values around 0.1-0.3

    def process_frame(self, frame):
        # Convert to MediaPipe Image
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # Process detection
        detection_result = self.detector.detect(mp_image)
        
        blink_detected = None
        ear = self.last_ear
        landmarks = None
        
        if detection_result.face_landmarks:
            landmarks = detection_result.face_landmarks[0]
            
            left_ear = self.calculate_ear(landmarks, self.LEFT_UPPER, self.LEFT_LOWER)
            right_ear = self.calculate_ear(landmarks, self.RIGHT_UPPER, self.RIGHT_LOWER)
            
            # Blink logic: both eyes must be below the threshold to count as a deliberate blink
            # This filters out natural single-eye movements or side-profile issues
            if left_ear < self.blink_threshold and right_ear < self.blink_threshold:
                ear = (left_ear + right_ear) / 2.0
                if not self.is_blinking:
                    self.is_blinking = True
                    self.blink_start_time = time.time()
            else:
                ear = (left_ear + right_ear) / 2.0
                if self.is_blinking:
                    self.is_blinking = False
                    duration = time.time() - self.blink_start_time
                    current_time = time.time()
                    self.last_blink_end_time = current_time
                    
                    # Store blink for gesture detection (triple blink)
                    self.blink_timestamps.append(current_time)
                    # Keep only the last 3 timestamps
                    if len(self.blink_timestamps) > 3:
                        self.blink_timestamps.pop(0)
                    
                    # Check for Triple Blink gesture (3 blinks in less than 1.5 seconds)
                    if len(self.blink_timestamps) == 3:
                        if (self.blink_timestamps[2] - self.blink_timestamps[0]) < 1.5:
                            blink_detected = "clear"
                            self.blink_timestamps = [] # Reset after gesture
                    
                    # If no gesture was detected, handle as normal blink
                    if blink_detected is None:
                        if duration < self.min_blink_duration:
                            blink_detected = None # Too short, ignore (fatigue/micro-blink)
                        elif duration < self.short_blink_limit:
                            blink_detected = "."
                        elif duration < self.long_blink_limit:
                            blink_detected = "-"
                        else:
                            blink_detected = "reset"
            
            self.last_ear = ear
                        
        return blink_detected, ear, frame, landmarks

    def get_landmarks(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        detection_result = self.detector.detect(mp_image)
        if detection_result.face_landmarks:
            return detection_result.face_landmarks[0]
        return None
