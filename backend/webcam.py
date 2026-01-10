from ultralytics import YOLO
import cv2
from collections import defaultdict

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

FRAME_THRESHOLD = 10
DIRECTION_THRESHOLD = 30  # pixels accumulated

APPROVED_LABELS = {
    "apple", "banana", "orange",
    "broccoli", "carrot",
    "bottle", "cup", "bowl", "book"
}

frame_counts = defaultdict(int)
confirmed = set()

last_y = {}
direction_score = defaultdict(int)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame)
    r = results[0]

    detected_this_frame = set()

    for box in r.boxes:
        label = r.names[int(box.cls[0])]

        if label not in APPROVED_LABELS:
            continue

        # bounding box center Y
        x1, y1, x2, y2 = box.xyxy[0]
        center_y = int((y1 + y2) / 2)

        detected_this_frame.add(label)

        # track direction
        if label in last_y:
            delta = center_y - last_y[label]
            direction_score[label] += delta

        last_y[label] = center_y

    # reset counters if label disappears
    for label in list(frame_counts.keys()):
        if label not in detected_this_frame:
            frame_counts[label] = 0
            direction_score[label] = 0
            last_y.pop(label, None)

    # update frame counts
    for label in detected_this_frame:
        frame_counts[label] += 1

        if frame_counts[label] >= FRAME_THRESHOLD:
            if direction_score[label] > DIRECTION_THRESHOLD and label not in confirmed:
                print(f"➕ Added to cart: {label}")
                confirmed.add(label)
                # add_to_cart(label)

            elif direction_score[label] < -DIRECTION_THRESHOLD and label in confirmed:
                print(f"➖ Removed from cart: {label}")
                confirmed.discard(label)
                # remove_from_cart(label)

    annotated = r.plot()
    cv2.imshow("YOLOv8", annotated)

    print("CONFIRMED", confirmed)
    print("DIRECTION SCORE", direction_score)
    print("FRAME COUNTS", frame_counts)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
