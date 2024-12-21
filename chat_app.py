import tkinter as tk
from tkinter import messagebox
import sqlite3
import threading
import websockets
import asyncio

# --------------------- BACKEND ---------------------

# Initialize the Database
def init_db():
    conn = sqlite3.connect("chat_app.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, mobile TEXT)''')
    conn.commit()
    conn.close()

# User Registration
def register_user_backend(username, password, mobile):
    try:
        conn = sqlite3.connect("chat_app.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, mobile) VALUES (?, ?, ?)", (username, password, mobile))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

# User Authentication
def authenticate_user(username, password):
    conn = sqlite3.connect("chat_app.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = c.fetchone()
    conn.close()
    return user is not None

# WebSocket Server
connected_clients = {}

async def server_handler(websocket, path):
    username = await websocket.recv()
    connected_clients[username] = websocket
    try:
        async for message in websocket:
            for client in connected_clients.values():
                if client != websocket:
                    await client.send(message)
    except:
        pass
    finally:
        del connected_clients[username]

def start_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = websockets.serve(server_handler, "localhost", 8765)
    loop.run_until_complete(server)
    loop.run_forever()

# --------------------- FRONTEND ---------------------

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Real-Time Chat Application")
        self.root.geometry("400x550")
        self.root.configure(bg="#f0f8ff")
        self.username = None
        self.websocket = None
        self.setup_login()

    def setup_login(self):
        self.clear_window()

        tk.Label(self.root, text="Login", font=("Arial", 18), bg="#f0f8ff", fg="#4682b4").pack(pady=10)
        
        tk.Label(self.root, text="Username:", bg="#f0f8ff", fg="#4682b4").pack()
        self.username_entry = tk.Entry(self.root, bg="#ffffff", fg="#000000")
        self.username_entry.pack()
        
        tk.Label(self.root, text="Password:", bg="#f0f8ff", fg="#4682b4").pack()
        self.password_entry = tk.Entry(self.root, show="*", bg="#ffffff", fg="#000000")
        self.password_entry.pack()
        
        tk.Button(self.root, text="Login", bg="#4682b4", fg="#ffffff", command=self.login).pack(pady=5)
        tk.Button(self.root, text="Register", bg="#4682b4", fg="#ffffff", command=self.register).pack()

    def setup_register(self):
        self.clear_window()

        tk.Label(self.root, text="Register", font=("Arial", 18), bg="#f0f8ff", fg="#4682b4").pack(pady=10)
        
        tk.Label(self.root, text="Username:", bg="#f0f8ff", fg="#4682b4").pack()
        self.username_entry = tk.Entry(self.root, bg="#ffffff", fg="#000000")
        self.username_entry.pack()
        
        tk.Label(self.root, text="Password:", bg="#f0f8ff", fg="#4682b4").pack()
        self.password_entry = tk.Entry(self.root, show="*", bg="#ffffff", fg="#000000")
        self.password_entry.pack()

        tk.Label(self.root, text="Mobile Number:", bg="#f0f8ff", fg="#4682b4").pack()
        self.mobile_entry = tk.Entry(self.root, bg="#ffffff", fg="#000000")
        self.mobile_entry.pack()
        
        tk.Button(self.root, text="Submit", bg="#4682b4", fg="#ffffff", command=self.register_user).pack(pady=5)
        tk.Button(self.root, text="Back to Login", bg="#4682b4", fg="#ffffff", command=self.setup_login).pack()

    def setup_chat(self):
        self.clear_window()

        tk.Label(self.root, text=f"Welcome, {self.username}", font=("Arial", 16), bg="#f0f8ff", fg="#4682b4").pack(pady=10)

        self.chat_display = tk.Text(self.root, state="disabled", height=15, width=50, bg="#ffffff", fg="#000000")
        self.chat_display.pack(pady=5)

        self.message_entry = tk.Entry(self.root, width=40, bg="#ffffff", fg="#000000")
        self.message_entry.pack(side="left", padx=5)
        
        tk.Button(self.root, text="Send", bg="#4682b4", fg="#ffffff", command=self.send_message).pack(side="left")

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if authenticate_user(username, password):
            self.username = username
            self.setup_chat()
            threading.Thread(target=self.receive_messages, daemon=True).start()
        else:
            messagebox.showerror("Error", "Invalid username or password")

    def register(self):
        self.setup_register()

    def register_user(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        mobile = self.mobile_entry.get().strip()

        if not username or not password or not mobile:
            messagebox.showerror("Error", "All fields are required")
            return

        if len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters long")
            return

        if not mobile.isdigit() or len(mobile) != 10:
            messagebox.showerror("Error", "Mobile number must be a 10-digit numeric value")
            return

        if register_user_backend(username, password, mobile):
            messagebox.showinfo("Success", f"Account created successfully!\nUsername: {username}")
            self.setup_login()
        else:
            messagebox.showerror("Error", "Username already exists")

    def send_message(self):
        message = self.message_entry.get().strip()
        if message and self.websocket:
            asyncio.run(self.websocket.send(f"{self.username}: {message}"))
            self.message_entry.delete(0, tk.END)

    async def connect_to_server(self):
        try:
            self.websocket = await websockets.connect("ws://localhost:8765")
            await self.websocket.send(self.username)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to server: {e}")

    def receive_messages(self):
        asyncio.run(self.connect_to_server())
        if self.websocket:
            try:
                while True:
                    message = asyncio.run(self.websocket.recv())
                    self.chat_display.config(state="normal")
                    self.chat_display.insert(tk.END, message + "\n")
                    self.chat_display.config(state="disabled")
            except Exception as e:
                messagebox.showerror("Error", f"Connection error: {e}")

# --------------------- MAIN ---------------------

if __name__ == "__main__":
    init_db()
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
