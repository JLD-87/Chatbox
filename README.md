Python Chatbox with LLM Integration

Overview: 
This project is a Python client-server chat application with LLM integration. 

Features: 
multiple clients can connect, 
messages sent and received, 
connected client list shown, 
AI button sends AI request, server calls LLM, and returns the answer. 

Technologies: Python, sockets, threading, tkinter, JSON, getenv, event queue, requests and a free-tiered LLM API (https://openrouter.ai/nvidia/nemotron-3.5-super-vl:free)

Project structure:
client.py : It contains the code for the server launch.
server.py : It contains the code for the client. It connects to the server, locally or over the net depending on your setup.
.env : It contains your environment variables. HOST(host ip adress), PORT(used by the app), LLM_API_KEY (create it on the website mentionned before). Keep your API key in .env, not in the code.
README.md

Requirements: Python installed, virtual environment, install dependencies.

Installation: 
clone your repo or download the files, create and activate a virtual environment, pip install your requirements, create the .env file. add your API key. 
Run the server first, then the client. 

Network setup: 0.0.0.0 is for server listening all traffic on all network interfaces. It works over the internet if you install portforwarding and put your public IP adress. 

Messaging system:
normal message: On pressing Send. The message is flagged client-side and sent to the server. It is broadcasted to everyone by the server.
Ask AI: The AI button sends a type flag, server routes the question, calls the LLM via API, returns the reply. 

Possible improvements:
authentication
account creation and email verification, data in a JSON file or a DB
message encryption with TLS
concurrency (own thread for the LLM)
