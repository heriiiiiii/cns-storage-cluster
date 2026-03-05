import socket
import json
import time
from datetime import datetime

SERVER_IP = "127.0.0.1"
SERVER_PORT = 3000

NODE_ID = "LPZ"          # debe estar en EXPECTED_NODES
REGION = "La Paz"

def send_line(sock, obj):
    line = json.dumps(obj) + "\n"
    sock.sendall(line.encode())

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((SERVER_IP, SERVER_PORT))
        print("Conectado al servidor")

        # HELLO
        send_line(sock, {
            "type": "hello",
            "node_id": NODE_ID,
            "region": REGION,
            "client_timestamp": datetime.utcnow().isoformat() + "Z"
        })

        # Loop: enviar métricas cada 3s
        sock.settimeout(0.5)
        while True:
            # METRICS
            send_line(sock, {
                "type": "metrics",
                "node_id": NODE_ID,
                "disk": {
                    "name": "C:",
                    "type": "SSD",
                    "total_gb": 400,
                    "used_gb": 100,
                    "free_gb": 300,
                    "iops": 120
                },
                "extras": {
                    "ram_gb": 64,
                    "ip": "192.168.1.10",
                    "mac": "AA:BB:CC:DD:EE:FF"
                },
                "client_timestamp": datetime.utcnow().isoformat() + "Z"
            })

            # leer comandos del server y responder ACK
            try:
                data = sock.recv(4096)
                if data:
                    for line in data.decode(errors="replace").split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        msg = json.loads(line)
                        if msg.get("type") == "command":
                            msg_id = msg.get("msg_id")
                            print("Comando recibido:", msg.get("command"), "msg_id=", msg_id)
                            send_line(sock, {
                                "type": "ack",
                                "node_id": NODE_ID,
                                "msg_id": msg_id,
                                "status": "OK",
                                "client_timestamp": datetime.utcnow().isoformat() + "Z"
                            })
            except socket.timeout:
                pass

            time.sleep(3)

if __name__ == "__main__":
    main()