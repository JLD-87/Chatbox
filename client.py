from multiprocessing import context
import socket
import threading
import tkinter as tk
from tkinter import ttk
import tkinter.scrolledtext as st
from tkinter import simpledialog
import json
import struct
import queue
import os
import ssl
from dotenv import load_dotenv
load_dotenv()

#Set host and port with data from environment variables
'''
Use localhost for testing
LOCALHOST='127.0.0.1'
PORT = 5000
Else, put your public IP, and make sure to open the port in your router settings
'''
HOST=os.getenv('HOST')
PORT = int(os.getenv('PORT'))


class Client:
    def __init__(self,HOST,PORT):
        #Create a TCP socket on opening the client
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Wrap the socket with SSL
        context = ssl.create_default_context()
        context.load_verify_locations('./cert.pem')
        self.sock = context.wrap_socket(self.sock, server_hostname=HOST)
        #Connect to the server
        self.sock.connect((HOST, PORT))
        print(f"Connecting to server at {HOST}:{PORT} with SSL")

        # Prompt for nickname using a simple dialog window
        msg=tk.Tk()
        msg.withdraw()
        self.nickname = simpledialog.askstring("Nickname", "Please choose a nickname", parent=msg)

        self.running = True
        self.gui_events = queue.Queue()

        # Start a thread for each client to handle its main loop
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

    # Send a question with header ASK_AI to the server when AI button is clicked, the server sends an API request, and the answer is broadcasted to all clients
    def ask_ai(self):
        question = self.input_area.get('1.0', 'end').strip()
        if question:
            question_dump = json.dumps({"type": "ASK_AI", "user": self.nickname, "content": question}).encode('utf-8')
            self.sock.send(question_dump)
            self.input_area.delete('1.0', 'end')

    # Send a message with header MESSAGE to the server when Send button is clicked, the server broadcasts it to all clients
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

    # Write the list of clients in the GUI, on its own frame in list_area, and disable editing the list
    def write_client_list(self, clients):
        self.list_area.config(state='normal')
        self.list_area.delete('1.0', 'end')
        for client in clients:
            self.list_area.insert('end', f"{client}\n")
        print(f"Client list updated in GUI: {clients}")
        self.list_area.config(state='disabled')

    # Write a message in the GUI, on its own frame in text_area, and disable editing past messages
    def write_message(self, message):
        self.text_area.config(state='normal')
        self.text_area.insert('end', f"{message}\n")
        self.text_area.yview('end')
        self.text_area.config(state='disabled')

    # Main threadloop, awaits events from queue and writes them to the GUI, 50ms downtime to save CPU with 'after' method
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

    # Receive exactly the specified number of bytes in chunks from the socket, and concatenate them, also used to receive headers in 4 bytes
    def receive_exactly(self, length):
        data = b''
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk:
                raise ConnectionError("Client disconnected")
            data += chunk
        return data

    # Client thread that receives messages from the server, unpacks them, and put them in queue
    def receive_messages(self):
        while self.running:
            try:
                 # First receive the 4-byte header
                header = self.receive_exactly(4)

                # Extract message length
                message_length = struct.unpack('!I', header)[0]

                # Receive the rest of the complete message with the exact length specified in the header
                data = self.receive_exactly(message_length)
                message = json.loads(data.decode('utf-8'))

                # Queue the event for the GUI to process
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