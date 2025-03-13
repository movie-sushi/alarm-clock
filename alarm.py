import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime, date
import os
from playsound import playsound
import threading
import json
from typing import Optional
import pystray
from pystray import MenuItem as item
from PIL import Image
from win10toast import ToastNotifier
toaster = ToastNotifier()

def on_quit_tray(icon, _):
    """
    Called when selecting 'Exit' from the tray.
    Stop the icon, then shut down the Tk app.
    """
    icon.stop()
    root.quit()

def show_main_window(icon, _):
    """
    Called when selecting 'Show' from the tray menu.
    Show (deiconify) the hidden Tk window.
    Then stop the icon so we don't have two event loops.
    """
    root.deiconify()
    icon.stop()

def run_tray():
    """
    The function to run pystray.Icon in its own event loop (blocking).
    """
    # You need an icon image (PNG). Make or use a small 16x16 or 32x32 PNG.
    image = Image.open("assets/alarm.png")
    menu = (item('Show', show_main_window), item('Exit', on_quit_tray))
    icon = pystray.Icon("AlarmApp", image, "My Alarms", menu)
    icon.run()  # blocking call

def minimize_to_tray():
    """
    Hide the Tk window (so it 'goes to tray').
    Then run the tray icon in a separate thread.
    """
    root.withdraw()  # hide the window
    threading.Thread(target=run_tray, daemon=True).start()

class Alarm:
    """
    Stores:
      - name (str)
      - hour (int)
      - minute (int)
      - days (list of bools, for Mon..Sun)
      - sound_path (str)
      - last_triggered_date (date or None)
      - enabled (bool)
    """
    def __init__(self, name, hour, minute, days, sound_path, 
                 last_triggered_date: Optional[date] = None, enabled=True):
        self.name = name
        self.hour = hour
        self.minute = minute
        self.days = days
        self.sound_path = sound_path
        self.last_triggered_date = last_triggered_date  # a date object or None
        self.enabled = enabled

    def to_dict(self):
        """
        Convert Alarm to a dictionary suitable for JSON serialization.
        We'll store last_triggered_date as an ISO string if it's not None.
        """
        return {
            "name": self.name,
            "hour": self.hour,
            "minute": self.minute,
            "days": self.days,
            "sound_path": self.sound_path,
            "last_triggered_date": self.last_triggered_date.isoformat() if self.last_triggered_date else None,
            "enabled": self.enabled
        }

    @staticmethod
    def from_dict(data: dict):
        """
        Create an Alarm from a dict, converting the ISO date string back to a date object if present.
        """
        last_trigger_str = data.get("last_triggered_date")
        if last_trigger_str:
            # parse the ISO date string
            last_triggered_date = date.fromisoformat(last_trigger_str)
        else:
            last_triggered_date = None

        return Alarm(
            name=data["name"],
            hour=data["hour"],
            minute=data["minute"],
            days=data["days"],
            sound_path=data["sound_path"],
            last_triggered_date=last_triggered_date,
            enabled=data["enabled"]
        )

alarms = []  # will hold Alarm objects in memory

SAVE_FILE = "alarms.json"  # Name/path of the JSON file for storing alarms

def play_sound(sound_path):
    def _worker():
        playsound(sound_path)
    threading.Thread(target=_worker, daemon=True).start()

def check_alarms():
    """
    Periodically checks each alarm:
      - Is it enabled?
      - Do the hour/minute match?
      - Is today (weekday) active?
      - Have we not triggered it yet today?
    If so, play the sound and mark it as triggered for today.
    """
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    current_weekday = now.weekday()  # Monday=0 .. Sunday=6
    today_date = date.today()

    for alarm in alarms:
        if alarm.enabled:
            if alarm.hour == current_hour and alarm.minute == current_minute:
                if alarm.days[current_weekday]:
                    if alarm.last_triggered_date != today_date:
                        alarm.last_triggered_date = today_date
                        play_sound(alarm.sound_path)
                        toaster.show_toast("Alarm", f"Time to wake up! {alarm.name}",
                            icon_path='assets/alarm.ico', duration=5, threaded=True)
    # Check again in 10 seconds
    root.after(10_000, check_alarms)

