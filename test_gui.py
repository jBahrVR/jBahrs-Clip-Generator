import sys
import os
import app
from PIL import Image

def take_screenshot():
    os.system("scrot tmp/settings.png")

a = app.ClipGenApp()
a.show_settings_frame()
a.geometry("1100x1200")
a.update()
a.settings_frame._parent_canvas.yview_moveto(1.0) # scroll to bottom
a.after(2000, take_screenshot)
a.after(3000, a.destroy)
a.mainloop()
