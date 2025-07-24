
import tkinter as tk
from tkinter import simpledialog, messagebox, colorchooser
import socket
import threading
import json
import os
import datetime
import platform
import subprocess
import time
import re
import webbrowser

# -------------------- CONFIG --------------------
HOST = '127.0.0.1'
PORT = 12345

USERDATA_FILE = "username_data.json"
ALL_USERNAMES_FILE = "all_usernames.json"
last_speaker = None  # tracks previous message sender

# ------------------ HELPER FUNCTIONS ------------------

def load_user_data():
    if os.path.exists(USERDATA_FILE):
        return json.load(open(USERDATA_FILE, "r"))
    return {"username": "DesireL", "last_changed": None, "name": ""}

def save_user_data(data):
    json.dump(data, open(USERDATA_FILE, "w"))

def load_all_usernames():
    return json.load(open(ALL_USERNAMES_FILE, "r")) if os.path.exists(ALL_USERNAMES_FILE) else []

def save_all_usernames(lst):
    json.dump(lst, open(ALL_USERNAMES_FILE, "w"))

def can_change_username(iso):
    if not iso:
        return True
    return (datetime.datetime.now() - datetime.datetime.fromisoformat(iso)).days >= 7

def username_unique(name):
    return name.lower() not in [u.lower() for u in load_all_usernames()]

def update_username_list(old, new):
    lst = load_all_usernames()
    lst = [u for u in lst if u.lower() != old.lower()]
    lst.append(new)
    save_all_usernames(lst)

def open_in_explorer(path):
    if platform.system() == "Darwin":
        subprocess.run(["open", "-R", path])
    elif platform.system() == "Windows":
        subprocess.run(["explorer", "/select,", path])
    else:
        messagebox.showinfo("File is here", path)

def load_history(room):
    f = f"history_{room}.txt"
    return open(f, "r", encoding="utf-8").read().splitlines() if os.path.exists(f) else []

def save_history(room, line):
    with open(f"history_{room}.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")

# -------------------- SPLASH SCREEN --------------------

def show_splash_screen():
    splash = tk.Tk()
    splash.title("StudySync Loading")
    splash.geometry("400x150")
    splash.configure(bg="#f0f0f0")

    label = tk.Label(splash, text="Welcome to StudySync", font=("Arial", 20), bg="#f0f0f0")
    label.pack(expand=True)

    credits = tk.Label(splash, text="Creator: DesireL", font=("Arial", 10), fg="gray", bg="#f0f0f0")
    credits.pack(side="bottom", pady=10)

    splash.after(2500, lambda: start_main(splash))
    splash.mainloop()

# --------------------- MAIN APP ---------------------

def start_main(splash_window):
    splash_window.destroy()
    build_main_window()

