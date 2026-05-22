import argparse
import pandas as pd


def analyze_energy(energy_log, packet_summary, output_file, duration_s):
    energy_df = pd.read_csv(energy_log)
    packet_df = pd.read_csv(packet_summary)

    required_energy_cols = {"packet_rate_pps", "trial", "current_ma", "voltage_v"}
    required_packet_cols = {"packet_rate_pps", "trial", "received_packets"}

    missing_energy = required_energy_cols - set(energy_df.columns)
    missing_packet = required_packet_cols - set(packet_df.columns)

    if missing_energy:
        raise ValueError(f"Energy log is missing columns: {missing_energy}")

    if missing_packet:
        raise ValueError(f"Packet summary is missing columns: {missing_packet}")

    energy_summary = (
        energy_df
        .groupby(["packet_rate_pps", "trial"])
        .agg(
            current_ma=("current_ma", "mean"),
            voltage_v=("voltage_v", "mean"),
        )
        .reset_index()
    )

    final_df = energy_summary.merge(
        packet_df[["packet_rate_pps", "trial", "received_packets"]],
        on=["packet_rate_pps", "trial"],
        how="left"
    )

    if final_df["received_packets"].isna().any():
        missing_rows = final_df[final_df["received_packets"].isna()]
        raise ValueError(
            "Some energy rows do not have matching packet summary rows:\n"
            f"{missing_rows}"
        )

    final_df["duration_s"] = duration_s

    final_df["energy_j"] = (
        (final_df["current_ma"] / 1000) *
        final_df["voltage_v"] *
        final_df["duration_s"]
    )

    final_df["energy_per_packet_j"] = final_df.apply(
        lambda row: row["energy_j"] / row["received_packets"]
        if row["received_packets"] > 0 else None,
        axis=1
    )

    final_df = final_df[
        [
            "packet_rate_pps",
            "trial",
            "current_ma",
            "voltage_v",
            "duration_s",
            "received_packets",
            "energy_j",
            "energy_per_packet_j",
        ]
    ]

    final_df = final_df.round({
        "current_ma": 2,
        "voltage_v": 2,
        "duration_s": 2,
        "energy_j": 4,
        "energy_per_packet_j": 6,
    })

    final_df.to_csv(output_file, index=False)
    print(final_df.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate final energy scenario CSV from ESP32 SD energy log and packet summary."
    )

    parser.add_argument("--energy-log", required=True)
    parser.add_argument("--packet-summary", required=True)
    parser.add_argument("--output", required=True)

    parser.add_argument(
        "--duration-s",
        type=float,
        default=10.0,
        help="Fixed experiment duration in seconds. Default: 10.0"
    )

    args = parser.parse_args()

    analyze_energy(
        energy_log=args.energy_log,
        packet_summary=args.packet_summary,
        output_file=args.output,
        duration_s=args.duration_s
    )