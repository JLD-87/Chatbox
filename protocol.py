import json
import struct

MAX_MESSAGE = 64 * 1024  # reject absurd frames


def recv_exactly(sock, length):
    data = b''
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ConnectionError("Peer disconnected")
        data += chunk
    return data


def encode_frame(payload):
    raw = json.dumps(payload).encode('utf-8')
    return struct.pack('!I', len(raw)) + raw


def send_json(sock, payload):
    sock.sendall(encode_frame(payload))


def recv_json(sock):
    (length,) = struct.unpack('!I', recv_exactly(sock, 4))
    if length > MAX_MESSAGE:
        raise ValueError("Message too large")
    return json.loads(recv_exactly(sock, length).decode('utf-8'))