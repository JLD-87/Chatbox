import socket
import threading
import tkinter as tk
from tkinter import ttk
import tkinter.scrolledtext as st
from tkinter import simpledialog
import json
import queue
import os

#LOCALHOST='127.0.0.1'
#PORT = 5000
HOST=os.getenv('HOST')
PORT = os.getenv('PORT')

class Client:
    def __init__(self,HOST,PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))

        msg=tk.Tk()
        msg.withdraw()
        self.nickname = simpledialog.askstring("Nickname", "Please choose a nickname", parent=msg)

        self.running = True
        self.gui_events = queue.Queue()

        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.start()
        self.gui_loop()

    def gui_loop(self):
        self.win = tk.Tk()
        self.win.configure(bg="lightgray")
        self.win.title("Chat Client")
        self.win.geometry("800x600")

        # Configure grid so frames can resize proportionally
        self.win.grid_rowconfigure(0, weight=1)
        self.win.grid_columnconfigure(0, weight=5, minsize=500)  # Larger frame
        self.win.grid_columnconfigure(1, weight=0)  # Smaller frame

        # ===== Frame 1 =====
        frame1 = ttk.Frame(self.win, relief="ridge")
        frame1.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.chat_label = tk.Label(frame1, text="Chat:", bg="lightgray")
        self.chat_label.config(font=("Arial", 12))
        self.chat_label.pack(padx=20, pady=5)

        self.text_area = st.ScrolledText(frame1)
        self.text_area.pack(padx=20, pady=5)
        self.text_area.config(state='disabled') #history of chat, cant be changed

        self.msg_label = tk.Label(frame1, text="Message:", bg="lightgray")
        self.msg_label.config(font=("Arial", 12))
        self.msg_label.pack(padx=20, pady=5)

        self.input_area = tk.Text(frame1, height=3)
        self.input_area.pack(padx=20, pady=5)

        self.send_button = tk.Button(frame1, text="Send", command=self.write)
        self.send_button.config(font=("Arial", 12))
        self.send_button.pack(padx=20, pady=5)

        self.ask_button = tk.Button(frame1, text="Ask AI", command=self.ask_ai)
        self.ask_button.config(font=("Arial", 12))
        self.ask_button.pack(padx=20, pady=5)

        # ===== Frame 2 =====
        frame2 = ttk.Frame(self.win, relief="ridge", padding=5, width=200)
        frame2.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.list_area = st.ScrolledText(frame2, height=200, width=30)
        self.list_area.pack(padx=5, pady=5)
        self.list_area.config(state='disabled') #clients connected

        self.win.protocol("WM_DELETE_WINDOW", self.stop)
        self.win.after(50, self.process_gui_events)
        self.win.mainloop()

    def ask_ai(self):
        question = self.input_area.get('1.0', 'end').strip()
        if question:
            question_dump = json.dumps({"type": "ASK_AI", "user": self.nickname, "content": question}).encode('utf-8')
            self.sock.send(question_dump)
            self.input_area.delete('1.0', 'end')

    def write(self):
        message = f"{self.nickname}: {self.input_area.get('1.0', 'end')}"
        message_dump = json.dumps({"type": "MESSAGE", "content": message}).encode('utf-8')
        self.sock.send(message_dump)
        self.input_area.delete('1.0', 'end')

    def stop(self):
        self.running = False
        self.win.destroy()
        self.sock.close()
        exit(0)

    def write_client_list(self, clients):
        self.list_area.config(state='normal')
        self.list_area.delete('1.0', 'end')
        for client in clients:
            self.list_area.insert('end', f"{client}\n")
        print(f"Client list updated in GUI: {clients}")
        self.list_area.config(state='disabled')

    def write_message(self, message):
        self.text_area.config(state='normal')
        self.text_area.insert('end', f"{message}\n")
        self.text_area.yview('end')
        self.text_area.config(state='disabled')

    def process_gui_events(self):
        while True:
            try:
                event_type, payload = self.gui_events.get_nowait()
            except queue.Empty:
                break
            if event_type == 'CLIENT_LIST':
                self.write_client_list(payload)
            elif event_type == 'MESSAGE':
                self.write_message(payload)
            elif event_type == 'NICK':
                self.sock.send(self.nickname.encode('utf-8'))

        if self.running:
            self.win.after(50, self.process_gui_events)

    def receive_messages(self):
        while self.running:
            try:
                message = self.sock.recv(1024).decode('utf-8')
                message = json.loads(message)
                self.gui_events.put((message['type'], message['content']))
                print(f"Event queued: {message['type']} with content: {message['content']}")

            except ConnectionAbortedError:
                print("Connection closed by the server.")
                break
            except:
                print("An error occurred while receiving messages.")
                self.sock.close()
                break

client = Client(HOST, PORT)