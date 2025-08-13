# utils/image.py
import cv2
import numpy as np

def resize_image(image, output_size, keep_aspect=True, padding_color=(0, 0, 0)):
    target_w, target_h = output_size

    if not keep_aspect:
        return cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_AREA)

    h, w = image.shape[:2]
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)

    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    pad_left = (target_w - new_w) // 2
    pad_right = target_w - new_w - pad_left
    pad_top = (target_h - new_h) // 2
    pad_bottom = target_h - new_h - pad_top

    result = cv2.copyMakeBorder(
        resized,
        pad_top, pad_bottom ,
        pad_left, pad_right,
        borderType=cv2.BORDER_CONSTANT,
        value=padding_color
    )
    # print(f"Desired Size: {output_size} - Result: {result.shape}")
    return result
