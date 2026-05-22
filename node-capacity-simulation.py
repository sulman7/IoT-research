from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TechnologyConfig:
    name: str
    packet_size_bytes: int
    base_rate_pps: float
    throughput_limit_kbps: float
    delay_load_coeff: float
    delay_node_coeff: float
    delay_jitter_ms: float
    pdr_floor: float


class IoTWirelessSimulator:

    def __init__(self, random_seed: int = 42) -> None:
        self.rng = np.random.default_rng(random_seed)

        #kiekvienos tech baseline rezultatai is pirmu eksperimentu
        self.tech = {
            "wifi": TechnologyConfig(
                name="Wi-Fi",
                packet_size_bytes=100,
                base_rate_pps=20.0,
                throughput_limit_kbps=22000.0,
                delay_load_coeff=0.013,
                delay_node_coeff=0.16,
                delay_jitter_ms=1.5,
                pdr_floor=0.80,
            ),
            "ble": TechnologyConfig(
                name="Bluetooth Low Energy",
                packet_size_bytes=100,
                base_rate_pps=15.0,
                throughput_limit_kbps=250.0,
                delay_load_coeff=0.020,
                delay_node_coeff=0.30,
                delay_jitter_ms=2.5,
                pdr_floor=0.80,
            ),
            "lora": TechnologyConfig(
                name="LoRa",
                packet_size_bytes=20,
                base_rate_pps=0.10,
                throughput_limit_kbps=0.20,
                delay_load_coeff=0.030,
                delay_node_coeff=0.12,
                delay_jitter_ms=10.0,
                pdr_floor=0.35,
            ),
        }

        self.distance_profiles: Dict[str, List[Dict[str, float]]] = {
            "wifi": [
                {"distance": 10.0, "pdr": 1.0000, "rssi": -46.0, "snr": 39.0, "delay_ms": 6.0},
                {"distance": 50.0, "pdr": 0.9110, "rssi": -66.0, "snr": 23.67, "delay_ms": 10.0},
                {"distance": 100.0, "pdr": 0.6667, "rssi": -80.0, "snr": 12.33, "delay_ms": 18.0},
            ],
            "ble": [
                {"distance": 5.0, "pdr": 1.0000, "rssi": -51.0, "snr": 34.0, "delay_ms": 8.0},
                {"distance": 20.0, "pdr": 0.8447, "rssi": -71.0, "snr": 19.0, "delay_ms": 15.0},
                {"distance": 50.0, "pdr": 0.5333, "rssi": -87.67, "snr": 8.0, "delay_ms": 26.0},
            ],
            "lora": [
                {"distance": 0.4, "pdr": 1.0000, "rssi": -93.0, "snr": 8.67, "delay_ms": 50.0},
                {"distance": 1.2, "pdr": 0.9110, "rssi": -105.67, "snr": 3.0, "delay_ms": 60.0},
                {"distance": 3.0, "pdr": 0.6667, "rssi": -117.67, "snr": -3.67, "delay_ms": 90.0},
            ],
        }

        self.throughput_profiles: Dict[str, List[Dict[str, float]]] = {
             "wifi": [
                {"pps": 10.0, "pdr": 0.9967, "throughput_kbps": 7.9733, "delay_ms": 8.0},
                {"pps": 20.0, "pdr": 0.9933, "throughput_kbps": 15.8933, "delay_ms": 8.0},
                {"pps": 30.0, "pdr": 0.9867, "throughput_kbps": 23.6800, "delay_ms": 9.0},
            ],
            "ble": [
                {"pps": 5.0, "pdr": 0.9933, "throughput_kbps": 3.9733, "delay_ms": 12.0},
                {"pps": 15.0, "pdr": 0.9533, "throughput_kbps": 11.4400, "delay_ms": 18.0},
                {"pps": 30.0, "pdr": 0.8700, "throughput_kbps": 20.8800, "delay_ms": 28.0},
            ],
            "lora": [
                {"pps": 0.1, "pdr": 1.0000, "throughput_kbps": 0.0160, "delay_ms": 60.0},
                {"pps": 0.5, "pdr": 0.9333, "throughput_kbps": 0.0747, "delay_ms": 80.0},
                {"pps": 1.0, "pdr": 0.8223, "throughput_kbps": 0.1317, "delay_ms": 110.0},
            ],
        }

        self.capacity_profiles: Dict[str, List[Dict[str, float]]] = {
            "wifi": [
                {"nodes": 1, "pdr": 1.0000, "throughput_kbps": 16.00, "delay_ms": 8.0},
                {"nodes": 2, "pdr": 0.9903, "throughput_kbps": 31.68, "delay_ms": 15.67},
                {"nodes": 3, "pdr": 0.9867, "throughput_kbps": 47.36, "delay_ms": 24.33},
            ],
            "ble": [
                {"nodes": 1, "pdr": 0.9850, "throughput_kbps": 15.76, "delay_ms": 13.0},
                {"nodes": 2, "pdr": 0.9317, "throughput_kbps": 29.81, "delay_ms": 24.67},
                {"nodes": 3, "pdr": 0.8420, "throughput_kbps": 40.40, "delay_ms": 38.33},
            ],
            "lora": [
                # Anchor LoRa small-node baseline to a realistic sparse-traffic case
                {"nodes": 1, "pdr": 0.9600, "throughput_kbps": 0.0160, "delay_ms": 60.0},
                {"nodes": 2, "pdr": 0.9300, "throughput_kbps": 0.0300, "delay_ms": 72.0},
                {"nodes": 3, "pdr": 0.9000, "throughput_kbps": 0.0430, "delay_ms": 88.0},
            ],
        }

    @staticmethod
    def _interpolate(x: float, points: List[Dict[str, float]], x_key: str, y_key: str) -> float:
        pts = sorted(points, key=lambda p: p[x_key])

        if x <= pts[0][x_key]:
            return pts[0][y_key]
        if x >= pts[-1][x_key]:
            x0, y0 = pts[-2][x_key], pts[-2][y_key]
            x1, y1 = pts[-1][x_key], pts[-1][y_key]
            slope = (y1 - y0) / (x1 - x0)
            return y1 + slope * (x - x1)

        for left, right in zip(pts[:-1], pts[1:]):
            if left[x_key] <= x <= right[x_key]:
                x0, y0 = left[x_key], left[y_key]
                x1, y1 = right[x_key], right[y_key]
                frac = (x - x0) / (x1 - x0)
                return y0 + frac * (y1 - y0)

        raise RuntimeError("Interpolation failed unexpectedly.")

    def baseline_from_distance(self, tech: str, distance: float) -> Dict[str, float]:
        profiles = self.distance_profiles[tech]
        return {
            "pdr": self._interpolate(distance, profiles, "distance", "pdr"),
            "rssi": self._interpolate(distance, profiles, "distance", "rssi"),
            "snr": self._interpolate(distance, profiles, "distance", "snr"),
            "delay_ms": self._interpolate(distance, profiles, "distance", "delay_ms"),
        }

    def baseline_from_rate(self, tech: str, packet_rate_pps: float) -> Dict[str, float]:
        profiles = self.throughput_profiles[tech]
        return {
            "pdr": self._interpolate(packet_rate_pps, profiles, "pps", "pdr"),
            "throughput_kbps": self._interpolate(packet_rate_pps, profiles, "pps", "throughput_kbps"),
            "delay_ms": self._interpolate(packet_rate_pps, profiles, "pps", "delay_ms"),
        }

    def baseline_from_nodes(self, tech: str, nodes: int) -> Dict[str, float]:
        profiles = self.capacity_profiles[tech]
        return {
            "pdr": self._interpolate(nodes, profiles, "nodes", "pdr"),
            "throughput_kbps": self._interpolate(nodes, profiles, "nodes", "throughput_kbps"),
            "delay_ms": self._interpolate(nodes, profiles, "nodes", "delay_ms"),
        }

    def simulate_capacity(
        self,
        tech: str,
        nodes: int,
        packets_per_node: int,
        packet_rate_pps: Optional[float] = None,
        distance: Optional[float] = None,
        runs: int = 30,
    ) -> pd.DataFrame:
        cfg = self.tech[tech]
        packet_rate_pps = float(packet_rate_pps if packet_rate_pps is not None else cfg.base_rate_pps)

        node_base = self.baseline_from_nodes(tech, max(1, min(nodes, 3)))
        rate_base = self.baseline_from_rate(tech, packet_rate_pps)

        if distance is not None:
            dist_base = self.baseline_from_distance(tech, distance)
            distance_scale = max(0.3, dist_base["pdr"] / max(1e-9, self.distance_profiles[tech][0]["pdr"]))
            base_pdr = min(node_base["pdr"], rate_base["pdr"]) * distance_scale
            rssi = dist_base["rssi"]
            snr = dist_base["snr"]
            base_delay = max(node_base["delay_ms"], rate_base["delay_ms"], dist_base["delay_ms"])
        else:
            base_pdr = min(node_base["pdr"], rate_base["pdr"])
            rssi = np.nan
            snr = np.nan
            base_delay = max(node_base["delay_ms"], rate_base["delay_ms"])

        extra_nodes = max(0, nodes - 3)

        # Normalize load against each technology baseline instead of using raw pps
        load_ratio = packet_rate_pps / max(cfg.base_rate_pps, 1e-9)
        extra_load_ratio = max(0.0, load_ratio - 1.0)

        if tech == "wifi":
            pdr_penalty = 0.004 * extra_nodes + 0.0012 * extra_load_ratio * math.sqrt(max(nodes, 1))
        elif tech == "ble":
            pdr_penalty = 0.018 * extra_nodes + 0.0030 * extra_load_ratio * math.sqrt(max(nodes, 1))
        else:  # lora
            pdr_penalty = 0.015 * extra_nodes + 0.010 * extra_load_ratio * math.sqrt(max(nodes, 1))

        effective_pdr = max(cfg.pdr_floor, min(0.999, base_pdr - pdr_penalty))

        results = []
        total_time_s = packets_per_node / packet_rate_pps if packet_rate_pps > 0 else 1.0
        packet_bits = cfg.packet_size_bytes * 8

        for run in range(1, runs + 1):
            sent = nodes * packets_per_node
            recv = int(self.rng.binomial(sent, effective_pdr))

            throughput_kbps = (recv * packet_bits / total_time_s) / 1000.0

            if throughput_kbps > cfg.throughput_limit_kbps:
                throughput_kbps = cfg.throughput_limit_kbps * self.rng.uniform(0.96, 1.00)

            offered_load = nodes * packet_rate_pps
            mean_delay = base_delay * (
                1.0
                + cfg.delay_load_coeff * offered_load
                + cfg.delay_node_coeff * max(0, nodes - 1)
            )
            avg_delay = max(1.0, self.rng.normal(mean_delay, cfg.delay_jitter_ms))

            out_rssi = rssi if np.isnan(rssi) else self.rng.normal(rssi, 1.5)
            out_snr = snr if np.isnan(snr) else self.rng.normal(snr, 0.9)

            results.append(
                {
                    "technology": tech,
                    "run": run,
                    "nodes": nodes,
                    "distance": distance,
                    "packet_rate_pps": packet_rate_pps,
                    "sent_packets": sent,
                    "received_packets": recv,
                    "pdr": recv / sent if sent > 0 else 0.0,
                    "throughput_kbps": throughput_kbps,
                    "avg_delay_ms": avg_delay,
                    "mean_rssi_dbm": out_rssi,
                    "mean_snr_db": out_snr,
                }
            )

        return pd.DataFrame(results)

    def simulate_distance(
        self,
        tech: str,
        distance: float,
        packets: int = 300,
        packet_rate_pps: Optional[float] = None,
        runs: int = 30,
    ) -> pd.DataFrame:
        cfg = self.tech[tech]
        packet_rate_pps = float(packet_rate_pps if packet_rate_pps is not None else cfg.base_rate_pps)
        dist = self.baseline_from_distance(tech, distance)
        rate = self.baseline_from_rate(tech, packet_rate_pps)

        effective_pdr = max(
            cfg.pdr_floor,
            min(0.999, dist["pdr"] * (rate["pdr"] / max(0.75, self.throughput_profiles[tech][0]["pdr"])))
        )
        mean_delay = max(dist["delay_ms"], rate["delay_ms"])
        total_time_s = packets / packet_rate_pps if packet_rate_pps > 0 else 1.0
        packet_bits = cfg.packet_size_bytes * 8

        rows = []
        for run in range(1, runs + 1):
            recv = int(self.rng.binomial(packets, effective_pdr))
            throughput_kbps = (recv * packet_bits / total_time_s) / 1000.0
            if throughput_kbps > cfg.throughput_limit_kbps:
                throughput_kbps = cfg.throughput_limit_kbps * self.rng.uniform(0.96, 1.00)

            avg_delay = max(1.0, self.rng.normal(mean_delay, cfg.delay_jitter_ms))
            rows.append(
                {
                    "technology": tech,
                    "run": run,
                    "distance": distance,
                    "packet_rate_pps": packet_rate_pps,
                    "sent_packets": packets,
                    "received_packets": recv,
                    "pdr": recv / packets,
                    "throughput_kbps": throughput_kbps,
                    "avg_delay_ms": avg_delay,
                    "mean_rssi_dbm": self.rng.normal(dist["rssi"], 1.5),
                    "mean_snr_db": self.rng.normal(dist["snr"], 0.9),
                }
            )

        return pd.DataFrame(rows)

    @staticmethod
    def summarize(df: pd.DataFrame, group_cols: List[str]) -> pd.DataFrame:
        return (
            df.groupby(group_cols)
            .agg(
                pdr_mean=("pdr", "mean"),
                pdr_std=("pdr", "std"),
                throughput_mean_kbps=("throughput_kbps", "mean"),
                throughput_std_kbps=("throughput_kbps", "std"),
                delay_mean_ms=("avg_delay_ms", "mean"),
                delay_std_ms=("avg_delay_ms", "std"),
            )
            .reset_index()
        )


