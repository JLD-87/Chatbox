import socket
import threading
import json
import struct
import requests
import os
import ssl
from dotenv import load_dotenv

#load environment variables from .env file
load_dotenv()

HOST ='0.0.0.0' #localhost='127.0.0.1'
PORT = 5000
llm_api_key=os.getenv('LLM_API_KEY')

send_lock = threading.Lock()  # Create a lock for sending messages

# Create a TCP socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST,PORT))
server.listen()

# Wrap socket with SSL
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

# Save TLS secured sockets and nicknames in lists, clients is a list of sockets themselves
clients = []
nicknames = []

# Send messages to everyone in the clients list, with a lock to prevent race conditions
def broadcast(message):
    message_dumped = json.dumps({"type": "MESSAGE", "content": message.decode('utf-8')}).encode('utf-8')
    # Encode message length into a 4 bytes header
    header = struct.pack('!I', len(message_dumped))
    print(f"Broadcasting message: {message.decode('utf-8')}")
    # Use lock and send messages to all clients. The header sends the message length first, allowing for lengthy messages
    with send_lock:
        for tls_client in clients:
            tls_client.sendall(header + message_dumped)

# Broadcast the list of nicknames to all clients
def broadcast_list_clients():
    client_list = json.dumps({"type": "CLIENT_LIST", "content": nicknames}).encode('utf-8')
    # Encode message length into a 4 bytes header
    header = struct.pack('!I', len(client_list))
    print(f"Broadcasting client list: {nicknames}")
    for tls_client in clients:
        tls_client.sendall(header + client_list)

# Request the nickname from the client, with 4-bytes header and type 'NICK'
def request_nickname(tls_client):
    nickname_request=json.dumps({"type": "NICK", "content": ""}).encode('utf-8')
    header = struct.pack('!I', len(nickname_request))
    tls_client.send(header + nickname_request)

    nickname = tls_client.recv(1024).decode('utf-8')
    nicknames.append(nickname)
    clients.append(tls_client)
    broadcast_list_clients()
    broadcast(f"{nickname} has joined the chat!\n".encode('utf-8'))

def handle_client(client):
    try:
    #Connecting the client, its socket and nickname to the server, and broadcasting the new client's nickname to all other clients
        tls_client = context.wrap_socket(client, server_side=True)
        #print(f"TLS connection established with {tls_client.getpeername()}")
        request_nickname(tls_client)

    # Main loop awaiting messages or Ai requests from clients
        while True:
            message = tls_client.recv(1024).decode('utf-8')
            print(f"{message}")
            message=json.loads(message)

            if message['type'] == 'ASK_AI':
                question = message['content']
                broadcast(f"{message['user']}: {question}".encode('utf-8'))
                broadcast(("AI is thinking...").encode('utf-8'))
                answer = ask_openrouter(question)
                response_message = f"AI answered: {answer}"
                broadcast(response_message.encode('utf-8'))
            elif message['type'] == 'MESSAGE':
                print(f"{nicknames[clients.index(tls_client)]} sent message: {message}")
                broadcast(message['content'].encode('utf-8'))

    except (ConnectionError, OSError) as error:
        print(f"Connection error: {error}")

    # Handle client disconnection and cleanup
    finally:
        print("A client has disconnected.")

        if tls_client in clients:
            index = clients.index(tls_client)
            nickname = nicknames[index]

            clients.pop(index)
            nicknames.pop(index)

            tls_client.close()
            broadcast_list_clients()
        else:
            tls_client.close()

def receive_connections():
    print(f"Server is listening on port {PORT}...")
    while True:
        #when accepting a new connection, creates a socket object and returns the address of the client as (ip, port)
        client, address = server.accept()
        print(f"Connection established with {str(address)}")

        # Start a new thread to handle the client
        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()

def ask_openrouter(question):  
    # First API call with reasoning
    response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {llm_api_key}",
        "Content-Type": "application/json",
    },
    data=json.dumps({
        "model": "nvidia/nemotron-3.5-super-vl:free",
        "messages": [
            {
            "role": "user",
            "content": question
            }
        ],
        "reasoning": {"enabled": True}
    })
    )

    # Extract the assistant message with reasoning_details
    response = response.json()
    response = response['choices'][0]['message']
    return response.get('content')

# MAIN
print("Server is running and ready to accept connections...")
receive_connections()
