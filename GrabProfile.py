import os
import string
import requests
from io import BytesIO
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk

# Your Steam Web API key here
API_KEY = "API_KEY_HERE"

# Standard Steam userdata folder relative path on each drive letter
STEAM_FOLDER_SUBPATH = r"Program Files (x86)\Steam\userdata"

# Color theme constants
BG_COLOR = "#171C25"
FG_COLOR = "#FFFFFF"

# Converts Steam folder numeric ID (Account ID) to 64-bit SteamID required by Steam Web API
def to_steam64(account_id):
    return str(int(account_id) + 76561197960265728)

# Query Steam Web API for profile name and avatar by SteamID64
def get_profile_info(steam_id64):
    url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={API_KEY}&steamids={steam_id64}"
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        players = data.get('response', {}).get('players', [])
        if not players:
            return None
        p = players[0]
        return {
            'name': p.get('personaname'),
            'avatar': p.get('avatarfull')
        }
    except Exception as e:
        print(f"Error fetching profile for SteamID {steam_id64}: {e}")
        return None

# Finds all Steam userdata directories by scanning every drive letter for standard Steam path
def find_userdata_paths():
    drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
    paths = []
    for drive in drives:
        userdata_path = os.path.join(drive, STEAM_FOLDER_SUBPATH)
        if os.path.isdir(userdata_path):
            paths.append(userdata_path)
    return paths

# Returns list of all numeric profile folder names inside userdata path
def list_profiles(userdata_path):
    try:
        return [f for f in os.listdir(userdata_path)
                if os.path.isdir(os.path.join(userdata_path, f)) and f.isdigit()]
    except Exception:
        return []

# Main GUI application class for displaying selectable Steam profiles
class ProfileSelector(tk.Tk):
    def __init__(self, profiles):
        super().__init__()
        self.title("Select Steam Profile")
        self.configure(bg=BG_COLOR)
        self.selected_profile = None
        self.avatar_cache = []  # Stores references to images to prevent garbage collection

        # Create scrollable canvas and attach vertical scrollbar
        canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.profile_frame = tk.Frame(canvas, bg=BG_COLOR)

        # Update scrollable region when profile_frame changes size
        self.profile_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Embed profile_frame in canvas
        canvas.create_window((0, 0), window=self.profile_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack widgets
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Add profiles as rows to scroll frame
        for i, profile in enumerate(profiles):
            self.add_profile_row(i, profile)

        # Add bottom padding frame equal to top padding for visual balance (~60px)
        spacer = tk.Frame(self.profile_frame, height=60, bg=BG_COLOR)
        spacer.pack()

        # Calculate window size based on profile count, max 5 profiles tall
        max_visible_profiles = 5
        approx_row_height = 90  # Estimated height per profile row, include padding
        num_profiles = len(profiles)

        rows_to_show = min(max_visible_profiles, num_profiles)
        window_height = rows_to_show * approx_row_height
        window_width = 500

        # Calculate center screen position
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        # Set window size and position; disable resizing and maximizing
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(window_width, approx_row_height * 1)  # allow minimum height of one profile
        self.resizable(False, False)  # disables maximize and resizing

    # Adds one profile display row consisting of avatar and profile name
    def add_profile_row(self, index, profile):
        frame = tk.Frame(self.profile_frame, bg=BG_COLOR, borderwidth=0, highlightthickness=0)
        frame.pack(fill='x', padx=12, pady=12)

        # Fetch and resize avatar image; use blank image on failure
        try:
            response = requests.get(profile['avatar'], timeout=8)
            image = Image.open(BytesIO(response.content)).resize((64, 64), Image.Resampling.LANCZOS)
            img = ImageTk.PhotoImage(image)
        except Exception as e:
            print(f"Avatar load failed: {e}")
            img = tk.PhotoImage(width=64, height=64)
        self.avatar_cache.append(img)  # prevent GC

        avatar_label = tk.Label(frame, image=img, bg=BG_COLOR, borderwidth=0)
        avatar_label.pack(side='left')

        name_label = tk.Label(
            frame, text=profile['name'],
            font=("Segoe UI", 18, "bold"),
            fg=FG_COLOR, bg=BG_COLOR, height=2, anchor="w"
        )
        name_label.pack(side='left', padx=18, fill='y')

        # Event handler for clicking profile row
        def on_select(event=None):
            self.selected_profile = profile['path']
            self.destroy()

        # Bind clicks on all relevant parts of the row
        frame.bind("<Button-1>", on_select)
        avatar_label.bind("<Button-1>", on_select)
        name_label.bind("<Button-1>", on_select)

# Main application flow
def main():
    userdata_paths = find_userdata_paths()
    all_profiles = []
    # For each Steam userdata folder, add profiles found with API info
    for path in userdata_paths:
        profile_ids = list_profiles(path)
        for pid in profile_ids:
            steam_id64 = to_steam64(pid)
            info = get_profile_info(steam_id64)
            if info:
                info['path'] = os.path.join(path, pid)
                all_profiles.append(info)

    if not all_profiles:
        print("No Steam profiles found")
        return

    # Show profile selector GUI
    app = ProfileSelector(all_profiles)
    app.mainloop()

    # Output final selection
    if app.selected_profile:
        print(app.selected_profile)
    else:
        print("No profile selected.")

if __name__ == "__main__":
    main()
