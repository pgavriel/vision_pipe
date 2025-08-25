# pipeline/filters.py
import cv2
import numpy as np
from .base import PipelineStep
from .registry import register
from util.image_utils import resize_image

@register("Flip")
class FlipStep(PipelineStep):
    def apply(self, frame):
        flip_x = self.params.get("flip_x",False)
        flip_y = self.params.get("flip_y",False)
        if not flip_x and not flip_y:
            self.result = frame
        elif flip_x and flip_y:
            self.result = cv2.flip(frame,-1)
        elif flip_x:
            self.result = cv2.flip(frame,0)
        else:# elif flip_y:
            self.result = cv2.flip(frame,1)
        return self.result

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
        hue_shift = self.params.get("hue_shift", 90) % 360
        sat_shift = self.params.get("saturation_shift",0)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)

        # Shift hue (OpenCV hue range is [0, 179], so scale down)
        hsv[..., 0] = (hsv[..., 0] + (hue_shift / 2)) % 180

        # Adjust saturation
        hsv[..., 1] = hsv[..., 1] + sat_shift

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

@register("Tile")
class TileStep(PipelineStep):
    def apply(self, frame):
        n = max(1, int(self.params.get("n", 2)))
        mirror = bool(self.params.get("mirror", False))
        downscale = self.params.get("downscale",True)
        h, w = frame.shape[:2]

        
        # Create tiled canvas
        if downscale:
            # Scale down to tile size
            small = cv2.resize(frame, (w // n, h // n), interpolation=cv2.INTER_AREA)
            tiled = np.zeros((h, w, 3), dtype=frame.dtype)
        else:
            small = frame
            tiled = np.zeros((h*n, w*n, 3), dtype=frame.dtype)

        for row in range(n):
            for col in range(n):
                tile = small.copy()

                if mirror:
                    # Flip horizontally if col is odd
                    if col % 2 == 1:
                        tile = cv2.flip(tile, 1)
                    # Flip vertically if row is odd
                    if row % 2 == 1:
                        tile = cv2.flip(tile, 0)

                # Place tile in the right spot
                if downscale:
                    y0, y1 = row * (h // n), (row + 1) * (h // n)
                    x0, x1 = col * (w // n), (col + 1) * (w // n)
                else:
                    y0, y1 = row * (h), (row + 1) * (h)
                    x0, x1 = col * (w ), (col + 1) * (w)
                tiled[y0:y1, x0:x1] = tile
                    

        self.result = tiled
        return self.result
    

@register("Border")
class Border(PipelineStep):
    def apply(self, frame):
        width = self.params.get("width", 20)
        color = self.params.get("color", [0, 0, 0])  # default black BGR

        # Ensure color is in BGR list form
        if isinstance(color, tuple):
            color = list(color)
        if len(color) != 3:
            color = [0, 0, 0]

        self.result = cv2.copyMakeBorder(
            frame,
            top=width,
            bottom=width,
            left=width,
            right=width,
            borderType=cv2.BORDER_CONSTANT,
            value=color
        )
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

# TODO: add automatic inference of the input_type (e.g., detect if the frame has 1 vs 3 channels, so you don’t have to specify it manually
@register("ColorConvert")   
class ColorConvertStep(PipelineStep):
    COLOR_MAP = {
        ("bgr", "gray"): cv2.COLOR_BGR2GRAY,
        ("bgr", "rgb"): cv2.COLOR_BGR2RGB,
        ("bgr", "hsv"): cv2.COLOR_BGR2HSV,
        ("rgb", "bgr"): cv2.COLOR_RGB2BGR,
        ("rgb", "gray"): cv2.COLOR_RGB2GRAY,
        ("rgb", "hsv"): cv2.COLOR_RGB2HSV,
        ("hsv", "bgr"): cv2.COLOR_HSV2BGR,
        ("hsv", "rgb"): cv2.COLOR_HSV2RGB,
        ("gray", "bgr"): cv2.COLOR_GRAY2BGR,
        ("gray", "rgb"): cv2.COLOR_GRAY2RGB,
    }

    def apply(self, frame):
        input_type = self.params.get("input_type", "bgr").lower()
        output_type = self.params.get("output_type", "gray").lower()

        if (input_type, output_type) not in self.COLOR_MAP:
            raise ValueError(
                f"Unsupported color conversion: {input_type} -> {output_type}"
            )

        code = self.COLOR_MAP[(input_type, output_type)]
        self.result = cv2.cvtColor(frame, code)
        return self.result