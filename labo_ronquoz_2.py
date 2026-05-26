from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ronquoz_common import (
    BUILDINGS_GEOJSON,
    ELEC_CONSUMPTION_FILE,
    RESULTS_DIR,
    ensure_dir,
    hourly_index,
    load_geojson,
    safe_divide,
    write_geojson,
)

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/PVcalc"
PV_LAT = 46.2246
PV_LON = 7.3600
PV_YEAR = 2023
PV_TILT = 15
PV_LOSS = 10
PV_KWP_PER_M2 = 0.165


def fetch_pvgis_profile(cache_path: Path, aspect: int) -> np.ndarray:
    if cache_path.exists():
        data = pd.read_csv(cache_path)
        return data["kwh_per_kwp"].to_numpy()

    import requests

    params = {
        "lat": PV_LAT,
        "lon": PV_LON,
        "peakpower": 1,
        "loss": PV_LOSS,
        "angle": PV_TILT,
        "aspect": aspect,
        "outputformat": "json",
        "startyear": PV_YEAR,
        "endyear": PV_YEAR,
        "mountingplace": "building",
    }
    def fallback_profile(hours: int = 8760, annual_kwh_per_kwp: float = 1100) -> np.ndarray:
        t = np.arange(hours)
        day = (t % 24) / 24.0
        year = t / hours
        shift = -2 / 24 if aspect < 0 else 2 / 24
        daily = np.sin(np.pi * ((day - 0.25 + shift) % 1))
        daily = np.clip(daily, 0, None)
        seasonal = 0.6 + 0.4 * np.sin(2 * np.pi * (year - 0.25))
        profile = daily * seasonal
        if profile.sum() > 0:
            profile = profile / profile.sum() * annual_kwh_per_kwp
        return profile

    try:
        response = requests.get(PVGIS_URL, params=params, timeout=60)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        kwh = fallback_profile()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame({"kwh_per_kwp": kwh}).to_csv(cache_path, index=False)
        return kwh

    hourly = payload.get("outputs", {}).get("hourly", [])
    df = pd.DataFrame(hourly)
    if "P" in df.columns:
        kwh = df["P"].astype(float) / 1000
    elif "power" in df.columns:
        kwh = df["power"].astype(float) / 1000
    elif "E" in df.columns:
        kwh = df["E"].astype(float)
    else:
        raise ValueError("Impossible d'extraire la production PVGIS.")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"kwh_per_kwp": kwh}).to_csv(cache_path, index=False)
    return kwh.to_numpy()


def main() -> None:
    base_geojson, buildings = load_geojson(BUILDINGS_GEOJSON)
    lab1_geojson = RESULTS_DIR / "lab1" / "buildings_energy.geojson"
    if lab1_geojson.exists():
        base_geojson, buildings = load_geojson(lab1_geojson)

    elec_df = pd.read_excel(ELEC_CONSUMPTION_FILE, sheet_name="resume")
    elec_df = elec_df.set_index("ID-BAT")
    elec_df.columns = elec_df.columns.astype(str)

    building_ids = buildings["id_unique"].astype(str).tolist()
    elec_values = elec_df.reindex(columns=building_ids).fillna(0).to_numpy()

    cache_dir = ensure_dir(RESULTS_DIR / "lab2" / "pvgis_cache")
    east_profile = fetch_pvgis_profile(cache_dir / "east.csv", aspect=-90)
    west_profile = fetch_pvgis_profile(cache_dir / "west.csv", aspect=90)

    if len(east_profile) != elec_values.shape[0]:
        raise ValueError("Le profil PVGIS ne correspond pas aux 8760 heures.")

    surface_pv = buildings["surface_pv"].fillna(0).astype(float).to_numpy()
    kwp = surface_pv * PV_KWP_PER_M2

    pv_profiles = (kwp / 2)[:, None] * (east_profile + west_profile)
    pv_profiles_t = pv_profiles.T

    self_consumed = np.minimum(pv_profiles_t, elec_values)
    pv_annual = pv_profiles.sum(axis=1)
    elec_annual = elec_values.sum(axis=0)
    self_annual = self_consumed.sum(axis=0)

    buildings = buildings.copy()
    buildings["pv_annual_kwh"] = pv_annual
    buildings["elec_annual_kwh"] = elec_annual
    buildings["autoconsumption"] = [safe_divide(sc, pv) for sc, pv in zip(self_annual, pv_annual)]
    buildings["autonomy"] = [safe_divide(sc, load) for sc, load in zip(self_annual, elec_annual)]

    results_dir = ensure_dir(RESULTS_DIR / "lab2")
    write_geojson(results_dir / "buildings_electricity.geojson", base_geojson, buildings)

    district_load = elec_values.sum(axis=1)
    district_pv = pv_profiles_t.sum(axis=1)
    district_self = np.minimum(district_load, district_pv)

    district_profile = pd.DataFrame(
        {
            "time": hourly_index(len(district_load)),
            "load_kw": district_load,
            "pv_kw": district_pv,
            "self_consumed_kw": district_self,
        }
    )
    district_profile.to_csv(results_dir / "district_profile.csv", index=False)

    surplus = district_pv - district_load
    soc = np.cumsum(surplus)
    storage_capacity_kwh = float(soc.max() - soc.min())

    summary = {
        "district_load_kwh": float(district_load.sum()),
        "district_pv_kwh": float(district_pv.sum()),
        "district_autoconsumption": safe_divide(district_self.sum(), district_pv.sum()),
        "district_autonomy": safe_divide(district_self.sum(), district_load.sum()),
        "storage_capacity_kwh_for_100pct_autoconsumption": storage_capacity_kwh,
    }
    with (results_dir / "district_summary.json").open("w") as handle:
        json.dump(summary, handle, indent=2)

    building_summary = buildings[["id_unique", "affect", "etat", "elec_annual_kwh", "pv_annual_kwh", "autoconsumption", "autonomy"]]
    building_summary.to_csv(results_dir / "building_electricity_summary.csv", index=False)

    try:
        import matplotlib.pyplot as plt

        admin_ids = buildings[(buildings["affect"] == "Administration") & (buildings["etat"] == "Nouveau")][
            "id_unique"
        ]
        industry_ids = buildings[(buildings["affect"] == "Industries") & (buildings["etat"] == "Nouveau")][
            "id_unique"
        ]

        if not admin_ids.empty and not industry_ids.empty:
            admin_id = admin_ids.iloc[0]
            industry_id = industry_ids.iloc[0]

            time_index = hourly_index(elec_values.shape[0])
            elec_time = pd.DataFrame(elec_values, index=time_index, columns=building_ids)

            def week_slice(start: str) -> pd.Series:
                end = pd.Timestamp(start) + pd.Timedelta(days=7)
                return elec_time.loc[start:end - pd.Timedelta(hours=1)]

            weeks = {
                "winter": week_slice("2023-01-01"),
                "midseason": week_slice("2023-04-01"),
                "summer": week_slice("2023-07-01"),
            }

            fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
            for ax, (label, week) in zip(axes, weeks.items()):
                ax.plot(week.index, week[admin_id], label=f"Administration ({label})")
                ax.plot(week.index, week[industry_id], label=f"Industries ({label})")
                ax.set_ylabel("kW")
                ax.legend()
            axes[-1].set_xlabel("Heure")
            fig.tight_layout()
            fig.savefig(results_dir / "typical_week_profiles.png", dpi=150)
            plt.close(fig)
    except ImportError:
        pass


if __name__ == "__main__":
    main()
