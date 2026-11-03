Python Chatbox with LLM Integration

Overview: 
This project is a Python client-server chat application with LLM integration. 

Features: 
multiple clients can connect, 
messages sent and received, 
connected client list shown,
connection is encrypted with TLS (server's identity is verified by certificate),
lock is implemented on broadcasting (messages do not appear in the middle of a long AI response),
AI button sends AI request, server calls LLM, and returns the answer. 

Technologies: Python, sockets, threading, tkinter, JSON, getenv, event queue, TLS, lock, requests and a free-tiered LLM API (https://openrouter.ai/nvidia/nemotron-3.5-super-vl:free)

Project structure:
client.py : It contains the code for the server launch.
server.py : It contains the code for the client. It connects to the server, locally or over the net depending on your setup.
.env : It contains your environment variables. HOST(host ip adress), PORT(used by the app), LLM_API_KEY (create it on the website mentionned before). Keep your API key in .env, not in the code.
README.md
cert.pem, key.pem: for TLS secure connection, public certificate and private key are both kept private

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
authentication
account creation and email verification, data in a JSON file or a DB
message chunking (long ai responses trigger errors)
