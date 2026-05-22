import argparse
import pandas as pd


def apply_min_delay_offset(df):
    df = df.copy()
    df["raw_delay_ms"] = df["rx_time_ms"] - df["tx_time_ms"]
    df["clock_offset_ms"] = df.groupby("node_id")["raw_delay_ms"].transform("min")
    df["delay_ms"] = df["raw_delay_ms"] - df["clock_offset_ms"]
    return df


def analyze_packets(
    input_file,
    output_file,
    packet_size_bytes,
    expected_packets_per_node,
    scenario,
    trial,
    packet_rate_pps=None,
    distance=None,
    distance_unit="m",
    include_pdr=False,
):
    df = pd.read_csv(input_file)

    required_cols = {"node_id", "seq", "tx_time_ms", "rx_time_ms"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")

    df["node_id"] = df["node_id"].astype(str)
    df["seq"] = pd.to_numeric(df["seq"], errors="coerce")
    df["tx_time_ms"] = pd.to_numeric(df["tx_time_ms"], errors="coerce")
    df["rx_time_ms"] = pd.to_numeric(df["rx_time_ms"], errors="coerce")

    if "rssi_dbm" in df.columns:
        df["rssi_dbm"] = pd.to_numeric(df["rssi_dbm"], errors="coerce")

    if "snr_db" in df.columns:
        df["snr_db"] = pd.to_numeric(df["snr_db"], errors="coerce")

    df = df.dropna(subset=["seq", "tx_time_ms", "rx_time_ms"])
    df = apply_min_delay_offset(df)

    rows = []

    for node_id, group in df.groupby("node_id"):
        received_packets = group["seq"].nunique()
        sent_packets = expected_packets_per_node

        duration_s = expected_packets_per_node / packet_rate_pps

        throughput_kbps = received_packets * packet_size_bytes * 8 / duration_s / 1000

        row = {
            "sent_packets": sent_packets,
            "received_packets": received_packets,
        }

        if include_pdr:
            pdr = received_packets / sent_packets if sent_packets > 0 else 0
            row["pdr"] = pdr
            row["pdr_percent"] = pdr * 100

        if scenario == "distance":
            if distance is None:
                raise ValueError("--distance is required for distance scenario")

            distance_col = "distance_km" if distance_unit == "km" else "distance_m"

            row = {
                distance_col: distance,
                "trial": trial,
                **row,
            }

            if "rssi_dbm" in group.columns:
                row["rssi_dbm"] = group["rssi_dbm"].mean()

            if "snr_db" in group.columns:
                row["snr_db"] = group["snr_db"].mean()

            row["delay_ms"] = group["delay_ms"].mean()

        elif scenario == "throughput":
            if packet_rate_pps is None:
                raise ValueError("--packet-rate is required for throughput scenario")

            row = {
                "packet_rate_pps": packet_rate_pps,
                "trial": trial,
                **row,
                "throughput_kbps": throughput_kbps,
                "delay_ms": group["delay_ms"].mean(),
            }

        else:
            raise ValueError("scenario must be one of: distance, throughput")

        rows.append(row)

    result_df = pd.DataFrame(rows)
    result_df.to_csv(output_file, index=False)

    print(result_df.round(4).to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--packet-size", type=int, required=True)
    parser.add_argument("--expected-packets", type=int, required=True)

    parser.add_argument(
        "--scenario",
        required=True,
        choices=["distance", "throughput"],
    )

    parser.add_argument("--trial", type=int, required=True)

    parser.add_argument("--packet-rate", type=float, default=None)
    parser.add_argument("--distance", type=float, default=None)
    parser.add_argument("--distance-unit", choices=["m", "km"], default="m")

    parser.add_argument(
        "--include-pdr",
        action="store_true",
    )

    args = parser.parse_args()

    analyze_packets(
        input_file=args.input,
        output_file=args.output,
        packet_size_bytes=args.packet_size,
        expected_packets_per_node=args.expected_packets,
        scenario=args.scenario,
        trial=args.trial,
        packet_rate_pps=args.packet_rate,
        distance=args.distance,
        distance_unit=args.distance_unit,
        include_pdr=args.include_pdr,
    )
