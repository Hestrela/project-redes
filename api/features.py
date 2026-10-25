from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite, nan
from statistics import median, quantiles, stdev
from typing import Sequence


FEATURES = (
    "z_robusto",
    "aumento_pct",
    "jitter_relativo",
    "perda_pct",
    "timeout_atual",
    "n5_timeout",
    "n5_aumento80",
    "n5_risco",
)
MIN_VALID_CALIBRATION_SAMPLES = 1500


@dataclass(frozen=True)
class Measurement:
    timestamp_utc: datetime
    enviados: int
    rtts_ms: tuple[float, ...]


class FeatureInputError(ValueError):
    pass


def _summarize(measurement: Measurement) -> dict[str, float | int | None]:
    if measurement.enviados < 1:
        raise FeatureInputError("Cada medição precisa ter pelo menos um pacote enviado.")
    if len(measurement.rtts_ms) > measurement.enviados:
        raise FeatureInputError("A quantidade de respostas não pode exceder os pacotes enviados.")
    if any(not isfinite(value) or value < 0 for value in measurement.rtts_ms):
        raise FeatureInputError("RTTs precisam ser números finitos e não negativos.")

    received = len(measurement.rtts_ms)
    rtt = sum(measurement.rtts_ms) / received if received else None
    jitter = stdev(measurement.rtts_ms) if received >= 2 else None
    loss_pct = (measurement.enviados - received) / measurement.enviados * 100.0

    return {
        "timestamp": measurement.timestamp_utc,
        "rtt_ms": rtt,
        "jitter_ms": jitter,
        "perda_pct": loss_pct,
        "timeout_atual": int(received == 0 or loss_pct >= 100.0),
    }


def _validate_order(measurements: Sequence[Measurement], label: str) -> None:
    timestamps = [item.timestamp_utc for item in measurements]
    if len(set(timestamps)) != len(timestamps):
        raise FeatureInputError(f"Há timestamps duplicados em {label}.")


def build_features(
    calibration_measurements: Sequence[Measurement],
    recent_measurements: Sequence[Measurement],
) -> dict[str, float | int]:
    """Build the model's eight t+12 features from raw packet RTT batches."""
    if not recent_measurements:
        raise FeatureInputError("Envie ao menos uma medição recente.")

    _validate_order(calibration_measurements, "calibracao")
    _validate_order(recent_measurements, "medicoes_recentes")

    calibration = sorted(calibration_measurements, key=lambda item: item.timestamp_utc)
    recent = sorted(recent_measurements, key=lambda item: item.timestamp_utc)
    if calibration and calibration[-1].timestamp_utc >= recent[0].timestamp_utc:
        raise FeatureInputError("A calibração precisa terminar antes das medições recentes.")

    calibration_rows = [_summarize(item) for item in calibration]
    valid_rtts = [row["rtt_ms"] for row in calibration_rows if row["rtt_ms"] is not None]
    if len(valid_rtts) < MIN_VALID_CALIBRATION_SAMPLES:
        raise FeatureInputError(
            "Baseline insuficiente: são necessárias pelo menos "
            f"{MIN_VALID_CALIBRATION_SAMPLES} medições com RTT válido."
        )

    baseline_median = median(valid_rtts)
    baseline_mad = median(abs(value - baseline_median) for value in valid_rtts)
    quartiles = quantiles(valid_rtts, n=4, method="inclusive")
    baseline_iqr = quartiles[2] - quartiles[0]
    valid_jitters = [
        row["jitter_ms"] for row in calibration_rows if row["jitter_ms"] is not None
    ]
    typical_jitter = median(valid_jitters) if valid_jitters else 0.0

    recent_rows = [_summarize(item) for item in recent[-5:]]
    for row in recent_rows:
        rtt = row["rtt_ms"]
        jitter = row["jitter_ms"]

        if rtt is None:
            row["z_robusto"] = nan
            row["aumento_pct"] = nan
        else:
            if baseline_mad == 0:
                denominator = max(baseline_iqr / 1.349, 1.0)
                robust_z = 0.0 if rtt == baseline_median else (rtt - baseline_median) / denominator
            else:
                robust_z = (rtt - baseline_median) / (1.4826 * baseline_mad)
            row["z_robusto"] = robust_z
            row["aumento_pct"] = (rtt - baseline_median) / baseline_median * 100.0

        if jitter is None:
            row["jitter_relativo"] = nan
        elif typical_jitter == 0:
            row["jitter_relativo"] = 1.0 if jitter == 0 else 3.0
        else:
            row["jitter_relativo"] = jitter / typical_jitter

        robust_z = row["z_robusto"]
        increase_pct = row["aumento_pct"]
        relative_jitter = row["jitter_relativo"]
        row["cond_risco"] = int(
            (2.0 <= robust_z < 3.5)
            or (30.0 <= increase_pct <= 80.0)
            or relative_jitter >= 3.0
        )
        row["cond_aumento80"] = int(increase_pct > 80.0)

    current = recent_rows[-1]
    return {
        "z_robusto": current["z_robusto"],
        "aumento_pct": current["aumento_pct"],
        "jitter_relativo": current["jitter_relativo"],
        "perda_pct": current["perda_pct"],
        "timeout_atual": current["timeout_atual"],
        "n5_timeout": sum(row["timeout_atual"] for row in recent_rows),
        "n5_aumento80": sum(row["cond_aumento80"] for row in recent_rows),
        "n5_risco": sum(row["cond_risco"] for row in recent_rows),
    }