def save_alarms_to_file():
    """
    Serializes the alarms list to a JSON file so we can load it next time the app runs.
    """
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        data = [alarm.to_dict() for alarm in alarms]
        json.dump(data, f, indent=2)

def load_alarms_from_file():
    """
    Reads any existing JSON file and restores the alarms into the app.
    If no file, or it's invalid, we skip loading.
    """
    if not os.path.exists(SAVE_FILE):
        return  # Nothing to load

    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # data should be a list of dicts, each representing an Alarm
            for alarm_dict in data:
                alarm = Alarm.from_dict(alarm_dict)
                alarms.append(alarm)
    except Exception as e:
        print("Error loading alarms:", e)

def refresh_alarm_list():
    """
    Clears and re-populates the Treeview to reflect current `alarms`.
    """
    alarm_tree.delete(*alarm_tree.get_children())

    for index, alarm in enumerate(alarms):
        # Create a short day string, e.g. "M T W Th F - -"
        day_labels = ["M", "T", "W", "Th", "F", "Sa", "Su"]
        active_days_str = []
        for i, active in enumerate(alarm.days):
            active_days_str.append(day_labels[i] if active else "-")
        day_string = " ".join(active_days_str)

        enabled_str = "Yes" if alarm.enabled else "No"
        time_str = f"{alarm.hour:02d}:{alarm.minute:02d}"

        alarm_tree.insert(
            "",
            "end",
            iid=str(index),
            values=(alarm.name, time_str, day_string, enabled_str)
        )

def add_alarm():
    name = name_entry.get().strip()
    if not name:
        status_label.config(text="Please provide an alarm name.")
        return

    try:
        hour = int(hour_entry.get())
        minute = int(minute_entry.get())
    except ValueError:
        status_label.config(text="Hour/Minute must be numeric.")
        return

    if not (0 <= hour < 24):
        status_label.config(text="Hour must be 0-23.")
        return
    if not (0 <= minute < 60):
        status_label.config(text="Minute must be 0-59.")
        return

    # Gather day checkboxes
    selected_days = [
        mon_var.get(),
        tue_var.get(),
        wed_var.get(),
        thu_var.get(),
        fri_var.get(),
        sat_var.get(),
        sun_var.get()
    ]

    sound_path = sound_path_entry.get()
    if not os.path.isfile(sound_path):
        status_label.config(text="Invalid sound file path.")
        return

    new_alarm = Alarm(name, hour, minute, selected_days, sound_path)
    alarms.append(new_alarm)

    # Save and refresh
    save_alarms_to_file()
    refresh_alarm_list()

    status_label.config(text=f"Alarm '{name}' added.")
    # Clear inputs
    name_entry.delete(0, tk.END)
    hour_entry.delete(0, tk.END)
    minute_entry.delete(0, tk.END)
    sound_path_entry.delete(0, tk.END)
    mon_var.set(False)
    tue_var.set(False)
    wed_var.set(False)
    thu_var.set(False)
    fri_var.set(False)
    sat_var.set(False)
    sun_var.set(False)

def browse_sound():
    file_path = filedialog.askopenfilename(
        title="Select Alarm Sound",
        filetypes=[("Audio Files", "*.wav *.mp3 *.ogg *.flac *.aac *.m4a *.wma"), ("All Files", "*.*")]
    )
    if file_path:
        sound_path_entry.delete(0, tk.END)
        sound_path_entry.insert(0, file_path)

def toggle_alarm():
    """
    Enables/Disables the selected alarm in the Treeview.
    """
    selected = alarm_tree.selection()
    if not selected:
        messagebox.showinfo("No Selection", "Please select an alarm to enable/disable.")
        return

    idx = int(selected[0])
    alarms[idx].enabled = not alarms[idx].enabled

    save_alarms_to_file()
    refresh_alarm_list()

def delete_alarm():
    """
    Removes the selected alarm from the list and file.
    """
    selected = alarm_tree.selection()
    if not selected:
        messagebox.showinfo("No Selection", "Please select an alarm to delete.")
        return

    idx = int(selected[0])
    alarm_name = alarms[idx].name
    confirm = messagebox.askyesno("Confirm Delete", f"Delete alarm '{alarm_name}'?")
    if confirm:
        alarms.pop(idx)
        save_alarms_to_file()
        refresh_alarm_list()
        status_label.config(text=f"Alarm '{alarm_name}' deleted.")

