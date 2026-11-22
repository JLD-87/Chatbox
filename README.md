Python Chatbox with LLM Integration

Overview: 
This project is a Python client-server chat application with LLM integration. 

Features: 

multiple clients can connect, 
messages sent and received, timestamped and saved in history,
connected client list shown,
connection is encrypted with TLS (server's identity is verified by a self-signed certificate),
lock is implemented on broadcasting (messages from the same client do not appear in the middle of a long AI response),
long AI responses are sent in chunks and recontructed after reception,
AI button sends AI request, server calls LLM, and returns the answer,
clients need to register with username and password, data is saved in json, lock prevents race conditions on writing the file.

Technologies: Python, sockets, threading, tkinter, JSON and JSONL, getenv, event queue, TLS, lock, register and login, robust exiting, requests and a free-tiered LLM API (https://openrouter.ai/nvidia/nemotron-3.5-super-vl:free)

Project structure:
server.py : It contains the code for the server launch.
client.py : It contains the code for the client. It connects to the server, locally or over the net depending on your setup.
authentication.py: The code manipulates data from the json file to write or check users information for logging.
.env : It contains your environment variables. HOST(host ip adress), PORT(used by the app), LLM_API_KEY (create it on the website mentionned before). Keep your API key in .env, not in the code.
README.md
cert.pem, key.pem: for TLS secure connection, public certificate and private key are both kept private
users.json: users data for logging. Passwords are hashed using argon2.

Requirements: Python installed, virtual environment, install dependencies.

Installation: 
clone your repo or download the files, create and activate a virtual environment, pip install your requirements, create the .env file. add your API key.
Create both certificate and private keys for TLS encryption.
Run the server first, then the client. 

Network setup: 0.0.0.0 is for server listening all traffic on all network interfaces. It works over the internet if you install portforwarding and put your public IP adress. 

Cmd line for creating a certificate and key: 
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem -subj "/CN=YOUR_PUBLIC_IP" -addext "subjectAltName=IP:YOUR_PUBLIC_IP"

Messaging system:
normal message: On pressing Send. The message is flagged client-side and sent to the server. It is broadcasted to everyone by the server.
Ask AI: The AI button sends a type flag, server routes the question, calls the LLM via API, returns the reply. 



Possible improvements:
add a logger,
email verification, data in a JSON file or a DB
global lock (not only the client asking, but all other clients can't send anything when AI is sending a long response)
chunking messages to server (server can send long messages to clients, especially from AI, but clients are limited to around 1000 chars)
OR limit message length on app client-side, before attempting to send to server
separate window for 1 on 1 messaging
adding emotes
Message delivery guarantees
user profiles
contact and friends

Message improvements
- Private messages between two users.
- Message timestamps.
- Read receipts.
- Typing indicators.
- Edit and delete messages.
- Message history.

Group chats
- Create chat rooms.
- Invite users.
- Join and leave rooms.
- Room-specific message history.
- Send images.

Robust authentication
- Password hashing with Argon2.
- Account registration and login.
- Session management.
- Multiple-device support.
- Account permissions.
  Private messaging and persistence
- Private conversations.
- Message history.
- SQLite or PostgreSQL.
- Message IDs and timestamps.
- Offline message delivery.
- Automatic reconnection.

- Separate authentication, networking and messaging modules.
- Dedicated message-processing queue.
- Logging and exception handling.
  
  Testing
- Dockerize the server.
- Deploy it to AWS.
- Configure persistent storage.
- Add monitoring and server logs.

22/11/26
- automatically create a chat history file in jsonl, the server doesnt need to read the full history to add a line
- save message into chat_history, username and content message are not seperated yet
- clients socks and username are now saved in a unique dictionnary
- message are sent into history via a queue
- on server launch, json files are created, and a thread dedicated to chat history is launched