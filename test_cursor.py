import customtkinter as ctk

app = ctk.CTk()

cb = ctk.CTkCheckBox(app, text="Test Checkbox", cursor="hand2")
cb.pack()

sw = ctk.CTkSwitch(app, text="Test Switch", cursor="hand2")
sw.pack()

app.update()
print("Success")
