# pipeline/filters.py
import cv2
import numpy as np
from .base import PipelineStep
from .registry import register
from util.image_utils import resize_image

@register("Blur")
class BlurStep(PipelineStep):
    def apply(self, frame):
        k = self.params.get("ksize", 5)
        self.result = cv2.GaussianBlur(frame, (k, k), 0)
        return self.result
    
@register("Threshold")
class ThresholdStep(PipelineStep):
    def apply(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thresh_val = self.params.get("thresh", 128)
        max_val = self.params.get("max_val", 255)
        _, self.result = cv2.threshold(gray, thresh_val, max_val, cv2.THRESH_BINARY)

        return cv2.cvtColor(self.result, cv2.COLOR_GRAY2BGR)

@register("Invert")
class InvertImageStep(PipelineStep):
    """Inverts the colors of the image."""
    # def __init__(self):
    #     super().__init__()

    def apply(self, frame):
        self.result = cv2.bitwise_not(frame)
        return self.result

@register("AdjustBrightness")
class AdjustBrightnessStep(PipelineStep):
    ''' Increase Brightness: beta > 0
        Decrease Brightness: beta < 0
    '''
    def apply(self, frame):
        beta = self.params.get("beta", 0)  # Brightness shift
        self.result = cv2.convertScaleAbs(frame, alpha=1.0, beta=beta)
        return self.result

@register("AdjustContrast")
class AdjustContrastStep(PipelineStep):
    ''' Increase Contrast: alpha > 1
        Decrease Contrast: 0 > alpha > 1
    '''
    def apply(self, frame):
        alpha = self.params.get("alpha", 1.0)  # Contrast scale
        self.result = cv2.convertScaleAbs(frame, alpha=alpha, beta=0)
        return self.result

@register("ColorShift")
class ColorShift(PipelineStep):
    def apply(self, frame):
        hue_shift = self.params.get("shift", 90) % 360
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)

        # Shift hue (OpenCV hue range is [0, 179], so scale down)
        hsv[..., 0] = (hsv[..., 0] + (hue_shift / 2)) % 180

        hsv = np.clip(hsv, 0, 255).astype(np.uint8)
        self.result =  cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return self.result
    
@register("Colorize")
class ColorizeStep(PipelineStep):
    def apply(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cmap = self.params.get("colormap", "JET").upper()
        cmap_id = getattr(cv2, f"COLORMAP_{cmap}", cv2.COLORMAP_JET)

        self.result = cv2.applyColorMap(gray, cmap_id)
        return self.result
    
@register("GaussianBlur")
class GaussianBlurStep(PipelineStep):
    def apply(self, frame):
        ksize = self.params.get("ksize", 5)
        if ksize % 2 == 0:
            ksize += 1  # must be odd
        self.result = cv2.GaussianBlur(frame, (ksize, ksize), 0)
        return self.result

@register("Resize")
class ResizeStep(PipelineStep):
    """ TEMPLATE
    {
    "name": "Resize",
    "params": {
        "size": [640, 480],
        "keep_aspect": true,
        "pad_color": [0, 0, 0], 
        "output_file": null}
    }
    """
    def apply(self, frame):
        size = self.params.get("size", [640, 480])  # [width, height]
        keep_aspect = self.params.get("keep_aspect", True)
        pad_color = tuple(self.params.get("pad_color", [0, 0, 0]))
        result = resize_image(frame, size, keep_aspect, pad_color)
        return result