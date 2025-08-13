# pipeline/base.py
import os
import cv2
from os.path import join, dirname
from util.io import get_unique_output_path
class PipelineStep:
    def __init__(self, global_config, **params):
        self.global_config = global_config
        self.params = params
        self.verbose = True

    def apply(self, frame):
        raise NotImplementedError("Must be implemented in subclass")

    def save_output(self, output_root, frame,numbered_files=False):
        output_file = self.params.get("output_file",None)
        if output_file and self.global_config["save_step_images"]:
            try:
                if numbered_files:
                    out_path = get_unique_output_path(join(output_root,output_file))
                else:
                    out_path = join(output_root,output_file)
                os.makedirs(dirname(out_path), exist_ok=True)
                if self.verbose: print(f"[OUTPUT] Writing \'{out_path}\'")
                success = cv2.imwrite(out_path, frame)
                if not success:
                    print(f"[Warning] Failed to write output to: {output_file}")
            except Exception as e:
                print(f"[Warning] Exception while saving output to {output_file}: {e}")

    def __repr__(self):
            classname = self.__class__.__name__
            param_str = ", ".join(f"{k}={v!r}" for k, v in self.params.items())
            return f"[{classname.center(20)}][{param_str}]"