from pythonosc import udp_client

class OSCSender:
    def __init__(self, ip, port, right_addr="/eye/right", left_addr="/eye/left", center_addr="/eye/center",
                 right_enable=True, left_enable=True, center_enable=True):
        self.ip = ip
        self.port = port
        self.right_addr = right_addr
        self.left_addr = left_addr
        self.center_addr = center_addr
        self.right_enable = right_enable
        self.left_enable = left_enable
        self.center_enable = center_enable
        try:
            self.client = udp_client.SimpleUDPClient(self.ip, self.port)
        except Exception as e:
            print("Error creating OSC client:", e)
            self.client = None

    def send(self, eye_pos):
        if self.client is not None:
            if eye_pos is not None:
                if self.right_enable:
                    self.client.send_message(self.right_addr, eye_pos[0])
                if self.left_enable:
                    self.client.send_message(self.left_addr, eye_pos[1])
                if self.center_enable:
                    self.client.send_message(self.center_addr, [(eye_pos[0][i] + eye_pos[1][i]) / 2 for i in range(3)])