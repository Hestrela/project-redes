from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Literal
from datetime import datetime, timedelta, timezone
from math import isfinite

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from api.features import FEATURES, FeatureInputError, Measurement, build_features
from api.ripe_atlas import (
    MAX_RESULTS_WINDOW_DAYS,
    RipeAtlasError,
    fetch_measurement_results,
    normalize_measurement_results,
    split_calibration_and_recent,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "predicao_12min" / "modelos" / "xgboost_t12.joblib"
CLASSES = ("OK", "RISCO", "FALHA")

app = FastAPI(
    title="API do Preditor de Falhas de Rede",
    version="0.1.0",
    description=(
        "Recebe medições brutas de ping, calcula as features do projeto e prevê "
        "a classe do fluxo 12 minutos à frente."
    ),
)


class MeasurementInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp_utc: datetime
    enviados: int = Field(ge=1)
    rtts_ms: list[float]

    @field_validator("timestamp_utc")
    @classmethod
    def timestamp_must_include_timezone(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("timestamp_utc precisa incluir fuso horário.")
        return value.astimezone(timezone.utc)

    @field_validator("rtts_ms")
    @classmethod
    def rtts_must_be_finite_and_nonnegative(cls, values: list[float]) -> list[float]:
        if any(not isfinite(value) or value < 0 for value in values):
            raise ValueError("RTTs precisam ser números finitos e não negativos.")
        return values

    @model_validator(mode="after")
    def received_cannot_exceed_sent(self) -> MeasurementInput:
        if len(self.rtts_ms) > self.enviados:
            raise ValueError("A quantidade de RTTs não pode exceder enviados.")
        return self


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fluxo_id: str = Field(min_length=1, max_length=200)
    calibracao: list[MeasurementInput] = Field(min_length=1)
    medicoes_recentes: list[MeasurementInput] = Field(min_length=1, max_length=5)


class RipeAtlasPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    measurement_id: int = Field(gt=0)
    probe_id: int | None = Field(default=None, gt=0)
    inicio_utc: datetime | None = None
    fim_utc: datetime | None = None

    @field_validator("inicio_utc", "fim_utc")
    @classmethod
    def optional_times_must_include_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("inicio_utc e fim_utc precisam incluir fuso horário.")
        return value.astimezone(timezone.utc) if value is not None else None

    @model_validator(mode="after")
    def validate_time_window(self) -> RipeAtlasPredictionRequest:
        if self.inicio_utc and self.fim_utc:
            duration = self.fim_utc - self.inicio_utc
            if duration <= timedelta(0):
                raise ValueError("fim_utc precisa ser posterior a inicio_utc.")
            if duration > timedelta(days=MAX_RESULTS_WINDOW_DAYS):
                raise ValueError("A janela consultada não pode exceder 14 dias.")
        return self


class PredictionResponse(BaseModel):
    fluxo_id: str
    classe_prevista: Literal["OK", "RISCO", "FALHA"]
    horizonte_minutos: Literal[12]
    previsto_para_utc: datetime
    probabilidades: dict[str, float]
    features_utilizadas: dict[str, float | int | None]
    modelo: str
    modelo_sha256: str


class RipeAtlasPredictionResponse(BaseModel):
    measurement_id: int
    fluxos_encontrados: int
    previsoes: list[PredictionResponse]
    fluxos_ignorados: list[dict[str, str]]


def _to_measurements(records: list[MeasurementInput]) -> list[Measurement]:
    return [
        Measurement(
            timestamp_utc=record.timestamp_utc,
            enviados=record.enviados,
            rtts_ms=tuple(record.rtts_ms),
        )
        for record in records
    ]


def _infer_t12(
    fluxo_id: str,
    latest_timestamp: datetime,
    features: dict[str, float | int],
) -> PredictionResponse:
    try:
        import pandas as pd

        model = _load_model()
        feature_frame = pd.DataFrame([features], columns=FEATURES)
        class_index = int(model.predict(feature_frame)[0])
        probability_values = model.predict_proba(feature_frame)[0]
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="O modelo t+12 não está disponível para inferência.",
        ) from exc

    if class_index < 0 or class_index >= len(CLASSES) or len(probability_values) != len(CLASSES):
        raise HTTPException(status_code=503, detail="Saída inesperada do modelo t+12.")

    probabilities = {
        label: float(probability_values[index])
        for index, label in enumerate(CLASSES)
    }
    response_features = {
        name: (None if not isfinite(value) else value)
        for name, value in features.items()
    }
    return PredictionResponse(
        fluxo_id=fluxo_id,
        classe_prevista=CLASSES[class_index],
        horizonte_minutos=12,
        previsto_para_utc=latest_timestamp + timedelta(minutes=12),
        probabilidades=probabilities,
        features_utilizadas=response_features,
        modelo="xgboost_t12",
        modelo_sha256=_model_sha256() or "",
    )


@lru_cache(maxsize=1)
def _load_model():
    if not MODEL_PATH.is_file():
        raise RuntimeError(f"Artefato do modelo não encontrado: {MODEL_PATH}")

    import joblib

    return joblib.load(MODEL_PATH)


def _model_sha256() -> str | None:
    if not MODEL_PATH.is_file():
        return None
    return sha256(MODEL_PATH.read_bytes()).hexdigest()


@app.get("/api/v1/saude")
def health() -> dict[str, str | bool]:
    try:
        _load_model()
    except Exception:
        return {"api": "ok", "modelo_disponivel": False}
    return {"api": "ok", "modelo_disponivel": True}


@app.get("/api/v1/modelo")
def model_info() -> dict[str, object]:
    return {
        "nome": "XGBoost",
        "horizonte_minutos": 12,
        "features": list(FEATURES),
        "classes": list(CLASSES),
        "arquivo": MODEL_PATH.name,
        "sha256": _model_sha256(),
    }


@app.post("/api/v1/previsoes/t12", response_model=PredictionResponse)
def predict_t12(request: PredictionRequest) -> PredictionResponse:
    try:
        features = build_features(
            _to_measurements(request.calibracao),
            _to_measurements(request.medicoes_recentes),
        )
    except FeatureInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    latest_timestamp = max(item.timestamp_utc for item in request.medicoes_recentes)
    return _infer_t12(request.fluxo_id, latest_timestamp, features)


@app.post(
    "/api/v1/previsoes/ripe-atlas",
    response_model=RipeAtlasPredictionResponse,
)
def predict_ripe_atlas(
    request: RipeAtlasPredictionRequest,
) -> RipeAtlasPredictionResponse:
    if request.inicio_utc and request.fim_utc:
        start_utc = request.inicio_utc
        stop_utc = request.fim_utc
    elif request.inicio_utc:
        start_utc = request.inicio_utc
        stop_utc = start_utc + timedelta(days=MAX_RESULTS_WINDOW_DAYS)
    else:
        stop_utc = request.fim_utc or datetime.now(timezone.utc)
        start_utc = stop_utc - timedelta(days=MAX_RESULTS_WINDOW_DAYS)

    try:
        raw_results = fetch_measurement_results(
            request.measurement_id,
            start_utc,
            stop_utc,
            request.probe_id,
        )
    except RipeAtlasError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    flows = normalize_measurement_results(raw_results)
    if request.probe_id is not None:
        probe_prefix = f"{request.probe_id}|"
        flows = {
            flow_id: measurements
            for flow_id, measurements in flows.items()
            if flow_id.startswith(probe_prefix)
        }

    if not flows:
        detail = "Nenhum resultado encontrado para a medição/probe informado."
        raise HTTPException(status_code=404, detail=detail)

    predictions: list[PredictionResponse] = []
    skipped_flows: list[dict[str, str]] = []
    for flow_id, measurements in sorted(flows.items()):
        calibration, recent = split_calibration_and_recent(measurements)
        try:
            features = build_features(calibration, recent)
        except FeatureInputError as exc:
            skipped_flows.append({"fluxo_id": flow_id, "motivo": str(exc)})
            continue

        predictions.append(
            _infer_t12(
                flow_id,
                recent[-1].timestamp_utc,
                features,
            )
        )

    if not predictions:
        raise HTTPException(
            status_code=422,
            detail={
                "mensagem": "Nenhum fluxo tem dados suficientes para previsão t+12.",
                "fluxos_ignorados": skipped_flows,
            },
        )

    return RipeAtlasPredictionResponse(
        measurement_id=request.measurement_id,
        fluxos_encontrados=len(flows),
        previsoes=predictions,
        fluxos_ignorados=skipped_flows,
    )