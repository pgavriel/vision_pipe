import json
import cv2
import time
import os
from os.path import join
import re
from pathlib import Path

import tkinter as tk
from tkinter import filedialog

def file_dialog(mode="open", initial_dir=".", filetypes=(("All files", "*.*"),), title="Select a file", defaultextension=None):
    """
    Opens a file dialog for opening or saving files.

    Parameters:
        mode (str): "open" for selecting an existing file, "save" for choosing a file to save.
        filetypes (tuple): List of (label, pattern) tuples for filtering file types.
        title (str): Dialog window title.
        defaultextension (str): Default extension for saving files (e.g., ".txt").

    Returns:
        str or None: Selected file path, or None if canceled.
    """
    root = tk.Tk()
    root.withdraw()  # Hide main window

    if mode == "open":
        return filedialog.askopenfilename(title=title, filetypes=filetypes, initialdir=initial_dir)
    elif mode == "save":
        return filedialog.asksaveasfilename(title=title, filetypes=filetypes, initialdir=initial_dir, defaultextension=defaultextension)
    else:
        raise ValueError("Invalid mode. Use 'open' or 'save'.")

def open_image_dialogue():
    return file_dialog(mode="open",
                       initial_dir=".",
                       filetypes=(("Images","*.png;*.jpg;*.jpeg"),("All files", "*.*"),),
                       title="Open Image")

def save_image_dialogue():
    return file_dialog(mode="save",
                       initial_dir=".",
                       filetypes=(("Images","*.png;*.jpg;*.jpeg"),("All files", "*.*"),),
                       title="Open Image")

def export_config(config: dict, current_config_path: str):
    """
    Export current configuration to a new JSON file.
    
    Args:
        config (dict): The configuration dictionary to export.
        current_config_path (str): Path of the currently loaded config file.
    """

    # Make sure Tk doesn't show the main window
    root = tk.Tk()
    root.withdraw()

    # Build default filename
    base, ext = os.path.splitext(os.path.basename(current_config_path))
    default_filename = f"{base}_new.json"

    # Open save file dialog
    save_path = filedialog.asksaveasfilename(
        initialdir=os.path.dirname(current_config_path),
        initialfile=default_filename,
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )

    if save_path:
        # Write JSON with indentation, preserve key order
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        print(f"Config exported to {save_path}")
    else:
        print("Export canceled.")

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
