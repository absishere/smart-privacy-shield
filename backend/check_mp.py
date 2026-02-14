import mediapipe as mp
print(dir(mp))
try:
    print(mp.solutions)
    print("✅ SUCCESS: MediaPipe Solutions loaded!")
except AttributeError:
    print("❌ ERROR: Still broken.")