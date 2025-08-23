from obswebsocket import obsws, requests

class OBSController:
    def __init__(self, host="localhost", port=4455, password=""):
        self.ws = obsws(host, port, password)
        self.connected = False

    def connect(self):
        if not self.connected:
            self.ws.connect()
            self.connected = True
            print("Connected to OBS WebSocket")

    def disconnect(self):
        if self.connected:
            self.ws.disconnect()
            self.connected = False
            print("Disconnected from OBS WebSocket")

    def start_recording(self):
        self.connect()
        self.ws.call(requests.StartRecord())
        print("Recording started")

    def stop_recording(self):
        self.connect()
        self.ws.call(requests.StopRecord())
        print("Recording stopped")

    def toggle_recording(self):
        self.connect()
        self.ws.call(requests.ToggleRecord())
        print("Toggled recording")

    def get_recording_status(self):
        self.connect()
        result = self.ws.call(requests.GetRecordStatus())
        return {
            "isRecording": result.getIsRecording(),
            "isPaused": result.getIsRecordingPaused()
        }
