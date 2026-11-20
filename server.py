import socket
import threading
import json
import struct
import requests
import os
import ssl
from dotenv import load_dotenv
import authentication

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

#Instantiate the authentication class
auth = authentication.Auth_class()

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

# Authentication GUI can send either a register or login request, this function calls the appropriate handler
# Only a succesful login returns true, allowing the client to enter the messaging system.
def request_credentials(tls_client, message):

    username = message['content']['username']
    password = message['content']['password']

    if message['type'] == 'REGISTER':
        return handle_register(tls_client, username, password)

    elif message['type'] == 'LOGIN':
        return handle_login(tls_client, username, password)

# Handles registration requests, authentication logic is in the authentication.py module
def handle_register(tls_client, username, password):
    if auth.register_user(username, password):
        print(f"User '{username}' registered successfully.")
        send_auth_response(tls_client, "REGISTER", username, "success")
    else:
        print(f"Registration failed for user '{username}'.")
        send_auth_response(tls_client, "REGISTER", username, "failure")

    return False # Return False, client still needs to authenticate to get to the messaging system

# Handles login requests, authentication logic is in the authentication.py module
# On successful login, the client is added to the clients list and the nickname is added to the nicknames list, allowing for messaging
def handle_login(tls_client, username, password):
    if auth.authenticate_user(username, password):
        print(f"User '{username}' authenticated successfully.")

        send_auth_response(tls_client, "LOGIN", username, "success")

        nicknames.append(username)
        clients.append(tls_client)

        broadcast_list_clients()
        broadcast(f"{username} has joined the chat!\n".encode('utf-8'))

        return True # Return True to indicate successful authentication

    else:
        print(f"Authentication failed for user '{username}'.")
        send_auth_response(tls_client, "LOGIN", username, "failure")
        return False # Return False to indicate failed authentication

# Packages the authentication response into a json message and sends it to the client, with a header indicating the message length
def send_auth_response(tls_client, event_type, username, result):
    response = json.dumps({
        "type": event_type,
        "content": {
            "username": username,
            "result": result
        }
    }).encode("utf-8")

    header = struct.pack('!I', len(response))
    tls_client.sendall(header + response)

#Main loops, first for login, second for messaging, clean up if the client disconnects
def handle_client(client):

    tls_client = None  # Initialize tls_client to None for cleanup in case of early exit

    try:

        #Connecting the client, its socket and to the server, and broadcasting the new client's to all other clients
        tls_client = context.wrap_socket(client, server_side=True)

        # Waiting for authentication,client can register here but does not proceed until login
        if not authenticate_client(tls_client):
            return


        # Main loop awaiting messages or Ai requests from clients
        while True:
            message = tls_client.recv(1024).decode('utf-8')

            if not message:
                break  # Client disconnected

            message=json.loads(message)
            process_message(tls_client, message)

    except (ConnectionError, ssl.SSLError, OSError) as error:
        print(f"Connection error: {error}")

    except Exception as e:
        print(f"Authentication error: {type(e).__name__}: {e}")
        raise

    # Handle client disconnection and cleanup
    finally:
        cleanup_client(tls_client)

# Handles authentication and registeration
def authenticate_client(tls_client):
    while True:
        credentials = tls_client.recv(1024).decode('utf-8')

        #check if the client disconnected, server receives an empty string when the client disconnects
        if not credentials:
            return False

        request = json.loads(credentials)

        if request_credentials(tls_client, request):
            return True

# Processes incoming messages from clients, determining whether they are AI requests or chat messages, and calls the appropriate handler
def process_message(tls_client, message):

    if message['type'] == 'ASK_AI':
        handle_ai_request(message)

    elif message['type'] == 'MESSAGE':
        handle_chat_message(tls_client, message)

# Handles chat messages by broadcasting them to all clients
def handle_chat_message(tls_client, message):
    print(f"{nicknames[clients.index(tls_client)]} sent message: {message}")
    broadcast(message['content'].encode('utf-8'))

# Handles AI requests by sending a POST request to the OpenRouter API with the user's question and returns the AI's response
def handle_ai_request(message):
    question = message['content']

    broadcast(f"{message['user']}: {question}".encode('utf-8'))
    broadcast("AI is thinking...".encode('utf-8'))

    answer = ask_openrouter(question)

    broadcast(f"AI answered: {answer}".encode('utf-8'))

# Handles disconnections and cleanup when a client disconnects
def cleanup_client(tls_client):
    if tls_client is None:
        return

    print("A client has disconnected.")

    if tls_client in clients:
        index = clients.index(tls_client)

        clients.pop(index)
        nicknames.pop(index)

        broadcast_list_clients()

    tls_client.close()

# Listens for incoming connections and starts a new thread for each client
def receive_connections():
    print(f"Server is listening on port {PORT}...")
    while True:
        #when accepting a new connection, creates a socket object and returns the address of the client as (ip, port)
        client, address = server.accept()
        print(f"Connection established with {str(address)}")

        # Start a new thread to handle the client
        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()

# Sends a POST request to the OpenRouter API with the user's question and returns the AI's response
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



# Start the server and begin accepting connections
print("Server is running and ready to accept connections...")
receive_connections()
