from ultralytics import YOLO

model = YOLO("yolov8n.pt")

model.predict(source="video.mp4", save=True)

print("Done!")