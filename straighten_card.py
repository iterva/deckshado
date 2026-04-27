"""Straighten (deskew) a card image."""
import cv2
import numpy as np
from pathlib import Path

INPUT = Path(r"cartas por subir\987f9e55-1d08-4f3e-ba69-359f44e939be.jpg")
OUTPUT = INPUT.with_stem(INPUT.stem + "_straight")

img = cv2.imread(str(INPUT))
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Edge detection
edges = cv2.Canny(gray, 50, 150, apertureSize=3)

# Detect lines via Hough transform
lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                        minLineLength=100, maxLineGap=10)

# Collect angles of near-horizontal and near-vertical lines
angles = []
for line in lines:
    x1, y1, x2, y2 = line[0]
    angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
    # Near-horizontal lines (within 15° of 0° or 180°)
    if abs(angle) < 15 or abs(angle - 180) < 15:
        angles.append(angle)
    # Near-vertical lines (within 15° of ±90°)
    elif abs(abs(angle) - 90) < 15:
        angles.append(angle - 90 if angle > 0 else angle + 90)

if angles:
    median_angle = np.median(angles)
else:
    median_angle = 0

print(f"Detected skew angle: {median_angle:.2f}°")

# Rotate to correct the skew
h, w = img.shape[:2]
center = (w // 2, h // 2)
M = cv2.getRotationMatrix2D(center, median_angle, 1.0)

# Compute new bounding box so nothing is cropped
cos = np.abs(M[0, 0])
sin = np.abs(M[0, 1])
new_w = int(h * sin + w * cos)
new_h = int(h * cos + w * sin)
M[0, 2] += (new_w - w) / 2
M[1, 2] += (new_h - h) / 2

rotated = cv2.warpAffine(img, M, (new_w, new_h),
                         borderMode=cv2.BORDER_REPLICATE)

# Auto-crop: find the card rectangle in the rotated image
gray_rot = cv2.cvtColor(rotated, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray_rot, 15, 255, cv2.THRESH_BINARY)
coords = cv2.findNonZero(thresh)
x, y, cw, ch = cv2.boundingRect(coords)
cropped = rotated[y:y+ch, x:x+cw]

cv2.imwrite(str(OUTPUT), cropped, [cv2.IMWRITE_JPEG_QUALITY, 95])
print(f"Saved straightened image to: {OUTPUT}")
