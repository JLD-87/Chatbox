import socket
import threading
import json
import requests
import os

HOST ='0.0.0.0' #localhost='127.0.0.1'
PORT = 5000
llm_api_key=os.getenv('LLM_API_KEY')

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
    try:
        while True:
            message = client.recv(1024).decode('utf-8')
            message=json.loads(message)

            if message['type'] == 'ASK_AI':
                question = message['content']
                broadcast(f"{message['user']}: {question}".encode('utf-8'))
                broadcast(("AI is thinking...").encode('utf-8'))
                answer = ask_openrouter(question)
                response_message = f"AI answered: {answer}"
                broadcast(response_message.encode('utf-8'))
            elif message['type'] == 'MESSAGE':
                print(f"{nicknames[clients.index(client)]} sent message: {message}")
                broadcast(message['content'].encode('utf-8'))

    except (ConnectionError, OSError) as error:
        print(f"Connection error: {error}")

    finally:
        print("A client has disconnected.")

        if client in clients:
            index = clients.index(client)
            nickname = nicknames[index]

            clients.pop(index)
            nicknames.pop(index)

            client.close()
            broadcast_list_clients()
        else:
            client.close()

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
