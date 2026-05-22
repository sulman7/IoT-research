import socket
import csv
import time
from datetime import datetime

UDP_IP = "0.0.0.0"
UDP_PORT = 5005
CSV_FILE = "wifi_received_packets.csv"

def create_csv():
    with open(CSV_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "rx_time_ms",
            "node_id",
            "seq",
            "tx_time_ms",
            "rssi_dbm",
            "payload_raw",
            "sender_ip",
            "sender_port"
        ])

def parse_payload(payload: str):
    parts = payload.strip().split(",")

    node_id = parts[0] if len(parts) > 0 else ""
    seq = parts[1] if len(parts) > 1 else ""
    tx_time_ms = parts[2] if len(parts) > 2 else ""
    rssi_dbm = parts[3] if len(parts) > 3 else ""

    return node_id, seq, tx_time_ms, rssi_dbm

def main():
    create_csv()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))

    print(f"Wi-Fi UDP gateway listening on port {UDP_PORT}")

    while True:
        data, addr = sock.recvfrom(1024)

        rx_time_ms = int(time.time() * 1000)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payload = data.decode("utf-8", errors="ignore")
        node_id, seq, tx_time_ms, rssi_dbm = parse_payload(payload)

        sender_ip, sender_port = addr

        with open(CSV_FILE, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                rx_time_ms,
                node_id,
                seq,
                tx_time_ms,
                rssi_dbm,
                payload,
                sender_ip,
                sender_port
            ])

        print(timestamp, node_id, seq, rssi_dbm)

if __name__ == "__main__":
    main()
