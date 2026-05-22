import asyncio
import csv
import time
from datetime import datetime
from bleak import BleakScanner, BleakClient

SERVICE_UUID = "xxxxxxxxxxxxxxxxxxxx"
CHARACTERISTIC_UUID = "xxxxxxxxxxxxxxxxxxxxxxxxxx"

CSV_FILE = "ble_received_packets.csv"

latest_rssi_by_address = {}

def create_csv():
    with open(CSV_FILE, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "rx_time_ms",
            "node_id",
            "seq",
            "tx_time_ms",
            "payload_raw",
            "device_address",
            "rssi_dbm"
        ])


def parse_payload(payload):
    parts = payload.strip().split(",")

    node_id = parts[0] if len(parts) > 0 else ""
    seq = parts[1] if len(parts) > 1 else ""
    tx_time_ms = parts[2] if len(parts) > 2 else ""

    return node_id, seq, tx_time_ms


def make_notification_handler(device_address):
    def notification_handler(sender, data):
        rx_time_ms = int(time.time() * 1000)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payload = data.decode("utf-8", errors="ignore")
        node_id, seq, tx_time_ms = parse_payload(payload)

        # RSSI value from the latest BLE scan before connection
        rssi_dbm = latest_rssi_by_address.get(device_address, "")

        with open(CSV_FILE, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                timestamp,
                rx_time_ms,
                node_id,
                seq,
                tx_time_ms,
                payload,
                device_address,
                rssi_dbm
            ])

        print(f"{timestamp},{node_id},{seq},{payload},{device_address},{rssi_dbm}")

    return notification_handler


async def find_ble_node():
    found_device = None

    def detection_callback(device, advertisement_data):
        nonlocal found_device

        # Store latest RSSI for every scanned BLE device
        latest_rssi_by_address[device.address] = advertisement_data.rssi

        if device.name and "BLE_IOT_NODE" in device.name:
            found_device = device

    scanner = BleakScanner(detection_callback)
    await scanner.start()
    await asyncio.sleep(10)
    await scanner.stop()

    return found_device


async def main():
    create_csv()

    while True:
        device = await find_ble_node()

        if device is None:
            print("No BLE node found. Retrying...")
            await asyncio.sleep(5)
            continue

        try:
            rssi_dbm = latest_rssi_by_address.get(device.address, "")
            print(f"Found BLE node: {device.address}, RSSI: {rssi_dbm} dBm")

            async with BleakClient(device.address) as client:
                print(f"Connected to {device.address}")

                await client.start_notify(
                    CHARACTERISTIC_UUID,
                    make_notification_handler(device.address)
                )

                while client.is_connected:
                    await asyncio.sleep(1)

        except Exception as e:
            print(f"BLE error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
