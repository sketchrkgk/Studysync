clients = []
usernames = {}

def handle_client(conn, addr):
    print(f"[+] Connected: {addr}")
    
    # First receive username
    try:
        username = conn.recv(1024).decode()
        usernames[conn] = username
        broadcast(f"*** {username} joined the chat ***", conn)
    except:
        conn.close()
        return

    while True:
        try:
            msg = conn.recv(1024).decode()
            if not msg:
                break
            full_msg = f"{usernames[conn]}: {msg}"
            broadcast(full_msg, conn)
        except:
            break

    # Client disconnected
    print(f"[-] {usernames.get(conn, 'Unknown')} disconnected")
    broadcast(f"*** {usernames.get(conn, 'Unknown')} left the chat ***", conn)
    clients.remove(conn)
    usernames.pop(conn, None)
    conn.close()

