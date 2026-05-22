import time
import csv
from datetime import datetime
from SX127x.LoRa import *
from SX127x.board_config import BOARD

BOARD.setup()

CSV_FILE = "lora_received_packets.csv"

class LoRaGateway(LoRa):
    def __init__(self, verbose=False):
        super(LoRaGateway, self).__init__(verbose)

        self.set_mode(MODE.SLEEP)
        self.set_dio_mapping([0] * 6)

        self.set_freq(868.0)
        self.set_bw(BW.BW125)
        self.set_spreading_factor(7)
        self.set_coding_rate(CODING_RATE.CR4_5)

        print("LoRa gateway initialized")

    def start(self):
        self.reset_ptr_rx()
        self.set_mode(MODE.RXCONT)

        print("Waiting for LoRa packets...")

        while True:
            time.sleep(0.1)

    def on_rx_done(self):
        self.clear_irq_flags(RxDone=1)

        payload = bytes(self.read_payload(nocheck=True)).decode(
            "utf-8",
            errors="ignore"
        )

        rssi = self.get_pkt_rssi_value()
        snr = self.get_pkt_snr_value()

        rx_time_ms = int(time.time() * 1000)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        parts = payload.strip().split(",")
        node_id = parts[0] if len(parts) > 0 else ""
        seq = parts[1] if len(parts) > 1 else ""
        tx_time_ms = parts[2] if len(parts) > 2 else ""

        with open(CSV_FILE, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                rx_time_ms,
                node_id,
                seq,
                tx_time_ms,
                rssi,
                snr,
                payload
            ])

        print(
            f"{timestamp},{node_id},{seq},RSSI={rssi},SNR={snr},payload={payload}"
        )

        self.reset_ptr_rx()
        self.set_mode(MODE.RXCONT)

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
            "snr_db",
            "payload_raw"
        ])

if __name__ == "__main__":
    create_csv()

    gateway = LoRaGateway(verbose=False)

    try:
        gateway.start()
    except KeyboardInterrupt:
        print("Stopping LoRa gateway...")
        BOARD.teardown()
