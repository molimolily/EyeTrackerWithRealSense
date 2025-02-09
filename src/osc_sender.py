from pythonosc import udp_client
FILTERED_EYE_POS1 = "/eye/map_center"
FILTERED_EYE_POS2 = "/eye/kalman_center"

class OSCSender:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        try:
            self.client = udp_client.SimpleUDPClient(self.ip, self.port)
        except Exception as e:
            print("Error creating OSC client:", e)
            self.client = None

    def send(self, eye_pos, filtered_eye_pos1=None, filtered_eye_pos2=None):
        if self.client is not None:
            if eye_pos is not None:
                self.client.send_message("/eye/right", eye_pos[0])
                self.client.send_message("/eye/left", eye_pos[1])
                self.client.send_message("/eye/center", [(eye_pos[0][i] + eye_pos[1][i]) / 2 for i in range(3)])
                if filtered_eye_pos1 is not None:
                    self.client.send_message(FILTERED_EYE_POS1, [(filtered_eye_pos1[0][i] + filtered_eye_pos1[1][i]) / 2 for i in range(3)])
                if filtered_eye_pos2 is not None:
                    self.client.send_message(FILTERED_EYE_POS2, [(filtered_eye_pos2[0][i] + filtered_eye_pos2[1][i]) / 2 for i in range(3)])