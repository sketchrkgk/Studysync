import socket
import threading
import os

clients = []
usernames = {}

def broadcast(message, sender_conn):
    for client in clients:
        if client != sender_conn:
            try:
                client.send(message.encode())
            except:
                client.close()
                if client in clients:
                    clients.remove(client)

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
