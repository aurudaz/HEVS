from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent
LAB1_DIR = ROOT_DIR / "Laboratoire Ronquoz - 1"
LAB2_DIR = ROOT_DIR / "Laboratoire Ronquoz - 2"
LAB3_DIR = ROOT_DIR / "Laboratoire Ronquoz - 3"
RESULTS_DIR = ROOT_DIR / "results"

BUILDINGS_GEOJSON = LAB1_DIR / "buildings_parameters.geojson"
SIA_FILE = LAB1_DIR / "valeurs_limite_SIA_380_1.xlsx"
WEATHER_FILE = LAB1_DIR / "Sion_weather_2030_MeteoSuisse.xlsx"
ELEC_CONSUMPTION_FILE = LAB2_DIR / "elec_consumption.xlsx"

AFFECTATION_TO_SIA = {
    "Habitat collectif": "Habitat collectif",
    "Administration": "Administration",
    "Ecole": "Ecole",
    "Commerce": "Commerce",
    "Industries": "Industries",
    "Installation sportive": "Installation sportive",
    "Non chauffé": "Non chauffé",
}

FOISONNEMENT_FACTORS = {
    "Habitat collectif": 0.8,
    "Administration": 0.75,
    "Ecole": 0.75,
    "Commerce": 0.8,
    "Industries": 0.9,
    "Installation sportive": 0.75,
    "Non chauffé": 0.0,
}

THERMAL_INERTIA_HOURS = {
    "Habitat collectif": 6.0,
    "Administration": 4.0,
    "Ecole": 4.0,
    "Commerce": 3.0,
    "Industries": 2.0,
    "Installation sportive": 3.0,
    "Non chauffé": 0.0,
}


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_geojson(path: Path) -> Tuple[dict, pd.DataFrame]:
    with path.open() as handle:
        data = json.load(handle)
    features = data.get("features", [])
    properties = [feature.get("properties", {}) for feature in features]
    return data, pd.DataFrame(properties)


def write_geojson(path: Path, data: dict, df: pd.DataFrame) -> None:
    df = df.where(pd.notnull(df), None)
    features = data.get("features", [])
    for feature, (_, row) in zip(features, df.iterrows()):
        feature.setdefault("properties", {}).update(row.to_dict())
    ensure_dir(path.parent)
    with path.open("w") as handle:
        json.dump(data, handle, ensure_ascii=False)


def load_weather_series() -> pd.Series:
    weather = pd.read_excel(WEATHER_FILE, sheet_name=0)
    return weather["tre200h0"].astype(float)


def load_sia_tables() -> Dict[str, pd.DataFrame]:
    tables = {
        "Qhli_0": pd.read_excel(SIA_FILE, sheet_name="Qhli_0"),
        "delta_Qhli": pd.read_excel(SIA_FILE, sheet_name="delta_Qhli"),
        "ECS": pd.read_excel(SIA_FILE, sheet_name="ECS"),
    }
    return {key: table.set_index("Norme") for key, table in tables.items()}


def norme_from_year(year: int) -> str:
    if year <= 2001:
        return "SIA 380/1 1988-2001"
    if year <= 2007:
        return "SIA 380/1 2001"
    if year <= 2009:
        return "SIA 380/1 2007"
    return "SIA 380/1 2016"


def apply_thermal_inertia(profile: np.ndarray, tau_hours: float) -> np.ndarray:
    if tau_hours <= 0:
        return profile
    alpha = 1 - np.exp(-1 / tau_hours)
    smoothed = np.zeros_like(profile)
    smoothed[0] = profile[0]
    for idx in range(1, len(profile)):
        smoothed[idx] = smoothed[idx - 1] + alpha * (profile[idx] - smoothed[idx - 1])
    total = profile.sum()
    if total > 0 and smoothed.sum() > 0:
        smoothed *= total / smoothed.sum()
    return smoothed


def hourly_index(hours: int) -> pd.DatetimeIndex:
    return pd.date_range("2023-01-01", periods=hours, freq="h")


def get_foisonnement(affect: str) -> float:
    return FOISONNEMENT_FACTORS.get(affect, 0.8)


def get_inertia(affect: str) -> float:
    return THERMAL_INERTIA_HOURS.get(affect, 4.0)


def map_affectation(affect: str) -> str:
    return AFFECTATION_TO_SIA.get(affect, affect)


def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
