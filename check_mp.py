import mediapipe
print("Mediapipe version:", mediapipe.__version__)
print("Attributes:", dir(mediapipe))
try:
    from mediapipe import solutions
    print("Successfully imported solutions")
except ImportError as e:
    print("Failed to import solutions:", e)
