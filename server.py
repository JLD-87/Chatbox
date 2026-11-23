# Standard library
import json
import os
import socket
import ssl
import struct
import threading
import queue
import time
from datetime import datetime

# Third-party libraries
import requests
from dotenv import load_dotenv

# Local modules
import authentication
from protocol import encode_frame, recv_json, send_json

#load environment variables from .env file
load_dotenv()

# Constants
HOST ='0.0.0.0' #listens all ports, put localhost='127.0.0.1' for testing
PORT = 5000
llm_api_key=os.getenv('LLM_API_KEY')

send_lock = threading.Lock()  # Create a lock for sending messages
login_lock = threading.Lock()

server = None
context = None 
MAX_CHAT_LENGTH = 2000


# Save TLS secured sockets and nicknames in a dictionary
clients = {}

#Instantiate the authentication class
auth = authentication.Auth_class()

# Create queue to save history
history_queue = queue.Queue()

# Send one ready-made frame to every connected client, without letting one bad client affect the others
def send_to_all(frame):
    with send_lock:
        for tls_client in list(clients):      # snapshot: safe even if another thread changes clients
            try:
                tls_client.sendall(frame)
            except OSError:
                # Dead connection: close it, its own thread will notice and run cleanup_client
                try:
                    tls_client.close()
                except OSError:
                    pass

# Send messages to everyone in the clients list, with a lock to prevent race conditions
def broadcast(message):
    print(f"Broadcasting message: {message.decode('utf-8')}")
    send_to_all(encode_frame({"type": "MESSAGE", "content": message.decode('utf-8')}))

# Broadcast the list of nicknames to all clients
def broadcast_list_clients():
    print(f"Broadcasting client list: {list(clients.values())}")
    send_to_all(encode_frame({"type": "CLIENT_LIST", "content": list(clients.values())}))

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

        with login_lock:

            # Check if this account is already connected
            already_logged_in = username in clients.values()

            if not already_logged_in:
                clients[tls_client] = username

        if already_logged_in:
            send_auth_response(tls_client, "LOGIN", username, "failure")
            return False

        send_auth_response(tls_client, "LOGIN", username, "success")

        broadcast_list_clients()
        broadcast(f"{username} has joined the chat!\n".encode('utf-8'))

        return True

    else:
        print(f"Authentication failed for user '{username}'.")
        send_auth_response(tls_client, "LOGIN", username, "failure")
        return False

# Packages the authentication response into a json message and sends it to the client, with a header indicating the message length
def send_auth_response(tls_client, event_type, username, result):
    send_json(tls_client, {"type": event_type, "content": {"username": username, "result": result}})

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

            message = recv_json(tls_client)
            process_message(tls_client, message)

    except (ConnectionError, ssl.SSLError, OSError) as error:
        print(f"Connection error: {error}")

    except (ValueError, KeyError, TypeError) as error:   # includes JSONDecodeError
        print(f"Bad message, dropping client: {error}")

    except Exception as e:
        print(f"Unexpected error: {type(e).__name__}: {e}")

    # Handle client disconnection and cleanup
    finally:
        cleanup_client(tls_client)

# Handles authentication and registeration
def authenticate_client(tls_client):
    while True:
        request = recv_json(tls_client)

        if request_credentials(tls_client, request):
            return True

# Processes incoming messages from clients, determining whether they are AI requests or chat messages, and calls the appropriate handler
def process_message(tls_client, message):

    if message['type'] == 'ASK_AI':
        handle_ai_request(tls_client, message)

    elif message['type'] == 'MESSAGE':

        content = message.get("content", "")

        if not isinstance(content, str) or not content.strip():
            return
        if len(content) > MAX_CHAT_LENGTH:
            return
        
        message["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_queue.put(message)
        handle_chat_message(tls_client, message)

# Saves chat history to a JSON file in a separate thread to avoid blocking the main server thread
def save_chat_history_thread():
    while True:
        message = history_queue.get()
        print("History worker received:", message)

        try:
            save_message(message)

        except Exception as e:
            print(f"Failed to save chat history: {e}")

        finally:
            history_queue.task_done()

def save_message(message):
    history_message = message.copy()
    history_message.pop("type", None)

    with open(auth.CHAT_HISTORY_FILE, "a", encoding="utf-8") as file:
        json.dump(history_message, file, ensure_ascii=False)
        file.write("\n")

# Handles chat messages by broadcasting them to all clients
def handle_chat_message(tls_client, message):
    username = clients.get(tls_client, "Unknown")
    if username is None:
        return

    content = message.get("content", "")

    print(f"{username} sent message: {content}")

    broadcast(f"{username}: {content}".encode("utf-8"))

# Handles AI requests by sending a POST request to the OpenRouter API with the user's question and returns the AI's response
def handle_ai_request(tls_client, message):
    username = clients.get(tls_client)

    if username is None:
        return

    question = message['content']

    broadcast(f"{username}: {question}".encode('utf-8'))
    broadcast("AI is thinking...".encode('utf-8'))

    answer = ask_openrouter(question)

    broadcast(f"AI answered: {answer}".encode('utf-8'))

# Handles disconnections and cleanup when a client disconnects
def cleanup_client(tls_client):
    if tls_client is None:
        return

    print("A client has disconnected.")

    with login_lock:
        username = clients.pop(tls_client, None)

    if username is not None:
        broadcast_list_clients()
        broadcast(f"{username} has left the chat!".encode('utf-8'))

    try:
        tls_client.close()
    except OSError:
        pass

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

    try:
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
            }),
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

    except (requests.RequestException, ValueError) as e:
        print(f"OpenRouter request error: {e}")
        return "AI response unavailable."

    choices = data.get("choices")

    if not isinstance(choices, list) or not choices:
        return "AI response unavailable."

    message = choices[0].get("message", {})

    if not isinstance(message, dict):
        return "AI response unavailable."

    content = message.get("content")

    if not isinstance(content, str) or not content.strip():
        return "AI response unavailable."

    return content

def main():
    global server, context
    
    # Create a TCP socket
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()

    # Wrap socket with SSL
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

    # Initialize files
    auth.create_users_file()
    auth.create_chat_history_file()

    history_thread = threading.Thread(target=save_chat_history_thread, daemon=True)
    history_thread.start()

    # Start the server and begin accepting connections
    print("Server is running and ready to accept connections...")
    receive_connections()

if __name__ == "__main__":
    main()