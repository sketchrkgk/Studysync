import tkinter as tk
from tkinter import simpledialog, messagebox, colorchooser
import socket
import threading
import json, os, datetime, platform, subprocess, time, re, webbrowser, random, string

# -------------- CONFIG --------------
HOST = 'YOUR_LOCAL_IP'  # Replace with your Mac's IP address (e.g., "192.168.1.25")
PORT = 12345

USERDATA_FILE = "username_data.json"
ALL_USERNAMES_FILE = "all_usernames.json"
last_speaker = None

# Helper Functions
def load_user_data():
    return json.load(open(USERDATA_FILE, "r")) if os.path.exists(USERDATA_FILE) else {"username":"DesireL","last_changed":None,"name":""}

def save_user_data(data):
    json.dump(data, open(USERDATA_FILE, "w"))

def load_all_usernames():
    return json.load(open(ALL_USERNAMES_FILE, "r")) if os.path.exists(ALL_USERNAMES_FILE) else []

def save_all_usernames(lst):
    json.dump(lst, open(ALL_USERNAMES_FILE, "w"))

def can_change_username(iso):
    return True if not iso else (datetime.datetime.now() - datetime.datetime.fromisoformat(iso)).days >= 7

def username_unique(name):
    return name.lower() not in [u.lower() for u in load_all_usernames()]

def update_username_list(old, new):
    uu = load_all_usernames()
    uu = [u for u in uu if u.lower() != old.lower()]
    uu.append(new)
    save_all_usernames(uu)

def load_history(room):
    return open(f"history_{room}.txt","r",encoding="utf-8").read().splitlines() if os.path.exists(f"history_{room}.txt") else []

def save_history(room, line):
    with open(f"history_{room}.txt","a",encoding="utf-8") as f:
        f.write(line+"\n")

