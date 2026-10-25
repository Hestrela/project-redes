import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

inicio = datetime(2026, 10, 1, tzinfo=timezone.utc)

payload = {
    "fluxo_id": "teste-ripe-123",
    "calibracao": [
        {
            "timestamp_utc": (inicio + timedelta(seconds=240 * i))
            .isoformat()
            .replace("+00:00", "Z"),
            "enviados": 4,
            "rtts_ms": [21.2, 20.9, 21.5, 21.1],
        }
        for i in range(1500)
    ],
    "medicoes_recentes": [
        {
            "timestamp_utc": (
                inicio + timedelta(seconds=240 * (1500 + i))
            ).isoformat().replace("+00:00", "Z"),
            "enviados": 4,
            "rtts_ms": [21.2, 20.9, 21.5, 21.1],
        }
        for i in range(5)
    ],
}

output_path = Path(__file__).with_name("payload_teste_t12.json")
output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

print(f"JSON gerado: {output_path}")
print(f"Calibracao: {len(payload['calibracao'])} medicoes")
print(f"Medicoes recentes: {len(payload['medicoes_recentes'])}")