if __name__ == "__main__":
    sim = IoTWirelessSimulator(random_seed=7)

    capacity_cases = {
        "wifi": {
            "nodes": [1, 2, 3, 5, 10, 20],
            "packets_per_node": 200,
            "packet_rate_pps": 20.0,
            "distance": None,
        },
        "ble": {
            "nodes": [1, 2, 3, 5, 10, 20],
            "packets_per_node": 200,
            "packet_rate_pps": 15.0,
            "distance": None,
        },
        "lora": {
            "nodes": [1, 2, 3, 5, 10, 20],
            "packets_per_node": 30,
            "packet_rate_pps": 0.1,
            "distance": 1.2,
        },
    }

    frames = []

    for tech, case in capacity_cases.items():
        for nodes in case["nodes"]:
            df = sim.simulate_capacity(
                tech=tech,
                nodes=nodes,
                packets_per_node=case["packets_per_node"],
                packet_rate_pps=case["packet_rate_pps"],
                distance=case["distance"],
                runs=30,
            )
            frames.append(df)

    capacity = pd.concat(frames, ignore_index=True)
    summary = sim.summarize(capacity, ["technology", "nodes"])

    thesis_table = summary.copy()

    # Use consistent thesis-friendly units.
    thesis_table["PDR (%)"] = thesis_table["pdr_mean"] * 100
    thesis_table["PDR std. nuokrypis (%)"] = thesis_table["pdr_std"] * 100

    thesis_table = thesis_table.rename(
        columns={
            "technology": "Technologija",
            "nodes": "IoT mazgų skaičius",
            "throughput_mean_kbps": "Pralaidumas (kbps)",
            "throughput_std_kbps": "Pralaidumo std. nuokrypis (kbps)",
            "delay_mean_ms": "Delsa (ms)",
            "delay_std_ms": "Delsos std. nuokrypis (ms)",
        }
    )

    thesis_table = thesis_table[
        [
            "Technologija",
            "IoT mazgų skaičius",
            "PDR (%)",
            "PDR std. nuokrypis (%)",
            "Pralaidumas (kbps)",
            "Pralaidumo std. nuokrypis (kbps)",
            "Delsa (ms)",
            "Delsos std. nuokrypis (ms)",
        ]
    ]

    tech_order = {"wifi": 0, "ble": 1, "lora": 2}
    thesis_table["_order"] = thesis_table["Technologija"].map(tech_order)
    thesis_table = thesis_table.sort_values(["_order", "IoT mazgų skaičius"])
    thesis_table = thesis_table.drop(columns=["_order"])

    thesis_table = thesis_table.round(
        {
            "PDR (%)": 2,
            "PDR std. nuokrypis (%)": 2,
            "Pralaidumas (kbps)": 4,
            "Pralaidumo std. nuokrypis (kbps)": 4,
            "Delsa (ms)": 2,
            "Delsos std. nuokrypis (ms)": 2,
        }
    )

    thesis_table.to_csv(
        "capacity_simulation_summary_for_thesis.csv",
        index=False,
    )

    for tech in ["wifi", "ble", "lora"]:
        print(f"\n{tech.upper()} capacity table:")
        print(
            thesis_table[thesis_table["Technologija"] == tech]
            .drop(columns=["Technologija"])
            .to_string(index=False)
        )

    print("\nSaved: capacity_simulation_summary_for_thesis.csv")