def generate_random_code(n=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

# Splash Screen
def show_splash_screen():
    sp = tk.Tk()
    sp.title("StudySync Loading")
    sp.geometry("400x150")
    sp.configure(bg="#f0f0f0")
    tk.Label(sp, text="Welcome to StudySync", font=("Arial",20),bg="#f0f0f0").pack(expand=True)
    tk.Label(sp, text="Creator: DesireL", font=("Arial",10), fg="gray",bg="#f0f0f0").pack(side="bottom", pady=10)
    sp.after(2000, lambda: (sp.destroy(), build_main_window()))
    sp.mainloop()

# Main App
def build_main_window():
    global window, sock, username_data, current_room, chat_box, entry_box, last_speaker, rooms, share_codes

    username_data = load_user_data()
    current_room = "Default"
    rooms = ["Default"]
    share_codes = {}

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((HOST, PORT))
    except Exception:
        messagebox.showerror("Error", f"Cannot connect to server at {HOST}:{PORT}")
        return

    window = tk.Tk()
    window.title("StudySync")
    window.geometry("900x600")
    window.protocol("WM_DELETE_WINDOW", lambda: (sock.close(), window.destroy()))

    # Profile Frame
    pf = tk.Frame(window, bg="#f0f0f0", width=250); pf.pack(side="left", fill="y")
    tk.Label(pf, text="Profile", font=("Arial",14,"bold"), bg="#f0f0f0").pack(pady=10)
    tk.Label(pf, text="Username:", bg="#f0f0f0").pack(anchor="w", padx=10)
    ul = tk.Label(pf, text=username_data["username"], font=("Arial",12), bg="#f0f0f0")
    ul.pack(anchor="w", padx=20, pady=(0,10))

    def change_user():
        if not can_change_username(username_data.get("last_changed")):
            cd = datetime.datetime.fromisoformat(username_data["last_changed"]) + datetime.timedelta(days=7)
            return messagebox.showinfo("Wait", f"Next change allowed on {cd.strftime('%Y-%m-%d')}")
        n = simpledialog.askstring("New Username","Enter ≥4 chars:")
        if not n or len(n)<4 or not username_unique(n):
            return messagebox.showerror("Invalid", "Name must be ≥4 chars and unique")
        old = username_data["username"]
        username_data.update({"username":n,"last_changed":datetime.datetime.now().isoformat()})
        save_user_data(username_data)
        update_username_list(old, n)
        ul.config(text=n)

    tk.Button(pf, text="Change Username", command=change_user).pack(pady=(0,20))
    tk.Label(pf, text="Name:", bg="#f0f0f0").pack(anchor="w", padx=10)
    ne = tk.Entry(pf); ne.pack(anchor="w", padx=20, fill="x", pady=(0,10)); ne.insert(0, username_data.get("name",""))
    tk.Button(pf, text="Save Name", command=lambda: (username_data.update({"name":ne.get()}), save_user_data(username_data), messagebox.showinfo("Saved","Name saved"))).pack(pady=(0,20))

    # Chatrooms Frame
    crf = tk.Frame(window, bg="#ddd", width=150); crf.pack(side="left", fill="y")
    tk.Label(crf,text="Chatrooms", font=("Arial",14,"bold"), bg="#ddd").pack(pady=10)
    crlf = tk.Frame(crf, bg="#ddd"); crlf.pack(fill="y", expand=True)

    def refresh_rooms():
        for w in crlf.winfo_children(): w.destroy()
        tk.Button(crlf, text="Join Chatroom", bg="#bbb", command=join_chatroom).pack(fill="x", pady=(0,5))
        for r in rooms:
            fr = tk.Frame(crlf, bg="#ddd"); fr.pack(fill="x", pady=2)
            tk.Button(fr, text=r, width=15, anchor="w", command=lambda r=r: switch_room(r)).pack(side="left")
            mb = tk.Menubutton(fr, text="⋮", relief="flat"); m = tk.Menu(mb, tearoff=0)
            m.add_command(label="Rename", command=lambda r=r: rename_room(r))
            m.add_command(label="Share", command=lambda r=r: share_room(r))
            m.add_command(label="Color", command=lambda r=r: customize_color(r))
            mb.config(menu=m); mb.pack(side="right")
        tk.Button(crf, text="+ Add", bg="#ccc", command=new_room).pack(pady=10)

    def new_room():
        n = simpledialog.askstring("Add Chatroom","Enter name:")
        if n and n not in rooms: rooms.append(n); refresh_rooms(); switch_room(n)

    def rename_room(r):
        n = simpledialog.askstring("Rename",f"Rename '{r}' to:")
        if n and n not in rooms:
            i = rooms.index(r); rooms[i] = n
            if r in share_codes: share_codes[n] = share_codes.pop(r)
            if os.path.exists(f"history_{r}.txt"): os.rename(f"history_{r}.txt", f"history_{n}.txt")
            refresh_rooms(); switch_room(n)

    def share_room(r):
        code = generate_random_code(); share_codes[r] = code
        messagebox.showinfo("Share Code", f"Invite code for '{r}':\n{code}")

    def join_chatroom():
        code = simpledialog.askstring("Join Chatroom","Enter invite code:")
        if not code: return
        for r,c in share_codes.items():
            if code.strip().upper() == c:
                if r not in rooms: rooms.append(r); refresh_rooms()
                switch_room(r); return
        messagebox.showerror("Invalid", "Wrong invite code")

    def customize_color(r):
        c = colorchooser.askcolor()[1]
        if c: chat_box.config(bg=c)

    # Main Chat Area
    mf = tk.Frame(window); mf.pack(side="left", expand=True, fill="both")
    chat_box = tk.Text(mf, state="disabled", wrap="word"); chat_box.pack(expand=True, fill="both", padx=10, pady=10)
    entry_box = tk.Entry(mf); entry_box.pack(fill="x", padx=10, pady=(0,10)); entry_box.focus()

    def insert_text_with_links(text):
        nonlocal_last = globals()
        nonlocal_last['last_speaker'] = last_speaker
        global last_speaker
        chat_box.config(state="normal")
        match = re.match(r"^(.+?): (.+)", text)
        if match:
            speaker, content = match.groups()
            indent = " "*(len(speaker)+2)
            u = re.search(r"\(([^)]+)\)", speaker)
            sp = u.group(1) if u else speaker
            if sp != last_speaker:
                chat_box.insert("end", f"{speaker}: ")
                last_speaker = sp
            else:
                chat_box.insert("end", indent)
            parts = re.split(r"(https?://\S+)", content)
            for i, p in enumerate(parts):
                if p.startswith("http"):
                    tag = f"link{time.time()}{i}"
                    chat_box.insert("end", p, tag)
                    chat_box.tag_config(tag, foreground="blue", underline=True)
                    chat_box.tag_bind(tag, "<Button-1>", lambda e, url=p: webbrowser.open(url))
                else:
                    chat_box.insert("end", p)
            chat_box.insert("end","\n")
        else:
            chat_box.insert("end", text+"\n")
        chat_box.config(state="disabled"); chat_box.see("end")

    def switch_room(r):
        global current_room, last_speaker
        current_room = r; last_speaker = None
        window.title(f"StudySync - {r}")
        chat_box.config(state="normal"); chat_box.delete("1.0","end")
        for line in load_history(r): insert_text_with_links(line)
        chat_box.config(state="disabled")

    def send_msg(evt=None):
        t = entry_box.get().strip()
        if not t: return
        dn = username_data.get("name","").strip()
        sender = f"{dn} ({username_data['username']})" if dn else username_data['username']
        msg = f"{sender}: {t}"
        try:
            sock.send(msg.encode()); save_history(current_room, msg); insert_text_with_links(msg)
        except:
            messagebox.showerror("Error","Failed to send message")
        entry_box.delete(0,"end")

    def recv_msg():
        while True:
            try:
                d = sock.recv(4096).decode()
                if not d: break
                save_history(current_room, d); insert_text_with_links(d)
            except:
                break

    entry_box.bind("<Return>", send_msg)
    threading.Thread(target=recv_msg, daemon=True).start()
    switch_room(current_room); refresh_rooms()
    window.mainloop()

if __name__ == "__main__":
    show_splash_screen()
