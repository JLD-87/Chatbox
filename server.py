import socket
import threading
import json

HOST ='127.0.0.1'
PORT = 5000

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST,PORT))
server.listen()

clients = []
nicknames = []

def broadcast(message):
    message_dumped = json.dumps({"type": "MESSAGE", "content": message.decode('utf-8')}).encode('utf-8')
    print(f"Broadcasting message: {message.decode('utf-8')}")
    for client in clients:
        client.send(message_dumped)


def broadcast_list_clients():
    client_list = json.dumps({"type": "CLIENT_LIST", "content": nicknames}).encode('utf-8')
    print(f"Broadcasting client list: {nicknames}")
    for client in clients:
        client.send(client_list)


def handle_client(client):
    while True:
        try:
            message = client.recv(1024)
            print(f"{nicknames[clients.index(client)]} sent message: {message}")
            broadcast(message)
        except:
            print("A client has disconnected.")
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            nicknames.remove(nickname)
            broadcast_list_clients()
            break

def receive_connections():
    print(f"Server is listening on port {PORT}...")
    while True:
        #when accepting a new connection, creates a socket object and returns the address of the client as (ip, port)
        client, address = server.accept()
        print(f"Connection established with {str(address)}")

        nickname_request=json.dumps({"type": "NICK", "content": ""}).encode('utf-8')
        client.send(nickname_request)
        nickname = client.recv(1024).decode('utf-8')
        nicknames.append(nickname)
        clients.append(client)
        broadcast_list_clients()

        print(f"Nickname of the client is {nickname}")
        broadcast(f"{nickname} has joined the chat!\n".encode('utf-8'))

        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()

print("Server is running and ready to accept connections...")
receive_connections()
