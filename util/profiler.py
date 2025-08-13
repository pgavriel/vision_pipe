# utils/profiler.py
import time
from collections import deque

class PipelineProfiler:
    def __init__(self, window_size=30, print_interval=10,desired_framerate=0):
        self.window_size = window_size
        self.print_interval = print_interval
        self.desired_framerate = desired_framerate
        self.step_times = {}  # step_name -> deque of recent times
        self.frame_times = deque(maxlen=window_size)
        self.frame_count = 0

    def start_frame(self):
        self._frame_start = time.perf_counter()

    def end_frame(self):
        total_time = time.perf_counter() - self._frame_start
        self.frame_times.append(total_time)
        self.frame_count += 1

        if self.frame_count % self.print_interval == 0:
            self._print_summary()

    def start_step(self, step_name):
        self._step_start = time.perf_counter()
        self._current_step = step_name

    def end_step(self):
        elapsed = time.perf_counter() - self._step_start
        dq = self.step_times.setdefault(self._current_step, deque(maxlen=self.window_size))
        dq.append(elapsed)

    def _moving_avg(self, dq):
        return sum(dq) / len(dq) if dq else 0.0

    def _print_summary(self):
        print_str = ""
        avg_frame_time = self._moving_avg(self.frame_times)
        fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        step_summaries = [
            f"{name}: {self._moving_avg(times)*1000:.2f} ms"
            for name, times in self.step_times.items()
        ]
        step_summary_str = " | ".join(step_summaries)

        warning = "[!]" if fps < self.desired_framerate else ""
        print_str += f"\n{warning}[Frames: {self.frame_count}] "
        print_str +=  f"Avg: {avg_frame_time*1000:.2f} ms/frame ({fps:.1f} FPS) | {step_summary_str}"

        print(print_str, end="\n", flush=True)