# ----- GUI SETUP -----
root = tk.Tk()
root.title("Alarm Clock")

main_frame = tk.Frame(root)
main_frame.pack(padx=10, pady=10)

# Alarm Name
tk.Label(main_frame, text="Name:").grid(row=0, column=0, sticky="e")
name_entry = tk.Entry(main_frame, width=15)
name_entry.grid(row=0, column=1, padx=5)

# Hour / Minute
tk.Label(main_frame, text="Hour (0-23):").grid(row=0, column=2, sticky="e")
hour_entry = tk.Entry(main_frame, width=5)
hour_entry.grid(row=0, column=3, padx=5)

tk.Label(main_frame, text="Minute (0-59):").grid(row=0, column=4, sticky="e")
minute_entry = tk.Entry(main_frame, width=5)
minute_entry.grid(row=0, column=5, padx=5)

# Days checkboxes
days_frame = tk.Frame(main_frame)
days_frame.grid(row=1, column=0, columnspan=6, pady=5)

mon_var = tk.BooleanVar()
tue_var = tk.BooleanVar()
wed_var = tk.BooleanVar()
thu_var = tk.BooleanVar()
fri_var = tk.BooleanVar()
sat_var = tk.BooleanVar()
sun_var = tk.BooleanVar()

tk.Checkbutton(days_frame, text="Mon", variable=mon_var).pack(side=tk.LEFT)
tk.Checkbutton(days_frame, text="Tue", variable=tue_var).pack(side=tk.LEFT)
tk.Checkbutton(days_frame, text="Wed", variable=wed_var).pack(side=tk.LEFT)
tk.Checkbutton(days_frame, text="Thu", variable=thu_var).pack(side=tk.LEFT)
tk.Checkbutton(days_frame, text="Fri", variable=fri_var).pack(side=tk.LEFT)
tk.Checkbutton(days_frame, text="Sat", variable=sat_var).pack(side=tk.LEFT)
tk.Checkbutton(days_frame, text="Sun", variable=sun_var).pack(side=tk.LEFT)

# Sound path
tk.Label(main_frame, text="Sound File:").grid(row=2, column=0, sticky="e")
sound_path_entry = tk.Entry(main_frame, width=30)
sound_path_entry.grid(row=2, column=1, columnspan=4, padx=5, sticky="w")
browse_button = tk.Button(main_frame, text="Browse...", command=browse_sound)
browse_button.grid(row=2, column=5, padx=5, sticky="w")

# Add alarm button
add_button = tk.Button(main_frame, text="Add Alarm", command=add_alarm)
add_button.grid(row=3, column=0, columnspan=6, pady=5)

# Status label
status_label = tk.Label(main_frame, text="", fg="blue")
status_label.grid(row=4, column=0, columnspan=6)

# Treeview for listing alarms
tree_frame = tk.Frame(root)
tree_frame.pack(padx=10, pady=10, fill="x")

columns = ("name", "time", "days", "enabled")
alarm_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=6)
alarm_tree.heading("name", text="Name")
alarm_tree.heading("time", text="Time")
alarm_tree.heading("days", text="Days")
alarm_tree.heading("enabled", text="Enabled")

alarm_tree.column("name", width=100)
alarm_tree.column("time", width=60)
alarm_tree.column("days", width=120)
alarm_tree.column("enabled", width=60)

alarm_tree.pack(side=tk.LEFT, fill="x", expand=True)
scrollbar = tk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=alarm_tree.yview)
alarm_tree.configure(yscroll=scrollbar.set)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Buttons to manage selected alarm
manage_frame = tk.Frame(root)
manage_frame.pack(pady=5)

enable_button = tk.Button(manage_frame, text="Enable/Disable Alarm", command=toggle_alarm)
enable_button.pack(side=tk.LEFT, padx=5)

delete_button = tk.Button(manage_frame, text="Delete Alarm", command=delete_alarm)
delete_button.pack(side=tk.LEFT, padx=5)
btn_tray = tk.Button(root, text="Minimize to System Tray", command=minimize_to_tray)
btn_tray.pack(padx=20, pady=20)

# ----- LOAD ALARMS (if any) -----
load_alarms_from_file()
refresh_alarm_list()

# Start checking
root.after(1000, check_alarms)
root.mainloop()
