import json
import cv2
import time
import os
from os.path import join
import re
from pathlib import Path

def get_unique_output_path(base_path):
    """
    Given a path like 'output/frame.png', returns a path like 'output/frame_000001.png'
    based on how many existing files match 'frame_######.png' in the directory.
    """
    base_path = Path(base_path)
    parent_dir = base_path.parent
    stem = base_path.stem  # 'frame'
    suffix = base_path.suffix  # '.png'

    pattern = re.compile(rf"^{re.escape(stem)}_(\d{{6}}){re.escape(suffix)}$")
    existing_ids = []
    for file in parent_dir.glob(f"{stem}_*{suffix}"):
        match = pattern.match(file.name)
        if match:
            existing_ids.append(int(match.group(1)))
    next_id = max(existing_ids, default=-1) + 1
    new_name = f"{stem}_{next_id:06d}{suffix}"
    return str(parent_dir / new_name)

def open_input_stream(input_root, input_type, input_source, framerate=30):
    return InputStreamWrapper(input_root, input_type, input_source, framerate)

class InputStreamWrapper:
    def __init__(self, input_root, input_type, input_source, framerate=30):
        self.root = input_root
        self.input_type = input_type
        self.input_source = input_source
        self.framerate = framerate
        self.delay = 1.0 / framerate if framerate != 0 else 0
        self.last_frame_time = time.time()

        if input_type == "image":
            self.input_source = join(input_root,input_source)
            if not os.path.exists(self.input_source):
                raise FileNotFoundError(f"Image not found: {self.input_source}")
            self.frame = cv2.imread(self.input_source)
            if self.frame is None:
                raise ValueError(f"Failed to read image: {self.input_source}")
            self.finished = False

        elif input_type in {"video", "live"}:
            if input_type == "live":
                print("Opening live feed...")
                # input_source should be device index, e.g., 0
                self.cap = cv2.VideoCapture(int(input_source))
            else:  # video file
                self.input_source = join(input_root,input_source)
                if not os.path.exists(self.input_source):
                    raise FileNotFoundError(f"Video not found: {self.input_source}")
                self.cap = cv2.VideoCapture(self.input_source)

            if not self.cap.isOpened():
                raise ValueError(f"Failed to open input: {input_source}")
        else:
            raise ValueError(f"Unknown input type: {input_type}")

    def read(self):
        if self.input_type == "image":
            if self.finished:
                return None
            # self.finished = True
            return self.frame

        # For video/live, throttle by framerate
        now = time.time()
        elapsed = now - self.last_frame_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_frame_time = time.time()

        ret, frame = self.cap.read()
        return frame if ret else None

    def release(self):
        if self.input_type in {"video", "live"}:
            self.cap.release()

    def is_open(self):
        if self.input_type == "image":
            return not self.finished
        return self.cap.isOpened()
