from __future__ import annotations

import numpy as np
import pandas as pd

from ronquoz_common import (
    BUILDINGS_GEOJSON,
    RESULTS_DIR,
    apply_thermal_inertia,
    ensure_dir,
    get_foisonnement,
    get_inertia,
    hourly_index,
    load_geojson,
    load_sia_tables,
    load_weather_series,
    map_affectation,
    norme_from_year,
    write_geojson,
)


def main() -> None:
    data, buildings = load_geojson(BUILDINGS_GEOJSON)

    weather = load_weather_series()
    weather_hours = len(weather)
    temps = weather.to_numpy(dtype=float)
    heating_intensity = np.clip(18.5 - temps, 0, None)
    heating_total = heating_intensity.sum()
    heating_weights = heating_intensity / heating_total if heating_total > 0 else np.zeros_like(heating_intensity)

    sia_tables = load_sia_tables()
    t_avg = float(weather.mean())
    fcor = 1 + ((9.4 - t_avg) * 0.06)

    times = hourly_index(weather_hours)
    ecs_mask = (times.hour >= 8) & (times.hour < 20)
    ecs_hours = ecs_mask.sum()

    district_heating = np.zeros(weather_hours)
    district_ecs = np.zeros(weather_hours)

    annual_heating = []
    annual_ecs = []
    peak_kw = []
    peak_kw_foisonnement = []
    foisonnement = []
    inertia_hours = []

    for _, row in buildings.iterrows():
        affect = row.get("affect")
        affect_sia = map_affectation(affect)
        norme = norme_from_year(int(row.get("annee_constr")))
        sre = float(row.get("sre", 0) or 0)
        facteur_env = float(row.get("facteur_enveloppe", 0) or 0)

        qhli0 = float(sia_tables["Qhli_0"].loc[norme, affect_sia])
        delta_qhli = float(sia_tables["delta_Qhli"].loc[norme, affect_sia])
        ecs_specific = float(sia_tables["ECS"].loc[norme, affect_sia])

        qh_li = (qhli0 + delta_qhli * facteur_env) * fcor
        heat_annual_kwh = qh_li * sre
        ecs_annual_kwh = ecs_specific * sre

        heating_profile = heating_weights * heat_annual_kwh if heat_annual_kwh > 0 else np.zeros(weather_hours)
        inertia = get_inertia(affect)
        heating_profile = apply_thermal_inertia(heating_profile, inertia)

        ecs_profile = np.zeros(weather_hours)
        if ecs_annual_kwh > 0 and ecs_hours > 0:
            ecs_profile[ecs_mask] = ecs_annual_kwh / ecs_hours

        total_profile = heating_profile + ecs_profile
        peak = total_profile.max()
        factor = get_foisonnement(affect)

        district_heating += heating_profile
        district_ecs += ecs_profile

        annual_heating.append(heat_annual_kwh)
        annual_ecs.append(ecs_annual_kwh)
        peak_kw.append(peak)
        peak_kw_foisonnement.append(peak * factor)
        foisonnement.append(factor)
        inertia_hours.append(inertia)

    buildings = buildings.copy()
    buildings["heat_annual_kwh"] = annual_heating
    buildings["ecs_annual_kwh"] = annual_ecs
    buildings["heat_ecs_annual_kwh"] = buildings["heat_annual_kwh"] + buildings["ecs_annual_kwh"]
    buildings["heat_peak_kw"] = peak_kw
    buildings["heat_peak_kw_foisonnement"] = peak_kw_foisonnement
    buildings["foisonnement"] = foisonnement
    buildings["inertie_thermique_h"] = inertia_hours
    buildings["maxpowerqhw"] = buildings["heat_peak_kw_foisonnement"]

    results_dir = ensure_dir(RESULTS_DIR / "lab1")
    write_geojson(results_dir / "buildings_energy.geojson", data, buildings)

    pie_data = buildings.groupby("affect")["sre"].sum().sort_values(ascending=False)
    pie_data.to_csv(results_dir / "sre_by_affectation.csv")

    district_profile = pd.DataFrame(
        {
            "time": times,
            "heating_kw": district_heating,
            "ecs_kw": district_ecs,
            "total_kw": district_heating + district_ecs,
        }
    )
    district_profile.to_csv(results_dir / "district_profile.csv", index=False)

    peaks = buildings[["id_unique", "affect", "heat_peak_kw", "heat_peak_kw_foisonnement"]]
    peaks.to_csv(results_dir / "building_peaks.csv", index=False)

    try:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 6))
        pie_data.plot.pie(autopct="%1.1f%%", ax=ax)
        ax.set_ylabel("")
        ax.set_title("Répartition SRE par affectation")
        fig.tight_layout()
        fig.savefig(results_dir / "sre_by_affectation.png", dpi=150)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(district_profile["time"], district_profile["total_kw"], label="Total")
        ax.plot(district_profile["time"], district_profile["heating_kw"], label="Chauffage", alpha=0.7)
        ax.plot(district_profile["time"], district_profile["ecs_kw"], label="ECS", alpha=0.7)
        ax.set_ylabel("Puissance (kW)")
        ax.set_title("Profil horaire quartier")
        ax.legend()
        fig.tight_layout()
        fig.savefig(results_dir / "district_profile.png", dpi=150)
        plt.close(fig)
    except ImportError:
        pass


if __name__ == "__main__":
    main()
