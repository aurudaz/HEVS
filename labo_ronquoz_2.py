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


def add_energy_intensity(buildings: pd.DataFrame) -> pd.DataFrame:
    buildings = buildings.copy()
    sre = buildings.get("sre", pd.Series(0, index=buildings.index)).fillna(0).astype(float)
    default_series = pd.Series(0, index=buildings.index)
    heat = buildings.get("heat_ecs_annual_kwh", buildings.get("heat_annual_kwh", default_series))
    heat = heat.fillna(0).astype(float)
    elec = buildings.get("elec_annual_kwh", pd.Series(0, index=buildings.index)).fillna(0).astype(float)
    buildings["heat_kwh_per_sre"] = [safe_divide(val, s) for val, s in zip(heat, sre)]
    buildings["elec_kwh_per_sre"] = [safe_divide(val, s) for val, s in zip(elec, sre)]
    return buildings


def save_geopandas_maps(gdf, output_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return

    output_dir = ensure_dir(output_dir)
    gdf = gdf.copy()
    if "heat_ecs_annual_kwh" in gdf.columns:
        gdf["heat_mwh"] = gdf["heat_ecs_annual_kwh"].astype(float) / 1000
        heat_column = "heat_mwh"
    elif "heat_annual_kwh" in gdf.columns:
        gdf["heat_mwh"] = gdf["heat_annual_kwh"].astype(float) / 1000
        heat_column = "heat_mwh"
    else:
        heat_column = None
    if "elec_annual_kwh" in gdf.columns:
        gdf["elec_mwh"] = gdf["elec_annual_kwh"].astype(float) / 1000
    if "maxpowerqhw" in gdf.columns:
        gdf["maxpower_kw"] = gdf["maxpowerqhw"].astype(float)

    maps = [
        (heat_column, "Heat energy (MWh/an)", "map_heat_energy.png", "YlOrRd"),
        ("elec_mwh", "Electric energy (MWh/an)", "map_electric_energy.png", "YlGnBu"),
        ("maxpower_kw", "Yearly max power (kW)", "map_yearly_max_power.png", "magma"),
        ("heat_kwh_per_sre", "Heat energy per SRE (kWh/m²/an)", "map_heat_per_sre.png", "plasma"),
        ("elec_kwh_per_sre", "Electric energy per SRE (kWh/m²/an)", "map_elec_per_sre.png", "viridis"),
    ]

    for column, title, filename, cmap in maps:
        if not column or column not in gdf.columns:
            continue
        fig, ax = plt.subplots(figsize=(8, 6))
        gdf.plot(
            column=column,
            ax=ax,
            legend=True,
            cmap=cmap,
            missing_kwds={"color": "lightgrey", "label": "No data"},
        )
        ax.set_title(title)
        ax.set_axis_off()
        fig.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)


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
    if "heat_annual_kwh" not in buildings.columns:
        buildings["heat_annual_kwh"] = 0.0
    if "heat_ecs_annual_kwh" not in buildings.columns:
        buildings["heat_ecs_annual_kwh"] = buildings["heat_annual_kwh"]
    if "maxpowerqhw" not in buildings.columns:
        buildings["maxpowerqhw"] = 0.0
    buildings = add_energy_intensity(buildings)

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
        import geopandas as gpd
    except ImportError:
        gpd = None

    if gpd is not None:
        maps_dir = ensure_dir(results_dir / "maps")
        buildings_gdf = gpd.read_file(results_dir / "buildings_electricity.geojson")
        save_geopandas_maps(buildings_gdf, maps_dir)

    try:
        import plotly.express as px
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        energy_by_affect = (
            buildings.groupby("affect")[["heat_annual_kwh", "elec_annual_kwh"]]
            .sum()
            .reset_index()
            .fillna(0)
        )
        energy_by_affect["heat_mwh"] = energy_by_affect["heat_annual_kwh"] / 1000
        energy_by_affect["elec_mwh"] = energy_by_affect["elec_annual_kwh"] / 1000

        affect_long = energy_by_affect.melt(
            id_vars="affect",
            value_vars=["heat_mwh", "elec_mwh"],
            var_name="energy_type",
            value_name="mwh",
        )
        affect_long["energy_type"] = affect_long["energy_type"].map({"heat_mwh": "Chauffage", "elec_mwh": "Electricité"})
        fig = px.bar(
            affect_long,
            x="affect",
            y="mwh",
            color="energy_type",
            barmode="group",
            title="Energie annuelle par affectation",
            labels={"affect": "Affectation", "mwh": "Energie (MWh/an)", "energy_type": "Type"},
        )
        fig.update_layout(xaxis_tickangle=-30)
        fig.write_html(results_dir / "energy_by_affectation.html", include_plotlyjs="cdn")

        buildings["etat_label"] = buildings["etat"].fillna("Inconnu")
        energy_by_etat = (
            buildings.groupby("etat_label")[["heat_annual_kwh", "elec_annual_kwh"]]
            .sum()
            .reset_index()
            .fillna(0)
        )
        energy_by_etat["heat_mwh"] = energy_by_etat["heat_annual_kwh"] / 1000
        energy_by_etat["elec_mwh"] = energy_by_etat["elec_annual_kwh"] / 1000
        etat_long = energy_by_etat.melt(
            id_vars="etat_label",
            value_vars=["heat_mwh", "elec_mwh"],
            var_name="energy_type",
            value_name="mwh",
        )
        etat_long["energy_type"] = etat_long["energy_type"].map({"heat_mwh": "Chauffage", "elec_mwh": "Electricité"})
        fig = px.bar(
            etat_long,
            x="etat_label",
            y="mwh",
            color="energy_type",
            barmode="group",
            title="Energie annuelle par état",
            labels={"etat_label": "Etat", "mwh": "Energie (MWh/an)", "energy_type": "Type"},
        )
        fig.write_html(results_dir / "energy_by_state.html", include_plotlyjs="cdn")

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

            fig = make_subplots(
                rows=3,
                cols=1,
                shared_xaxes=True,
                subplot_titles=["Semaine d'hiver", "Semaine de mi-saison", "Semaine d'été"],
            )
            for idx, (label, week) in enumerate(weeks.items(), start=1):
                show_legend = idx == 1
                fig.add_trace(
                    go.Scatter(
                        x=week.index,
                        y=week[admin_id],
                        name=f"Administration ({label})",
                        mode="lines",
                        showlegend=show_legend,
                    ),
                    row=idx,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=week.index,
                        y=week[industry_id],
                        name=f"Industries ({label})",
                        mode="lines",
                        showlegend=show_legend,
                    ),
                    row=idx,
                    col=1,
                )
                fig.update_yaxes(title_text="kW", row=idx, col=1)
            fig.update_layout(height=900, title="Profils hebdomadaires typiques", hovermode="x unified")
            fig.write_html(results_dir / "typical_week_profiles.html", include_plotlyjs="cdn")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
