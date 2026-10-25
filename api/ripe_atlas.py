from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import isfinite
from typing import Any

import requests

from api.features import Measurement


RESULTS_URL = "https://atlas.ripe.net/api/v2/measurements/{measurement_id}/results/"
CALIBRATION_DAYS = 7
MAX_RESULTS_WINDOW_DAYS = 14
RIPE_MAX_CHUNK_DAYS = 6


class RipeAtlasError(RuntimeError):
    def __init__(self, detail: str, status_code: int = 502) -> None:
        super().__init__(detail)
        self.status_code = status_code


def fetch_measurement_results(
    measurement_id: int,
    start_utc: datetime,
    stop_utc: datetime,
    probe_id: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch public RIPE Atlas results; no write-capable API key is used."""
    url = RESULTS_URL.format(measurement_id=measurement_id)
    chunk_size = timedelta(days=RIPE_MAX_CHUNK_DAYS)
    results: list[dict[str, Any]] = []
    chunk_start = start_utc

    while chunk_start < stop_utc:
        chunk_stop = min(chunk_start + chunk_size, stop_utc)
        params = {
            "start": int(chunk_start.timestamp()),
            "stop": int(chunk_stop.timestamp()),
        }
        if probe_id is not None:
            params["probe_ids"] = probe_id

        try:
            response = requests.get(url, params=params, timeout=(5, 30))
        except requests.RequestException as exc:
            raise RipeAtlasError("Não foi possível consultar o RIPE Atlas.", 502) from exc

        if response.status_code == 404:
            raise RipeAtlasError("Measurement ID não encontrada no RIPE Atlas.", 404)
        if response.status_code == 429:
            raise RipeAtlasError(
                "Limite de consultas do RIPE Atlas atingido; tente novamente.", 503
            )
        if not response.ok:
            raise RipeAtlasError(
                f"RIPE Atlas respondeu com HTTP {response.status_code}.", 502
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise RipeAtlasError("RIPE Atlas retornou um JSON inválido.", 502) from exc

        if not isinstance(payload, list):
            raise RipeAtlasError(
                "A resposta do RIPE Atlas não é uma lista de resultados.", 502
            )
        results.extend(payload)
        chunk_start = chunk_stop

    return results


def normalize_measurement_results(
    records: list[dict[str, Any]],
) -> dict[str, list[Measurement]]:
    """Convert RIPE result rows into timestamped ping batches per probe/target."""
    unique_records: dict[tuple[str, str, datetime], Measurement] = {}

    for record in records:
        try:
            probe_id = str(int(record["prb_id"]))
            destination = str(record["dst_addr"])
            timestamp = datetime.fromtimestamp(float(record["timestamp"]), timezone.utc)
            sent = int(record["sent"])
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            continue

        if not destination or sent < 1:
            continue

        raw_results = record.get("result")
        if not isinstance(raw_results, list):
            raw_results = []

        rtts: list[float] = []
        for item in raw_results:
            if not isinstance(item, dict) or "rtt" not in item:
                continue
            try:
                rtt = float(item["rtt"])
            except (TypeError, ValueError, OverflowError):
                continue
            if isfinite(rtt) and rtt > 0:
                rtts.append(rtt)

        measurement = Measurement(
            timestamp_utc=timestamp,
            enviados=sent,
            rtts_ms=tuple(rtts[:sent]),
        )
        unique_records[(probe_id, destination, timestamp)] = measurement

    flows: dict[str, list[Measurement]] = defaultdict(list)
    for (probe_id, destination, _), measurement in unique_records.items():
        flows[f"{probe_id}|{destination}"].append(measurement)

    return {
        flow_id: sorted(measurements, key=lambda item: item.timestamp_utc)
        for flow_id, measurements in flows.items()
    }


def split_calibration_and_recent(
    measurements: list[Measurement],
) -> tuple[list[Measurement], list[Measurement]]:
    """Use the first seven days of each flow as its frozen training baseline."""
    if not measurements:
        return [], []

    ordered = sorted(measurements, key=lambda item: item.timestamp_utc)
    calibration_end = ordered[0].timestamp_utc + timedelta(days=CALIBRATION_DAYS)
    calibration = [item for item in ordered if item.timestamp_utc < calibration_end]
    recent = [item for item in ordered if item.timestamp_utc >= calibration_end]
    return calibration, recent[-5:]