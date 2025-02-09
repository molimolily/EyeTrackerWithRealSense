import tkinter as tk
from PIL import Image, ImageTk

class RealSenseView:
    def __init__(self, title, info_text):
        self.win = tk.Tk()
        self.win.title(title)
        self.win.resizable(False, False)
        self.image_label = tk.Label(self.win)
        self.image_label.pack()
        
        self.info_frame = tk.Frame(self.win)
        self.info_frame.pack(fill=tk.X)
        
        self.info_label = tk.Label(self.info_frame, text=info_text, justify="left", anchor="w")
        self.info_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.fps_label = tk.Label(self.info_frame, justify="center", anchor="center")
        self.fps_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.eye_pos_label = tk.Label(self.info_frame, justify="right", anchor="e")
        self.eye_pos_label.pack(side=tk.LEFT, expand=True, fill=tk.X)

    def update(self, image, info_text, fps_text, eye_pos_text):
        im = Image.fromarray(image)
        imgtk = ImageTk.PhotoImage(image=im)
        self.image_label.imgtk = imgtk  # keep a reference
        self.image_label.configure(image=imgtk)
        self.info_label.config(text=info_text)
        self.fps_label.config(text=fps_text)
        self.eye_pos_label.config(text=eye_pos_text)

    def after(self, delay, callback):
        self.win.after(delay, callback)

    def mainloop(self):
        self.win.mainloop()

    def protocol(self, protocol_name, func):
        self.win.protocol(protocol_name, func)

    def destroy(self):
        self.win.destroy()
