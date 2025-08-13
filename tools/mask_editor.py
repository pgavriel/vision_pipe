import cv2
import numpy as np
import os

# === Config ===
WINDOW_NAME = "Mask Editor"
DEFAULT_SIZE = (800, 600)  # width, height
FULLSCREEN_DEFAULT = False
POINT_RADIUS = 4
POINT_THICKNESS = -1
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# === Globals ===
image = None
mask = None
fullscreen = FULLSCREEN_DEFAULT
points = []  # active polygon points
shapes = []  # list of {"color": (B, G, R), "points": [(x, y), ...]}
current_color = WHITE
invert_mask = False


def init_editor(image_path=None):
    """Initialize the image and mask."""
    global image, mask
    if image_path and os.path.exists(image_path):
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")
        print(f"Loaded image: {image_path}")
    else:
        print("No image provided. Creating black canvas.")
        width, height = DEFAULT_SIZE
        image = np.zeros((height, width, 3), dtype=np.uint8)

    mask = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)


def toggle_fullscreen():
    """Toggle fullscreen/windowed mode."""
    global fullscreen
    fullscreen = not fullscreen
    if fullscreen:
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    else:
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)


def mouse_callback(event, x, y, flags, param):
    """Handle mouse events."""
    global points
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"Adding point at [{x},{y}]")
        points.append((x, y))


def draw_points(frame):
    """Draw the active points on the frame."""
    for (px, py) in points:
        cv2.circle(frame, (px, py), POINT_RADIUS, current_color, POINT_THICKNESS)


def render_mask():
    """Render mask based on shapes list."""
    global mask
    mask[:] = 0  # clear mask
    for shape in shapes:
        if len(shape["points"]) >= 3:
            pts = np.array(shape["points"], np.int32).reshape((-1, 1, 2))
            fill_val = 255 if shape["color"] == WHITE else 0
            cv2.fillPoly(mask, [pts], color=fill_val)

    if invert_mask:
        mask[:] = cv2.bitwise_not(mask)


def main(image_path=None):
    global fullscreen, points, shapes, current_color, invert_mask

    init_editor(image_path)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    if fullscreen:
        cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    while True:
        # Render mask
        render_mask()

        # Show background image + active points
        frame = image.copy()
        draw_points(mask)

        cv2.imshow(WINDOW_NAME, mask)

        key = cv2.waitKey(10) & 0xFF

        if key == 27 or key == ord('q'):  # ESC
            break
        elif key == ord('f'):
            toggle_fullscreen()
        elif key == ord('c'):  # Close current polygon
            if len(points) >= 3:
                shapes.append({"color": current_color, "points": points.copy()})
                print(f"Shape added with {len(points)} points, color={current_color}")
                points.clear()
            else:
                print("Not enough points to form a shape.")
        elif key == ord('x'):  # Toggle shape color
            current_color = WHITE if current_color == BLACK else BLACK
            print(f"Current color set to {'WHITE' if current_color == WHITE else 'BLACK'}")
        elif key == ord('z'):  # Toggle invert mask
            invert_mask = not invert_mask
            print(f"Invert mask set to {invert_mask}")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main(None)
