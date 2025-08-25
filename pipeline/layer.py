import cv2
import numpy as np
from os.path import join
from .base import PipelineStep
from .registry import register
from util.animator import Animator

@register("Layer")
class LayerStep(PipelineStep):
    def __init__(self, global_config, **params):
        super().__init__(global_config, **params)
        self.params["in_file"] = join(global_config["input_root"],params["source"])
        self.params["position"] = params.get("position",[0.5, 0.5])  # normalized [x, y]
        self.params["scale"] = float(params.get("scale",1.0))
        self.params["rotation"] = float(params.get("rotation",0))
        self.params["opacity"] = float(params.get("opacity", 1.0))
        self.params["paused"] = params.get("paused", False)

        self.animators = {}
        for k, v in self.params.items():
            if isinstance(v, dict) and "mode" in v:  # animator config
                print(f"Creating Animator for {k}")
                self.animators[k] = Animator(config=v)

        # Load source image (with alpha if present)
        self.original_img  = cv2.imread(self.params["in_file"], cv2.IMREAD_UNCHANGED)
        if self.original_img  is None:
            raise FileNotFoundError(f"Layer source not found: {self.original_img}")
        
        # Cache
        self._cached_img = None
        self._cached_params = None

    def _update_cache(self, frame_shape):
        h, w = frame_shape[:2]
        img = self.original_img

        # compute target size
        new_w = int(img.shape[1] * self.params["scale"])
        new_h = int(img.shape[0] * self.params["scale"])

        if new_w <= 0 or new_h <= 0:
            self._cached_img = None
            return

        # resize
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # rotate
        if self.params["rotation"] != 0:
            M = cv2.getRotationMatrix2D((new_w / 2, new_h / 2), self.params["rotation"], 1.0)
            cos = np.abs(M[0, 0])
            sin = np.abs(M[0, 1])

            # compute bounding box of rotated image
            new_w_rot = int((new_h * sin) + (new_w * cos))
            new_h_rot = int((new_h * cos) + (new_w * sin))

            M[0, 2] += (new_w_rot / 2) - (new_w / 2)
            M[1, 2] += (new_h_rot / 2) - (new_h / 2)

            rotated = cv2.warpAffine(resized, M, (new_w_rot, new_h_rot), flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=(0, 0, 0, 0))  # RGBA black/transparent)
            self._cached_img = rotated
        else:
            self._cached_img = resized

        self._cached_params = (self.params["scale"], self.params["rotation"])

    def apply(self, frame):
        if self.original_img is None:
            return frame

        # Update Animator Params
        if not self.params["paused"]:
            for k, v in self.animators.items():
                if isinstance(v, Animator):
                    self.params[k] = v.step()
        # check cache
        if self._cached_params != (self.params["scale"], self.params["rotation"]):
            self._update_cache(frame.shape)

        if self._cached_img is None:
            return frame

        layer = self._cached_img
        lh, lw = layer.shape[:2]
        fh, fw = frame.shape[:2]

        # target center in pixel coordinates
        cx = int(self.params["position"][0] * fw)
        cy = int(self.params["position"][1] * fh)

        # top-left corner
        x1 = cx - lw // 2
        y1 = cy - lh // 2
        x2 = x1 + lw
        y2 = y1 + lh

        # clip to frame
        if x1 >= fw or y1 >= fh or x2 <= 0 or y2 <= 0:
            return frame  # completely out of frame

        x1_clip = max(x1, 0)
        y1_clip = max(y1, 0)
        x2_clip = min(x2, fw)
        y2_clip = min(y2, fh)

        lx1 = x1_clip - x1
        ly1 = y1_clip - y1
        lx2 = lx1 + (x2_clip - x1_clip)
        ly2 = ly1 + (y2_clip - y1_clip)

        roi = frame[y1_clip:y2_clip, x1_clip:x2_clip]
        layer_crop = layer[ly1:ly2, lx1:lx2]

        # handle transparency (if source has alpha)
        if layer_crop.shape[2] == 4:
            alpha = (layer_crop[:, :, 3] / 255.0) * self.params["opacity"]
            for c in range(3):
                roi[:, :, c] = (1 - alpha) * roi[:, :, c] + alpha * layer_crop[:, :, c]
        else:
            cv2.addWeighted(layer_crop, self.params["opacity"], roi, 1 - self.params["opacity"], 0, roi)

        frame[y1_clip:y2_clip, x1_clip:x2_clip] = roi
        return frame