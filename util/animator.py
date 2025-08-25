import math
import random

class Animator:
    def __init__(self, config):
        self.mode = config.get("mode", "static")
        self.points = config.get("points", [0])
        self.speed = config.get("speed", 1)
        self.interpolation = config.get("interpolation", "linear")

        self.current_index = 0
        self.t = 0.0  # progress between waypoints
        self.value = self.points[0] if self.points else 0

        # Random-specific setup
        self.bounds = config.get("bounds", [(0.1, 0.1), (0.9, 0.9)])
        self.min_distance = config.get("min_distance", 0.2)

    def step(self):
        if self.mode == "static":
            return self.value

        elif self.mode == "waypoints":
            self.t += 1.0 / max(1, self.speed)
            if self.t >= 1.0:
                self.t = 0.0
                self.current_index = (self.current_index + 1) % len(self.points)

            p1 = self.points[self.current_index]
            p2 = self.points[(self.current_index + 1) % len(self.points)]
            return self._interpolate(p1, p2, self.t)

        elif self.mode == "random":
            self.t += 1.0 / max(1, self.speed)
            if self.t >= 1.0:
                self.t = 0.0
                self.points[0] = self.points[1]  # shift target -> current
                self.points[1] = self._random_point()

            p1, p2 = self.points
            return self._interpolate(p1, p2, self.t)

    def _interpolate(self, a, b, t):
        if self.interpolation == "sine":
            t = (1 - math.cos(t * math.pi)) / 2
        if isinstance(a, (list, tuple)):
            return type(a)(ai + (bi - ai) * t for ai, bi in zip(a, b))
        else:
            return a + (b - a) * t

    def _random_point(self):
        while True:
            x = random.uniform(self.bounds[0][0], self.bounds[1][0])
            y = random.uniform(self.bounds[0][1], self.bounds[1][1])
            if self._distance((x, y), self.points[-1]) >= self.min_distance:
                return (x, y)

    def _distance(self, a, b):
        return math.dist(a, b)


# class Layer:
#     def __init__(self, config):
#         self.paused = config.get("paused", False)
#         self.params = {}

#         for k, v in config.items():
#             if isinstance(v, dict) and "mode" in v:  # animator config
#                 self.params[k] = Animator(v)
#             else:
#                 self.params[k] = v

#     def draw(self, canvas):
#         # update animated params
#         if not self.paused:
#             for k, v in self.params.items():
#                 if isinstance(v, Animator):
#                     self.params[k] = v.step()

#         # At this point, self.params has the *actual values* for this frame
#         # Example: self.params["position"], self.params["scale"], etc.
#         pass  # replace with actual drawing
