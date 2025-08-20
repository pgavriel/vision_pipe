import cv2
import time

class Message:
    def __init__(self, text, duration=10, color=(0, 255, 255), size=1, position=(50, 50)):
        self.text = text
        self.duration = duration        # duration in frames
        self.color = color
        self.size = size
        self.position = position
        self.start_frame = 0            # set later by manager

class MessageManager:
    def __init__(self,verbose=True):
        self.messages = {}  # dict: name -> (Message, start_frame)
        self.frame_count = 0
        self.verbose = verbose

    def add_message(self, name, text, duration=25, color=(0, 255, 255), size=1, position=(10, 50)):
        """Add or overwrite a message with given name."""
        msg = Message(text, duration, color, size, position)
        msg.start_frame = self.frame_count
        self.messages[name] = msg
        if self.verbose:
            print(f"[{name}] {text}")

    def step(self):
        """Increment frame counter and remove expired messages."""
        self.frame_count += 1
        expired = []
        for name, msg in self.messages.items():
            if self.frame_count - msg.start_frame >= msg.duration:
                expired.append(name)
        for name in expired:
            del self.messages[name]

    def draw(self, frame, autostep=True):
        """Draw all active messages onto the given frame."""
        for msg in self.messages.values():
            cv2.putText(frame, msg.text, (msg.position[0],msg.position[1]+2),
                        cv2.FONT_HERSHEY_SIMPLEX, msg.size,
                        (0,0,0), 2, cv2.LINE_AA)
            cv2.putText(frame, msg.text, msg.position,
                        cv2.FONT_HERSHEY_SIMPLEX, msg.size,
                        msg.color, 2, cv2.LINE_AA)
        if autostep: self.step()
        return frame