def build_main_window():
    global window, sock, username_data, current_room, chat_box, entry_box, last_speaker

    last_speaker = None
    username_data = load_user_data()
    current_room = "Default"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except Exception:
        messagebox.showerror("Error", "Cannot connect to server")
        return

    window = tk.Tk()
    window.title("StudySync")
    window.geometry("900x600")

    def on_close():
        try:
            sock.close()
        except:
            pass
        window.destroy()
    window.protocol("WM_DELETE_WINDOW", on_close)

    # Profile Panel
    pf = tk.Frame(window, width=250, bg="#f0f0f0")
    pf.pack(side="left", fill="y")

    tk.Label(pf, text="Profile", font=("Arial", 14, "bold"), bg="#f0f0f0").pack(pady=10)

    tk.Label(pf, text="Username:", bg="#f0f0f0").pack(anchor="w", padx=10)
    ul = tk.Label(pf, text=username_data["username"], font=("Arial", 12), bg="#f0f0f0")
    ul.pack(anchor="w", padx=20, pady=(0, 10))

    def change_user():
        if not can_change_username(username_data["last_changed"]):
            cd = datetime.datetime.fromisoformat(username_data["last_changed"]) + datetime.timedelta(days=7)
            return messagebox.showinfo("Wait", f"Next username change allowed on {cd.strftime('%Y-%m-%d')}")
        n = simpledialog.askstring("New username", "Enter new username (≥4 chars):")
        if not n:
            return
        if len(n) < 4:
            return messagebox.showerror("Invalid", "Username must be at least 4 characters")
        if not username_unique(n):
            return messagebox.showerror("Invalid", "Username already taken")
        old = username_data["username"]
        username_data.update({"username": n, "last_changed": datetime.datetime.now().isoformat()})
        save_user_data(username_data)
        update_username_list(old, n)
        ul.config(text=n)

    tk.Button(pf, text="Change Username", command=change_user).pack(pady=(0, 20))

    tk.Label(pf, text="Name:", bg="#f0f0f0").pack(anchor="w", padx=10)
    ne = tk.Entry(pf)
    ne.pack(anchor="w", padx=20, fill="x", pady=(0, 10))
    ne.insert(0, username_data.get("name", ""))

    def save_name():
        username_data.update({"name": ne.get()})
        save_user_data(username_data)
        messagebox.showinfo("Saved", "Name saved")

    tk.Button(pf, text="Save Name", command=save_name).pack(pady=(0, 20))

    # Chatrooms Panel
    crf = tk.Frame(window, width=150, bg="#ddd")
    crf.pack(side="left", fill="y")

    tk.Label(crf, text="Chatrooms", font=("Arial", 14, "bold"), bg="#ddd").pack(pady=10)

    crlf = tk.Frame(crf, bg="#ddd")
    crlf.pack(fill="y", expand=True)

    rooms = ["Default"]

    def refresh_rooms():
        for w in crlf.winfo_children():
            w.destroy()
        for r in rooms:
            fr = tk.Frame(crlf, bg="#ddd")
            fr.pack(fill="x", pady=2)

            def switchroom_callback(room=r):
                switch_room(room)

            b = tk.Button(fr, text=r, width=15, anchor="w", command=switchroom_callback)
            b.pack(side="left")

            mb = tk.Menubutton(fr, text="⋮", relief="flat")
            m = tk.Menu(mb, tearoff=0)
            m.add_command(label="Rename", command=lambda room=r: rename_room(room))
            m.add_command(label="Share", command=lambda room=r: share_room(room))
            m.add_command(label="Customize Color", command=lambda room=r: customize_color(room))
            mb.config(menu=m)
            mb.pack(side="right")

        tk.Button(crf, text="+ Add", bg="#ccc", command=new_room).pack(pady=10)

    def new_room():
        n = simpledialog.askstring("Chatroom", "Enter new chatroom name:")
        if n and n not in rooms:
            rooms.append(n)
            refresh_rooms()
            switch_room(n)

    def rename_room(r):
        n = simpledialog.askstring("Rename Chatroom", f"Rename '{r}' to:")
        if n and n not in rooms:
            i = rooms.index(r)
            rooms[i] = n
            if os.path.exists(f"history_{r}.txt"):
                os.rename(f"history_{r}.txt", f"history_{n}.txt")
            refresh_rooms()
            switch_room(n)

    def share_room(r):
        p = os.path.abspath(f"history_{r}.txt")
        if os.path.exists(p):
            open_in_explorer(p)
        else:
            messagebox.showinfo("Share", "No history file found to share.")

    def customize_color(r):
        c = colorchooser.askcolor()[1]
        if c:
            chat_box.config(bg=c)

    # Main Chat Area
    mf = tk.Frame(window)
    mf.pack(side="left", fill="both", expand=True)

    chat_box = tk.Text(mf, state="disabled", wrap="word")
    chat_box.pack(fill="both", expand=True, padx=10, pady=10)

    entry_box = tk.Entry(mf)
    entry_box.pack(fill="x", padx=10, pady=(0, 10))
    entry_box.focus()

    def insert_text_with_links(text):
        global last_speaker
        chat_box.config(state="normal")
        match = re.match(r"^(.+?): (.+)", text)
        if match:
            speaker, content = match.groups()
            indent = " " * (len(speaker) + 2)
            username_in_brackets = re.search(r"\(([^)]+)\)", speaker)
            username_for_group = username_in_brackets.group(1) if username_in_brackets else speaker
            if username_for_group != last_speaker:
                chat_box.insert(tk.END, f"{speaker}: ")
                last_speaker = username_for_group
            else:
                chat_box.insert(tk.END, indent)
            parts = re.split(r"(https?://\S+)", content)
            for i, part in enumerate(parts):
                if part.startswith("http"):
                    tag = f"link{time.time()}{i}"
                    chat_box.insert(tk.END, part, tag)
                    chat_box.tag_config(tag, foreground="blue", underline=True)
                    chat_box.tag_bind(tag, "<Button-1>", lambda e, url=part: webbrowser.open(url))
                else:
                    chat_box.insert(tk.END, part)
            chat_box.insert(tk.END, "\n")
        else:
            chat_box.insert(tk.END, text + "\n")
        chat_box.config(state="disabled")
        chat_box.see(tk.END)

    def switch_room(r):
        global current_room, last_speaker
        current_room = r
        last_speaker = None
        window.title(f"StudySync - {r}")
        chat_box.config(state="normal")
        chat_box.delete("1.0", "end")
        for line in load_history(r):
            insert_text_with_links(line)
        chat_box.config(state="disabled")

    def send_msg(event=None):
        txt = entry_box.get().strip()
        if not txt:
            return
        display_name = username_data.get("name", "").strip()
        sender_label = f"{display_name} ({username_data['username']})" if display_name else username_data['username']
        msg = f"{sender_label}: {txt}"
        try:
            sock.send(msg.encode())
            save_history(current_room, msg)
            insert_text_with_links(msg)
        except:
            messagebox.showerror("Error", "Failed to send message")
        entry_box.delete(0, "end")

    def recv():
        while True:
            try:
                data = sock.recv(1024).decode()
                if not data:
                    break
                save_history(current_room, data)
                insert_text_with_links(data)
            except:
                break

    entry_box.bind("<Return>", send_msg)

    switch_room(current_room)
    refresh_rooms()

    threading.Thread(target=recv, daemon=True).start()

    window.mainloop()

if __name__ == "__main__":
    show_splash_screen()
