# pipeline/filters.py
import cv2
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