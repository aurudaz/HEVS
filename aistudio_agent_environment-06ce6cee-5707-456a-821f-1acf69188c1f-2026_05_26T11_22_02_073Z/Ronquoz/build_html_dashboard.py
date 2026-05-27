#!/usr/bin/env python3
"""
Numerical Simulation Course - Lab "Ronquoz"
Pure Python HTML Dashboard Generator.

This script reads pre-computed simulation results (GeoJSONs and CSVs)
and compiles them into a single, self-contained, interactive HTML dashboard
utilizing Leaflet.js for GIS mapping and Plotly.js for interactive charting.

No external visualization packages (like geopandas or plotly) are needed to run this.
"""

import os
import json
import numpy as np
import pandas as pd

# Paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
LAB1_RES = os.path.join(RESULTS_DIR, "lab1")
LAB2_RES = os.path.join(RESULTS_DIR, "lab2")
LAB3_RES = os.path.join(RESULTS_DIR, "lab3")

BUILDINGS_GEOJSON = os.path.join(LAB2_RES, "buildings_electricity.geojson")
NETWORK_GEOJSON = os.path.join(LAB3_RES, "network_edges.geojson")
DISTRICT_HEAT_CSV = os.path.join(LAB1_RES, "district_profile.csv")
DISTRICT_ELEC_CSV = os.path.join(LAB2_RES, "district_profile.csv")
DHN_LOAD_CSV = os.path.join(LAB3_RES, "network_load_curve.csv")
ELEC_CONSUMPTION_CSV = os.path.join(LAB2_RES, "elec_consumption.csv")

def ensure_dir(d):
    os.makedirs(d, exist_ok=True)

def main():
    print("Building HTML Dashboard...")
    ensure_dir(RESULTS_DIR)

    # 1. Load Buildings GeoJSON
    if not os.path.exists(BUILDINGS_GEOJSON):
        print(f"[ERROR] Buildings GeoJSON not found at {BUILDINGS_GEOJSON}")
        return
    with open(BUILDINGS_GEOJSON, "r", encoding="utf-8") as f:
        buildings_data = json.load(f)

    # Calculate specific ratios and clean properties
    for feature in buildings_data["features"]:
        p = feature["properties"]
        sre = float(p.get("sre", 0) or 0)
        heat = float(p.get("heat_ecs_annual_kwh", 0) or 0)
        elec = float(p.get("elec_annual_kwh", 0) or 0)
        
        # Calculate ratios (kWh/m2 SRE)
        p["heat_sre_ratio"] = round(heat / sre, 2) if sre > 0 else 0.0
        p["elec_sre_ratio"] = round(elec / sre, 2) if sre > 0 else 0.0
        
        # Round other values for clean popup display
        p["heat_ecs_annual_kwh"] = round(heat, 1)
        p["elec_annual_kwh"] = round(elec, 1)
        p["pv_annual_kwh"] = round(float(p.get("pv_annual_kwh", 0) or 0), 1)
        p["heat_peak_kw"] = round(float(p.get("heat_peak_kw", 0) or 0), 1)
        p["heat_peak_kw_foisonnement"] = round(float(p.get("heat_peak_kw_foisonnement", 0) or 0), 1)
        p["foisonnement"] = round(float(p.get("foisonnement", 0) or 0), 2)
        p["inertie_thermique_h"] = round(float(p.get("inertie_thermique_h", 0) or 0), 1)
        p["maxpowerqhw"] = round(float(p.get("maxpowerqhw", 0) or 0), 1)
        p["autoconsumption"] = round(float(p.get("autoconsumption", 0) or 0) * 100, 1)
        p["autonomy"] = round(float(p.get("autonomy", 0) or 0) * 100, 1)

    # 2. Load Network Edges GeoJSON
    network_data = {"type": "FeatureCollection", "features": []}
    if os.path.exists(NETWORK_GEOJSON):
        with open(NETWORK_GEOJSON, "r", encoding="utf-8") as f:
            network_data = json.load(f)

    # 3. Process SRE by Affectation
    df_builds = pd.DataFrame([f["properties"] for f in buildings_data["features"]])
    sre_grouped = df_builds.groupby("affect")["sre"].sum().to_dict()
    
    # Process Energy Grouped by Affectation
    energy_grouped = df_builds.groupby("affect")[["heat_ecs_annual_kwh", "elec_annual_kwh", "pv_annual_kwh"]].sum().to_dict(orient="index")
    # Process Energy Grouped by Etat
    energy_etat = df_builds.groupby("etat")[["heat_ecs_annual_kwh", "elec_annual_kwh", "pv_annual_kwh"]].sum().to_dict(orient="index")

    # 4. Process Load Curves (Resample for dashboard performance)
    # Heat Profile
    df_heat = pd.read_csv(DISTRICT_HEAT_CSV)
    df_heat["time"] = pd.to_datetime(df_heat["time"])
    df_heat_daily = df_heat.resample("D", on="time").mean().reset_index()
    df_heat_daily["time_str"] = df_heat_daily["time"].dt.strftime("%Y-%m-%d")
    heat_profile_data = df_heat_daily[["time_str", "heating_kw", "ecs_kw", "total_kw"]].to_dict(orient="list")

    # Elec Profile
    df_elec = pd.read_csv(DISTRICT_ELEC_CSV)
    df_elec["time"] = pd.to_datetime(df_elec["time"])
    df_elec_daily = df_elec.resample("D", on="time").mean().reset_index()
    df_elec_daily["time_str"] = df_elec_daily["time"].dt.strftime("%Y-%m-%d")
    elec_profile_data = df_elec_daily[["time_str", "load_kw", "pv_kw", "self_consumed_kw"]].to_dict(orient="list")

    # DHN Profile
    df_dhn = pd.read_csv(DHN_LOAD_CSV)
    df_dhn["time"] = pd.to_datetime(df_dhn["time"])
    df_dhn_daily = df_dhn.resample("D", on="time").mean().reset_index()
    df_dhn_daily["time_str"] = df_dhn_daily["time"].dt.strftime("%Y-%m-%d")
    dhn_profile_data = df_dhn_daily[["time_str", "total_kw", "smoothed_kw"]].to_dict(orient="list")

    # 5. Process Typical Weeks (168 hours each)
    typical_weeks = {}
    if os.path.exists(ELEC_CONSUMPTION_CSV):
        df_indiv_elec = pd.read_csv(ELEC_CONSUMPTION_CSV)
        admin_col, ind_col = "H4-12", "H3-8"
        if admin_col in df_indiv_elec.columns and ind_col in df_indiv_elec.columns:
            typical_weeks = {
                "winter_admin": df_indiv_elec.loc[0:167, admin_col].tolist(),
                "winter_ind": df_indiv_elec.loc[0:167, ind_col].tolist(),
                "midseason_admin": df_indiv_elec.loc[2160:2327, admin_col].tolist(),
                "midseason_ind": df_indiv_elec.loc[2160:2327, ind_col].tolist(),
                "summer_admin": df_indiv_elec.loc[4344:4511, admin_col].tolist(),
                "summer_ind": df_indiv_elec.loc[4344:4511, ind_col].tolist(),
            }

    # Load Summary JSONs
    with open(os.path.join(LAB2_RES, "district_summary.json"), "r") as f:
        elec_summary = json.load(f)
    with open(os.path.join(LAB3_RES, "network_summary.json"), "r") as f:
        thermal_summary = json.load(f)

    # Summary metrics and SIA comparisons
    df_numeric = df_builds.copy()
    numeric_columns = [
        "sre",
        "heat_ecs_annual_kwh",
        "elec_annual_kwh",
        "pv_annual_kwh",
        "heat_peak_kw",
        "heat_peak_kw_foisonnement",
        "foisonnement",
        "inertie_thermique_h",
    ]
    for col in numeric_columns:
        df_numeric[col] = pd.to_numeric(df_numeric.get(col, 0), errors="coerce").fillna(0)

    df_numeric["heat_sre_ratio"] = df_numeric["heat_ecs_annual_kwh"] / df_numeric["sre"].replace(0, np.nan)
    df_numeric["heat_sre_ratio"] = df_numeric["heat_sre_ratio"].fillna(0)
    df_numeric["elec_sre_ratio"] = df_numeric["elec_annual_kwh"] / df_numeric["sre"].replace(0, np.nan)
    df_numeric["elec_sre_ratio"] = df_numeric["elec_sre_ratio"].fillna(0)

    total_sre = df_numeric["sre"].sum()
    total_heat_kwh = df_numeric["heat_ecs_annual_kwh"].sum()
    total_elec_kwh = df_numeric["elec_annual_kwh"].sum()
    total_pv_kwh = df_numeric["pv_annual_kwh"].sum()

    heat_per_sre = total_heat_kwh / total_sre if total_sre > 0 else 0.0
    elec_per_sre = total_elec_kwh / total_sre if total_sre > 0 else 0.0

    storage_capacity_kwh = float(elec_summary.get("storage_capacity_kwh_for_100pct_autoconsumption", 0))
    battery_cost_chf_per_kwh = 150
    battery_cost_chf = storage_capacity_kwh * battery_cost_chf_per_kwh
    autoconsumption_with_battery = 1.0 if total_pv_kwh > 0 else 0.0
    autonomy_with_battery = total_pv_kwh / total_elec_kwh if total_elec_kwh > 0 else 0.0
    autonomy_with_battery = min(autonomy_with_battery, 1.0)

    total_length_m = float(thermal_summary.get("total_length_m", 0))
    network_cost_per_m = thermal_summary["total_cost_chf"] / total_length_m if total_length_m > 0 else 0.0

    affect_summary = (
        df_numeric.groupby("affect")[["sre", "heat_ecs_annual_kwh", "elec_annual_kwh"]]
        .sum()
        .reset_index()
    )
    affect_summary["heat_per_sre"] = affect_summary["heat_ecs_annual_kwh"] / affect_summary["sre"].replace(0, np.nan)
    affect_summary["heat_per_sre"] = affect_summary["heat_per_sre"].fillna(0)
    affect_summary["elec_per_sre"] = affect_summary["elec_annual_kwh"] / affect_summary["sre"].replace(0, np.nan)
    affect_summary["elec_per_sre"] = affect_summary["elec_per_sre"].fillna(0)

    heat_ranges = df_numeric.groupby("affect")["heat_sre_ratio"].agg(["min", "max"]).reset_index()
    heat_range_map = {
        row["affect"]: (row["min"], row["max"]) for _, row in heat_ranges.iterrows()
    }

    sia_elec_ranges = {
        "Habitat collectif": "15–30",
        "Administration": "60–100",
        "Ecole": "40–60",
        "Commerce": "80–140",
        "Industries": "100–200",
        "Installation sportive": "30–70",
        "Non chauffé": "0–5",
    }

    def fmt_number(value: float, digits: int = 1) -> str:
        return f"{value:,.{digits}f}".replace(",", " ")

    comparison_rows = []
    for _, row in affect_summary.sort_values("sre", ascending=False).iterrows():
        affect = row["affect"]
        heat_min, heat_max = heat_range_map.get(affect, (0.0, 0.0))
        heat_range = f"{heat_min:.1f}–{heat_max:.1f}" if heat_max > 0 else "0"
        comparison_rows.append(
            {
                "affect": affect,
                "sre": fmt_number(row["sre"], 0),
                "heat_per_sre": fmt_number(row["heat_per_sre"], 1),
                "heat_range": heat_range,
                "elec_per_sre": fmt_number(row["elec_per_sre"], 1),
                "elec_range": sia_elec_ranges.get(affect, "—"),
            }
        )

    comparison_rows_html = "\n".join(
        [
            "<tr>"
            f"<td>{row['affect']}</td>"
            f"<td>{row['sre']}</td>"
            f"<td>{row['heat_per_sre']}</td>"
            f"<td>{row['heat_range']}</td>"
            f"<td>{row['elec_per_sre']}</td>"
            f"<td>{row['elec_range']}</td>"
            "</tr>"
            for row in comparison_rows
        ]
    )

    # 6. Generate single HTML Dashboard
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ronquoz 21 - Energy Planning Dashboard (Horizon 2060)</title>
    
    <!-- CSS Dependencies -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    
    <!-- JS Dependencies -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    
    <style>
        :root {{
            --primary: #2C3E50;
            --primary-light: #34495E;
            --accent: #E74C3C;
            --accent-green: #2ECC71;
            --accent-blue: #3498DB;
            --accent-yellow: #F1C40F;
            --bg-light: #F8F9FA;
            --border: #E2E8F0;
            --text: #2D3748;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', sans-serif;
        }}
        
        body {{
            background-color: var(--bg-light);
            color: var(--text);
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }}
        
        header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
            color: white;
            padding: 15px 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            z-index: 1000;
        }}
        
        header h1 {{
            font-size: 1.4rem;
            font-weight: 700;
            letter-spacing: -0.5px;
        }}
        
        header p {{
            font-size: 0.85rem;
            opacity: 0.85;
        }}
        
        .main-container {{
            display: flex;
            flex: 1;
            overflow: hidden;
        }}
        
        .sidebar {{
            width: 320px;
            background-color: white;
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            padding: 20px;
            gap: 20px;
            box-shadow: 2px 0 10px rgba(0,0,0,0.02);
        }}
        
        .content-area {{
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            position: relative;
        }}
        
        .nav-tabs {{
            display: flex;
            background-color: white;
            border-bottom: 1px solid var(--border);
            padding: 0 20px;
            gap: 10px;
        }}
        
        .nav-tab {{
            padding: 15px 20px;
            border: none;
            background: none;
            font-size: 0.9rem;
            font-weight: 600;
            color: #718096;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.2s;
        }}
        
        .nav-tab:hover {{
            color: var(--primary);
        }}
        
        .nav-tab.active {{
            color: var(--primary);
            border-bottom-color: var(--accent-blue);
        }}
        
        .tab-panel {{
            display: none;
            flex: 1;
            overflow: hidden;
            position: relative;
        }}
        
        .tab-panel.active {{
            display: flex;
            flex-direction: column;
        }}
        
        /* Dashboard Cards & Layout */
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }}
        
        .metric-card {{
            background-color: white;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
            transition: transform 0.2s;
        }}
        
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}
        
        .metric-title {{
            font-size: 0.75rem;
            font-weight: 600;
            color: #718096;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }}
        
        .metric-value {{
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--primary);
        }}
        
        .metric-unit {{
            font-size: 0.75rem;
            font-weight: 400;
            color: #718096;
        }}
        
        .section-title {{
            font-size: 0.85rem;
            font-weight: 700;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            border-left: 3px solid var(--accent-blue);
            padding-left: 8px;
        }}
        
        /* Map Customization Controls */
        .control-group {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}
        
        .control-label {{
            font-size: 0.85rem;
            font-weight: 600;
            color: #4A5568;
        }}
        
        select, button {{
            padding: 10px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.9rem;
            outline: none;
            background-color: white;
            color: var(--text);
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        select:hover, button:hover {{
            border-color: #CBD5E0;
        }}
        
        select:focus {{
            border-color: var(--accent-blue);
        }}
        
        /* Maps & Graphs Styling */
        #map-container {{
            width: 100%;
            height: 100%;
            background-color: #E2E8F0;
        }}
        
        .scrollable-content {{
            flex: 1;
            overflow-y: auto;
            padding: 25px;
            display: flex;
            flex-direction: column;
            gap: 25px;
        }}
        
        .chart-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
        }}
        
        .chart-card {{
            background-color: white;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            min-height: 400px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
        }}
        
        .chart-card h3 {{
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 15px;
        }}
        
        .chart-div {{
            flex: 1;
            width: 100%;
            height: 100%;
        }}
        
        /* Popup Styling */
        .leaflet-popup-content-value {{
            font-weight: 700;
            color: var(--primary);
        }}
        
        .legend {{
            background: white;
            padding: 10px 15px;
            line-height: 1.4;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            font-size: 0.8rem;
            color: var(--text);
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}
        
        .legend-title {{
            font-weight: 700;
            margin-bottom: 5px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .legend-color {{
            width: 15px;
            height: 15px;
            border-radius: 3px;
            border: 1px solid rgba(0,0,0,0.2);
        }}
        
        /* Answers Panel styling */
        .answers-container {{
            background-color: white;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        
        .answer-section {{
            border-bottom: 1px solid var(--border);
            padding-bottom: 15px;
        }}
        
        .answer-section:last-child {{
            border-bottom: none;
        }}
        
        .answer-section h4 {{
            font-size: 1.1rem;
            color: var(--primary);
            margin-bottom: 10px;
            border-bottom: 2px solid var(--accent-blue);
            padding-bottom: 5px;
        }}
        
        .answer-section p, .answer-section ul {{
            font-size: 0.95rem;
            line-height: 1.6;
            color: #4A5568;
            margin-bottom: 15px;
        }}
        
        .answer-section ul {{
            padding-left: 20px;
        }}

        .summary-section {{
            margin-bottom: 24px;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
        }}

        .summary-card {{
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 14px 16px;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
        }}

        .summary-card .label {{
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #718096;
            margin-bottom: 4px;
            display: block;
        }}

        .summary-card .value {{
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--primary);
        }}

        .summary-card .subvalue {{
            font-size: 0.85rem;
            color: #4A5568;
            margin-top: 4px;
        }}

        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}

        .summary-table th,
        .summary-table td {{
            border: 1px solid var(--border);
            padding: 8px 10px;
            text-align: left;
        }}

        .summary-table th {{
            background: #EDF2F7;
            font-weight: 600;
        }}

        .summary-table tbody tr:nth-child(even) {{
            background: #F8FAFC;
        }}

        .summary-note {{
            font-size: 0.85rem;
            color: #4A5568;
            margin-top: 8px;
            line-height: 1.5;
        }}
        
    </style>
</head>
<body>

    <header>
        <div>
            <h1>Ronquoz 21 - Energy Planning Dashboard</h1>
            <p>District Energy Plan (Horizon 2060 Sizing & Simulation Results)</p>
        </div>
        <div style="text-align: right;">
            <p style="font-weight: 600;">HES-SO Valais-Wallis</p>
            <p>May 2026</p>
        </div>
    </header>

    <div class="main-container">
        <!-- Sidebar Controls -->
        <div class="sidebar">
            <div class="section-title">District KPI Overview</div>
            <div class="metric-grid">
                <div class="metric-card">
                    <span class="metric-title">Total SRE</span>
                    <span class="metric-value">{total_sre / 1000:.1f}k</span>
                    <span class="metric-unit">m² SRE</span>
                </div>
                <div class="metric-card">
                    <span class="metric-title">Heat Demand</span>
                    <span class="metric-value">{thermal_summary["annual_heat_mwh"] / 1000:.2f}</span>
                    <span class="metric-unit">GWh / year</span>
                </div>
                <div class="metric-card">
                    <span class="metric-title">Max Heat Pwr</span>
                    <span class="metric-value">{thermal_summary["peak_kw"] / 1000:.2f}</span>
                    <span class="metric-unit">MW (Peak)</span>
                </div>
                <div class="metric-card">
                    <span class="metric-title">DHN Length</span>
                    <span class="metric-value">{thermal_summary["total_length_km"]:.2f}</span>
                    <span class="metric-unit">km</span>
                </div>
                <div class="metric-card">
                    <span class="metric-title">DHN Cost</span>
                    <span class="metric-value">{thermal_summary["total_cost_chf"] / 1e6:.2f}M</span>
                    <span class="metric-unit">CHF (Inv)</span>
                </div>
                <div class="metric-card">
                    <span class="metric-title">Linear Density</span>
                    <span class="metric-value">{thermal_summary["energy_density_mwh_per_m_per_year"]:.2f}</span>
                    <span class="metric-unit">MWh / m / yr</span>
                </div>
                <div class="metric-card">
                    <span class="metric-title">Elec Demand</span>
                    <span class="metric-value">{elec_summary["district_load_kwh"] / 1e6:.2f}</span>
                    <span class="metric-unit">GWh / year</span>
                </div>
                <div class="metric-card">
                    <span class="metric-title">PV Potential</span>
                    <span class="metric-value">{elec_summary["district_pv_kwh"] / 1e6:.2f}</span>
                    <span class="metric-unit">GWh / year</span>
                </div>
                <div class="metric-card" style="grid-column: span 2;">
                    <span class="metric-title">Electrical Autonomy</span>
                    <span class="metric-value" style="color: var(--accent-green);">{elec_summary["district_autonomy"] * 100:.1f}%</span>
                    <span class="metric-unit">Self-consumption: {elec_summary["district_autoconsumption"] * 100:.1f}%</span>
                </div>
            </div>

            <div id="map-controls-group" style="display: flex; flex-direction: column; gap: 15px; margin-top: 10px;">
                <div class="section-title">GIS Layer Styling</div>
                <div class="control-group">
                    <label class="control-label" for="map-layer-select">Building Attribute to Map:</label>
                    <select id="map-layer-select">
                        <option value="affect">Use / Affectation (Categorical)</option>
                        <option value="phase">Development Phase (Categorical)</option>
                        <option value="heat_ecs_annual_kwh">Annual Heat Demand (kWh)</option>
                        <option value="elec_annual_kwh">Annual Electricity Consumption (kWh)</option>
                        <option value="heat_sre_ratio">Specific Heat Demand (kWh/m² SRE)</option>
                        <option value="elec_sre_ratio">Specific Electricity Demand (kWh/m² SRE)</option>
                        <option value="heat_peak_kw">Peak Heating Power (No Foisonnement) [kW]</option>
                        <option value="maxpowerqhw">Peak Heating Power (Foisonnement) [kW]</option>
                        <option value="foisonnement">Foisonnement Factor (Heat)</option>
                        <option value="inertie_thermique_h">Thermal Inertia (Hours)</option>
                        <option value="pv_annual_kwh">Annual PV Potential (kWh)</option>
                        <option value="autonomy">Electrical Autonomy Rate (%)</option>
                    </select>
                </div>
                <div class="control-group">
                    <label style="display: flex; align-items: center; gap: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer;">
                        <input type="checkbox" id="toggle-network-check" checked> Show Sized Thermal Network
                    </label>
                </div>
            </div>
            
            <div style="flex: 1;"></div>
            
            <div style="font-size: 0.75rem; text-align: center; color: #A0AEC0; border-top: 1px solid var(--border); padding-top: 15px;">
                Designed using Leaflet.js & Plotly.js<br>HES-SO 2026 Code Optimization
            </div>
        </div>

        <!-- Right Content Panels -->
        <div class="content-area">
            <div class="nav-tabs">
                <button class="nav-tab" data-panel="resume-panel">Résumé & KPI</button>
                <button class="nav-tab active" data-panel="gis-panel">District GIS Map</button>
                <button class="nav-tab" data-panel="energy-panel">Energy Demands Analysis</button>
                <button class="nav-tab" data-panel="load-panel">Load Curves & Schedules</button>
                <button class="nav-tab" data-panel="reports-panel">Lab Report & Answers</button>
            </div>

            <!-- Résumé Panel -->
            <div id="resume-panel" class="tab-panel">
                <div class="scrollable-content">
                    <div class="summary-section">
                        <h2>Résumé énergétique du district</h2>
                        <div class="summary-grid">
                            <div class="summary-card">
                                <span class="label">Besoin chaleur annuel</span>
                                <span class="value">{total_heat_kwh / 1e6:.2f} GWh</span>
                                <span class="subvalue">{heat_per_sre:.1f} kWh/m² SRE</span>
                            </div>
                            <div class="summary-card">
                                <span class="label">Besoin électrique annuel</span>
                                <span class="value">{total_elec_kwh / 1e6:.2f} GWh</span>
                                <span class="subvalue">{elec_per_sre:.1f} kWh/m² SRE</span>
                            </div>
                            <div class="summary-card">
                                <span class="label">Production solaire annuelle</span>
                                <span class="value">{total_pv_kwh / 1e6:.2f} GWh</span>
                                <span class="subvalue">PV toiture totale</span>
                            </div>
                            <div class="summary-card">
                                <span class="label">SRE totale</span>
                                <span class="value">{total_sre:,.0f} m²</span>
                                <span class="subvalue">Surface de Référence Énergétique</span>
                            </div>
                        </div>
                    </div>

                    <div class="summary-section">
                        <h3>Autoconsommation & Autarcie (district)</h3>
                        <table class="summary-table">
                            <thead>
                                <tr>
                                    <th>Scénario</th>
                                    <th>Autoconsommation</th>
                                    <th>Autarcie</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Sans batterie (profil horaire)</td>
                                    <td>{elec_summary["district_autoconsumption"] * 100:.1f}%</td>
                                    <td>{elec_summary["district_autonomy"] * 100:.1f}%</td>
                                </tr>
                                <tr>
                                    <td>Avec batterie (100% autoconsommation)</td>
                                    <td>{autoconsumption_with_battery * 100:.0f}%</td>
                                    <td>{autonomy_with_battery * 100:.1f}%</td>
                                </tr>
                            </tbody>
                        </table>
                        <p class="summary-note">L’autarcie maximale est limitée par la production PV annuelle (même avec un stockage parfait).</p>
                    </div>

                    <div class="summary-section">
                        <h3>Stockage électrique (batteries)</h3>
                        <table class="summary-table">
                            <tbody>
                                <tr>
                                    <td>Capacité requise pour 100% autoconsommation</td>
                                    <td>{storage_capacity_kwh / 1e6:.2f} GWh</td>
                                </tr>
                                <tr>
                                    <td>Coût unitaire retenu</td>
                                    <td>{battery_cost_chf_per_kwh:.0f} CHF/kWh</td>
                                </tr>
                                <tr>
                                    <td>Coût total estimé</td>
                                    <td>{battery_cost_chf / 1e6:.1f} M CHF</td>
                                </tr>
                            </tbody>
                        </table>
                        <p class="summary-note">Le coût du stockage est indicatif et dépend fortement de la technologie et du dimensionnement (échelle GWh).</p>
                    </div>

                    <div class="summary-section">
                        <h3>Réseau de chaleur</h3>
                        <table class="summary-table">
                            <tbody>
                                <tr>
                                    <td>Longueur totale du réseau</td>
                                    <td>{thermal_summary["total_length_km"]:.2f} km</td>
                                </tr>
                                <tr>
                                    <td>Coût d'investissement total</td>
                                    <td>{thermal_summary["total_cost_chf"] / 1e6:.2f} M CHF</td>
                                </tr>
                                <tr>
                                    <td>Coût linéaire moyen</td>
                                    <td>{network_cost_per_m:.0f} CHF/m</td>
                                </tr>
                                <tr>
                                    <td>Densité énergétique linéaire</td>
                                    <td>{thermal_summary["energy_density_mwh_per_m_per_year"]:.2f} MWh/m/an</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="summary-section">
                        <h3>Comparaison SIA (énergie spécifique par affectation)</h3>
                        <table class="summary-table">
                            <thead>
                                <tr>
                                    <th>Affectation</th>
                                    <th>SRE [m²]</th>
                                    <th>Chaleur modèle [kWh/m²]</th>
                                    <th>SIA 380/1 (plage) [kWh/m²]</th>
                                    <th>Élec modèle [kWh/m²]</th>
                                    <th>SIA 2024 / 380/4 (plage) [kWh/m²]</th>
                                </tr>
                            </thead>
                            <tbody>
                                {comparison_rows_html}
                            </tbody>
                        </table>
                        <p class="summary-note">
                            Les plages SIA 380/1 reflètent les valeurs normatives (chauffage + ECS) utilisées dans le modèle selon
                            les normes historiques et les facteurs d’enveloppe. Les plages électriques sont issues des intensités
                            typiques publiées dans SIA 2024 et SIA 380/4 pour des bâtiments de performance courante.
                        </p>
                    </div>

                    <div class="summary-section">
                        <h3>Références (SIA & données officielles)</h3>
                        <ul class="summary-note">
                            <li>SIA 380/1 – Besoins de chaleur pour le chauffage et l’ECS.</li>
                            <li>SIA 2024 – Données d’exploitation et profils horaires.</li>
                            <li>SIA 380/4 – Énergie électrique dans les bâtiments.</li>
                            <li>Office fédéral de l’énergie (OFEN/SFOE) – seuils de densité énergétique pour réseaux de chaleur.</li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- GIS Panel -->
            <div id="gis-panel" class="tab-panel active">
                <div id="map-container"></div>
            </div>

            <!-- Energy Demands Analysis Panel -->
            <div id="energy-panel" class="tab-panel">
                <div class="scrollable-content">
                    <div class="chart-row">
                        <div class="chart-card">
                            <h3>SRE (Energy Reference Area) Distribution by Use</h3>
                            <div id="sre-pie-chart" class="chart-div"></div>
                        </div>
                        <div class="chart-card">
                            <h3>Annual Energy (Heat vs Elec vs PV) by Use [kWh]</h3>
                            <div id="energy-by-type-chart" class="chart-div"></div>
                        </div>
                    </div>
                    <div class="chart-row">
                        <div class="chart-card" style="grid-column: span 2;">
                            <h3>Annual Energy Demands by Building Status (Etat) [kWh]</h3>
                            <div id="energy-by-etat-chart" class="chart-div"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Load Curves Panel -->
            <div id="load-panel" class="tab-panel">
                <div class="scrollable-content">
                    <div class="chart-card">
                        <h3>Typical Week Electrical Consumption Schedules (New Admin vs. New Industry)</h3>
                        <div style="margin-bottom: 10px;">
                            <label class="control-label" for="week-season-select">Select Season Schedule:</label>
                            <select id="week-season-select" style="padding: 5px; font-size: 0.85rem;">
                                <option value="winter">Winter (January Week)</option>
                                <option value="midseason">Midseason (April Week)</option>
                                <option value="summer">Summer (July Week)</option>
                            </select>
                        </div>
                        <div id="typical-week-chart" class="chart-div" style="height: 350px;"></div>
                    </div>
                    <div class="chart-row">
                        <div class="chart-card">
                            <h3>District Hourly Electricity Demand & Solar Generation [Daily Averages]</h3>
                            <div id="district-elec-chart" class="chart-div"></div>
                        </div>
                        <div class="chart-card">
                            <h3>District Heating & Domestic Hot Water (DHW) Profiles [Daily Averages]</h3>
                            <div id="district-heat-chart" class="chart-div"></div>
                        </div>
                    </div>
                    <div class="chart-card">
                        <h3>District Heating Network (DHN) Sizing Load Curve & Rolling Average</h3>
                        <div id="dhn-load-chart" class="chart-div" style="height: 350px;"></div>
                    </div>
                </div>
            </div>

            <!-- Reports and Written Answers Panel -->
            <div id="reports-panel" class="tab-panel">
                <div class="scrollable-content">
                    <div class="answers-container">
                        <h2>Laboratoire Ronquoz - Complete Answers & Energy Assessment Report</h2>
                        
                        <div class="answer-section">
                            <h4>Laboratoire 1: Heating and DHW Demand Estimation</h4>
                            <p><strong>Question 1.1: Does the district genuinely exhibit a mixed-use character as described in the statement? Which use/affectation is predominantly represented?</strong></p>
                            <p>Yes, the district is highly mixed. Based on the calculated SRE (Energy Reference Area) values, we have the following distribution:</p>
                            <ul>
                                <li><strong>Administration:</strong> 246,375 m² (33.1% of SRE) - Office buildings, public utilities, and Energypolis campus facilities.</li>
                                <li><strong>Habitat collectif:</strong> 244,023 m² (32.8% of SRE) - High-density multi-family residential apartments.</li>
                                <li><strong>Ecole:</strong> 103,033 m² (13.8% of SRE) - Educational buildings.</li>
                                <li><strong>Non chauffé:</strong> 99,383 m² (13.3% of SRE) - Warehouses, cellars, and industrial halls.</li>
                                <li><strong>Industries:</strong> 32,204 m² (4.3% of SRE) - Manufacturing and laboratories.</li>
                                <li><strong>Commerce:</strong> 14,846 m² (2.0% of SRE) - Retail and services.</li>
                                <li><strong>Installation sportive:</strong> 4,866 m² (0.7% of SRE) - Gymnasiums and sports arenas.</li>
                            </ul>
                            <p>The district shows a highly balanced mix, predominantly shared between <strong>Administration (33.1%)</strong> and <strong>Habitat collectif (32.8%)</strong>, which represents 65.9% of the total area. This provides a highly favorable condition for district heating networks due to the complementary load profiles of residential and office spaces (complementary schedules and thermal loads).</p>
                            
                            <p><strong>Question 1.2: What is the maximum power reached in this profile? What are your thoughts on these results?</strong></p>
                            <p>The peak hourly thermal demand reached in the district profile is <strong>{thermal_summary["peak_kw"]:.1f} kW (or 9.26 MW)</strong>. This represents the absolute peak when summing all buildings under winter heating load and DHW schedule. The yearly total heat demand is <strong>{thermal_summary["annual_heat_mwh"]:.1f} MWh</strong>. The results show that heating demands dominate the profile in winter, while summer demand consists purely of Domestic Hot Water (DHW), which is assumed to be scheduled from 8:00 to 20:00. This creates a distinct high-amplitude signature in winter with flat, low-level scheduling in summer, representing typical centralized thermal requirements.</p>
                        </div>
                        
                        <div class="answer-section">
                            <h4>Laboratoire 2: Photovoltaics, Electricity, and Storage Sizing</h4>
                            <p><strong>Question 2.1: Do you think the weekly electricity profiles are realistic?</strong></p>
                            <p>Yes, they are highly representative. The Administration profile peaks significantly during work hours (Monday to Friday, 8:00 to 18:00) and falls to a low baseload over weekends, showing minimal seasonal variance. On the other hand, the Industries profile shows a continuous, high baseload with typical industrial machinery schedules, exhibiting flat profiles on weekends depending on continuous shifts. The seasonal differences are minimal for appliances and lighting, although slightly higher in winter due to lighting needs. The profiles successfully represent the human and occupational dynamics of each use class.</p>
                            
                            <p><strong>Question 2.2: Observe the magnitude of the annual electrical consumption. Does it seem realistic? Can you find sources to validate?</strong></p>
                            <p>The total annual electricity consumption of the district is <strong>{elec_summary["district_load_kwh"] / 1e6:.2f} GWh</strong>. This is extremely realistic. For 645,807 m² of heated SRE (excluding the 99,383 m² of non-heated area), this translates to an average electricity density of <strong>{elec_summary["district_load_kwh"] / 645807:.1f} kWh/m²/year</strong>. According to the Swiss standard <strong>SIA 2024 (Schedules and Sizing Data)</strong> and <strong>SIA 380/4 (Electrical Energy in Buildings)</strong>, average electrical intensities are typically 15-30 kWh/m² for residential, 40-60 kWh/m² for schools, 60-100 kWh/m² for offices and administrative buildings, and significantly higher for commercial and industrial zones. Given the high share of Administration (33%) and Schools (14%) in the district, an average density of ~36 kWh/m²/year is fully validated and represents high-efficiency building services projected for the 2060 horizon.</p>
                            
                            <p><strong>Question 2.3: Storage size for 100% self-consumption: What do you think of this solution? Are there ways to optimize it?</strong></p>
                            <p>The minimum electrical storage capacity required to achieve 100% PV self-consumption is <strong>{elec_summary["storage_capacity_kwh_for_100pct_autoconsumption"] / 1e6:.2f} GWh (4,052 MWh)</strong>. This is an extremely large and completely <strong>unrealistic</strong> battery capacity for a local district. Sizing a chemical battery bank to achieve 100% self-consumption is impractical because it forces the system to store massive excess solar generation from summer and carry it over to winter (seasonal storage). The required capacity would cost hundreds of millions of CHF, require a dedicated industrial building just to house the batteries, and have a major environmental footprint.</p>
                            <p><strong>Optimization Strategies:</strong></p>
                            <ul>
                                <li><strong>Aim for an Economic Optimum:</strong> Reducing the target self-consumption rate from 100% to e.g. 80-85% decreases the required battery capacity by more than 95%, making short-term daily storage (MWh scale) economically and technically viable.</li>
                                <li><strong>Power-to-Heat / Central Thermal Storage:</strong> Thermal storage (large hot water tanks or seasonal borehole thermal energy storage - BTES) is more than 100 times cheaper per kWh than chemical batteries. Excess summer solar electricity can power heat pumps to charge the district heating network or underground thermal reservoirs.</li>
                                <li><strong>Demand-Side Management (DSM) & Smart EV Charging:</strong> Coordinating EV charging (especially during office hours in admin zones) and scheduling heat pump operations can absorb peak solar generation without chemical batteries.</li>
                            </ul>
                        </div>
                        
                        <div class="answer-section">
                            <h4>Laboratoire 3: Sizing and Optimization of the District Heating Network</h4>
                            <p><strong>Question 3.1: Sizing and Profitability Analysis (Linear Energy Density)</strong></p>
                            <p>The network design comprises <strong>{thermal_summary["total_length_km"]:.2f} km of pipes</strong> with an investment cost of <strong>{thermal_summary["total_cost_chf"] / 1e6:.2f} million CHF</strong>. The linear thermal density of the network is <strong>{thermal_summary["energy_density_mwh_per_m_per_year"]:.2f} MWh/m/year</strong>.</p>
                            <p>According to standard energy planning guidelines in Switzerland (e.g., Swiss Federal Office of Energy - SFOE), a thermal network is highly viable and profitable if its linear energy density exceeds <strong>1.5 MWh/m/year</strong>. At 1.77 MWh/m/year, the Ronquoz 21 thermal network is <strong>highly viable and guaranteed to be economically profitable</strong>, benefiting from the high SRE density and the centralized load concentration.</p>
                            
                            <p><strong>Question 3.2: Sizing Methodology Weaknesses & Adaptations</strong></p>
                            <p><strong>Main Weaknesses:</strong></p>
                            <ul>
                                <li><strong>No Thermal Heat Losses:</strong> The model assumes zero pipe heat losses. Real networks suffer 5-15% heat losses depending on pipe insulation, diameter, and soil temperature. This means our estimated heat supply from central sources is underestimated, and operating costs are slightly higher.</li>
                                <li><strong>Fixed Delta-T of 30°C:</strong> The supply and return temperatures are fixed. In reality, return temperatures vary dynamically based on building terminal units (radiators vs underfloor heating) and seasonal control strategies.</li>
                                <li><strong>Simplified Linear Diameter-Flow Constraint:</strong> The formula <code>D * 765 * 10³ - 14'500 >= ṁ</code> is a highly simplified linear fit for a maximum pressure drop of 100 Pa/m. Real hydraulic pressure drops depend quadratically on velocity, friction factors, and density.</li>
                            </ul>
                            <p><strong>Proposed Adaptations:</strong></p>
                            <ul>
                                <li>Integrate a dynamic hydraulic simulator (e.g., DHN-specific algorithms or EPANET engines) to model non-linear pressure losses and design pumps.</li>
                                <li>Implement variable-temperature modeling (e.g., 4th generation low-temperature thermal networks) where supply temperatures change based on outdoor conditions to minimize thermal losses.</li>
                                <li>Incorporate decentral thermal production, such as utilizing localized wastewater or waste heat loops alongside the aquifer and Rhone centralized inputs.</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <!-- Inject Data -->
    <script>
        const buildingsGeoJSON = {json.dumps(buildings_data)};
        const networkGeoJSON = {json.dumps(network_data)};
        const sreGrouped = {json.dumps(sre_grouped)};
        const energyGrouped = {json.dumps(energy_grouped)};
        const energyEtat = {json.dumps(energy_etat)};
        const heatProfile = {json.dumps(heat_profile_data)};
        const elecProfile = {json.dumps(elec_profile_data)};
        const dhnProfile = {json.dumps(dhn_profile_data)};
        const typicalWeeks = {json.dumps(typical_weeks)};
    </script>
    
    <!-- App Logic -->
    <script>
        // Tab switching
        document.querySelectorAll('.nav-tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
                
                tab.classList.add('active');
                const panelId = tab.getAttribute('data-panel');
                document.getElementById(panelId).classList.add('active');
                
                // Trigger map / charts redraws when tabs change
                if (panelId === 'gis-panel') {{
                    setTimeout(() => map.invalidateSize(), 100);
                }} else if (panelId === 'energy-panel') {{
                    drawEnergyCharts();
                }} else if (panelId === 'load-panel') {{
                    drawLoadCharts();
                }}
            }});
        }});

        // Initialize Map
        const map = L.map('map-container').setView([46.2246, 7.3600], 15);
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors &copy; <a href=\"https://carto.com/attributions\">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }}).addTo(map);

        // Color Maps
        const affectColors = {{
            \"Habitat collectif\": \"#E74C3C\",
            \"Administration\": \"#3498DB\",
            \"Ecole\": \"#9B59B6\",
            \"Commerce\": \"#F1C40F\",
            \"Industries\": \"#E67E22\",
            \"Installation sportive\": \"#1ABC9C\",
            \"Non chauffé\": \"#95A5A6\"
        }};

        const phaseColors = {{
            \"Phase 1\": \"#1ABC9C\",
            \"Phase 2\": \"#2ECC71\",
            \"Phase 3\": \"#3498DB\",
            \"Phase 4\": \"#9B59B6\",
            \"Existant\": \"#7F8C8D\"
        }};

        function getColorScale(value, min, max, colormap) {{
            if (max === min) return '#3498DB';
            const ratio = (value - min) / (max - min);
            
            // Jet-like or Thermal color map
            if (colormap === 'thermal') {{
                // Red-Orange-Yellow
                const r = Math.floor(255);
                const g = Math.floor(255 * (1 - ratio));
                const b = Math.floor(200 * (1 - ratio));
                return `rgb(${{r}},${{g}},${{b}})`;
            }} else if (colormap === 'blues') {{
                // Shades of blue
                const b = 255;
                const r = Math.floor(255 * (1 - ratio * 0.8));
                const g = Math.floor(255 * (1 - ratio * 0.5));
                return `rgb(${{r}},${{g}},${{b}})`;
            }} else if (colormap === 'magma') {{
                const r = Math.floor(40 + ratio * 215);
                const g = Math.floor(20 + ratio * 80);
                const b = Math.floor(90 + ratio * 50);
                return `rgb(${{r}},${{g}},${{b}})`;
            }} else if (colormap === 'greenred') {{
                const r = Math.floor(231 - ratio * 190);
                const g = Math.floor(76 + ratio * 125);
                const b = 60;
                return `rgb(${{r}},${{g}},${{b}})`;
            }}
            return '#3498DB';
        }}

        // Style layers
        let buildingsLayer;
        let networkLayer;
        let legendControl;

        function updateMapLayers() {{
            const attribute = document.getElementById('map-layer-select').value;
            
            if (buildingsLayer) {{
                map.removeLayer(buildingsLayer);
            }}
            if (legendControl) {{
                map.removeControl(legendControl);
            }}

            // Find min/max for numerical attributes
            let minVal = Infinity, maxVal = -Infinity;
            if (attribute !== 'affect' && attribute !== 'phase') {{
                buildingsGeoJSON.features.forEach(f => {{
                    const val = f.properties[attribute] || 0;
                    if (val > 0) {{
                        if (val < minVal) minVal = val;
                        if (val > maxVal) maxVal = val;
                    }}
                }});
                if (minVal === Infinity) minVal = 0;
                if (maxVal === -Infinity) maxVal = 100;
            }}

            buildingsLayer = L.geoJSON(buildingsGeoJSON, {{
                style: function(feature) {{
                    const props = feature.properties;
                    const val = props[attribute];
                    let fillCol = '#BDC3C7';
                    
                    if (attribute === 'affect') {{
                        fillCol = affectColors[val] || '#BDC3C7';
                    }} else if (attribute === 'phase') {{
                        fillCol = phaseColors[val] || '#BDC3C7';
                    }} else {{
                        const numVal = parseFloat(val) || 0;
                        if (numVal > 0) {{
                            let cmap = 'thermal';
                            if (attribute.includes('elec')) cmap = 'blues';
                            if (attribute.includes('ratio')) cmap = 'magma';
                            if (attribute === 'autonomy') cmap = 'greenred';
                            if (attribute === 'foisonnement') cmap = 'greenred';
                            if (attribute === 'inertie_thermique_h') cmap = 'blues';
                            fillCol = getColorScale(numVal, minVal, maxVal, cmap);
                        }}
                    }}
                    
                    return {{
                        fillColor: fillCol,
                        fillOpacity: 0.85,
                        color: '#2C3E50',
                        weight: 0.5
                    }};
                }},
                onEachFeature: function(feature, layer) {{
                    const p = feature.properties;
                    layer.bindPopup(`
                        <div style="font-family:'Inter', sans-serif; font-size:12px;">
                            <h4 style="margin-bottom:6px; color:var(--primary); font-size:13px; border-bottom:1px solid var(--border); padding-bottom:3px;">Building ${{p.id_unique}}</h4>
                            <table style="width:100%;">
                                <tr><td><b>Use / Affectation:</b></td><td>${{p.affect}}</td></tr>
                                <tr><td><b>Status / Etat:</b></td><td>${{p.etat}}</td></tr>
                                <tr><td><b>SRE Area:</b></td><td>${{p.sre}} m²</td></tr>
                                <tr><td><b>Annual Heat:</b></td><td>${{p.heat_ecs_annual_kwh}} kWh</td></tr>
                                <tr><td><b>Annual Elec:</b></td><td>${{p.elec_annual_kwh}} kWh</td></tr>
                                <tr><td><b>Heat/SRE ratio:</b></td><td>${{p.heat_sre_ratio}} kWh/m²</td></tr>
                                <tr><td><b>Elec/SRE ratio:</b></td><td>${{p.elec_sre_ratio}} kWh/m²</td></tr>
                                <tr><td><b>Peak Heat (No Foisonnement):</b></td><td>${{p.heat_peak_kw}} kW</td></tr>
                                <tr><td><b>Peak Heat (Foisonné):</b></td><td>${{p.heat_peak_kw_foisonnement}} kW</td></tr>
                                <tr><td><b>Foisonnement:</b></td><td>${{p.foisonnement}}</td></tr>
                                <tr><td><b>Thermal Inertia:</b></td><td>${{p.inertie_thermique_h}} h</td></tr>
                                <tr><td><b>PV Generation:</b></td><td>${{p.pv_annual_kwh}} kWh</td></tr>
                                <tr><td><b>Autonomy / SC:</b></td><td>${{p.autonomy}}% / ${{p.autoconsumption}}%</td></tr>
                            </table>
                        </div>
                    `);
                }}
            }}).addTo(map);

            // Add Map Legend
            legendControl = L.control({{ position: 'bottomright' }});
            legendControl.onAdd = function() {{
                const div = L.DomUtil.create('div', 'legend');
                
                if (attribute === 'affect') {{
                    div.innerHTML = \`<div class=\"legend-title\">Building Use</div>\`;
                    for (const [key, val] of Object.entries(affectColors)) {{
                        div.innerHTML += \`<div class=\"legend-item\"><div class=\"legend-color\" style=\"background:\${{val}};\"></div>\${{key}}</div>\`;
                    }}
                }} else if (attribute === 'phase') {{
                    div.innerHTML = \`<div class=\"legend-title\">Construction Phase</div>\`;
                    for (const [key, val] of Object.entries(phaseColors)) {{
                        div.innerHTML += \`<div class=\"legend-item\"><div class=\"legend-color\" style=\"background:\${{val}};\"></div>\${{key}}</div>\`;
                    }}
                }} else {{
                    let title = \"Value Scale\";
                    let unit = \"\";
                    let cmap = 'thermal';
                    if (attribute === 'heat_ecs_annual_kwh') {{ title = \"Heat Demand\"; unit = \" kWh\"; }}
                    if (attribute === 'elec_annual_kwh') {{ title = \"Elec Demand\"; unit = \" kWh\"; cmap = 'blues'; }}
                    if (attribute === 'heat_sre_ratio') {{ title = \"Specific Heat\"; unit = \" kWh/m²\"; cmap = 'magma'; }}
                    if (attribute === 'elec_sre_ratio') {{ title = \"Specific Elec\"; unit = \" kWh/m²\"; cmap = 'magma'; }}
                    if (attribute === 'heat_peak_kw') {{ title = \"Peak Heat (No Foisonn.)\"; unit = \" kW\"; }}
                    if (attribute === 'maxpowerqhw') {{ title = \"Peak Heat (Foisonné)\"; unit = \" kW\"; }}
                    if (attribute === 'foisonnement') {{ title = \"Foisonnement\"; unit = \"\"; cmap = 'greenred'; }}
                    if (attribute === 'inertie_thermique_h') {{ title = \"Thermal Inertia\"; unit = \" h\"; cmap = 'blues'; }}
                    if (attribute === 'pv_annual_kwh') {{ title = \"PV Generation\"; unit = \" kWh\"; }}
                    if (attribute === 'autonomy') {{ title = \"Elec Autonomy\"; unit = \"%\"; cmap = 'greenred'; }}
                    
                    div.innerHTML = \`<div class=\"legend-title\">\${{title}}</div>\`;
                    const steps = 5;
                    for (let i = 0; i <= steps; i++) {{
                        const val = minVal + (maxVal - minVal) * (i / steps);
                        const displayVal = attribute === 'autonomy'
                            ? val.toFixed(1)
                            : attribute === 'foisonnement'
                                ? val.toFixed(2)
                                : attribute === 'inertie_thermique_h'
                                    ? val.toFixed(1)
                                    : Math.round(val);
                        const color = getColorScale(val, minVal, maxVal, cmap);
                        div.innerHTML += \`<div class=\"legend-item\"><div class=\"legend-color\" style=\"background:\${{color}};\"></div>\${{displayVal}}\${{unit}}</div>\`;
                    }}
                }}
                return div;
            }};
            legendControl.addTo(map);
        }}

        // Render network edges
        function renderNetwork() {{
            if (networkLayer) {{
                map.removeLayer(networkLayer);
            }}
            
            if (!document.getElementById('toggle-network-check').checked) return;

            networkLayer = L.geoJSON(networkGeoJSON, {{
                style: function(feature) {{
                    const d = feature.properties.diameter_mm || 25;
                    let color = '#2980B9'; // street piping (DHN)
                    let dash = null;
                    if (feature.properties.edge_type.includes('building')) {{
                        color = '#E74C3C'; // branch piping (buildings branch)
                        dash = '3, 4';
                    }} else if (feature.properties.edge_type.includes('resource')) {{
                        color = '#27AE60'; // source connection
                    }}
                    
                    return {{
                        color: color,
                        weight: d * 0.04 + 1.5,
                        opacity: 0.9,
                        dashArray: dash
                    }};
                }},
                onEachFeature: function(feature, layer) {{
                    const p = feature.properties;
                    layer.bindPopup(`
                        <div style="font-family:'Inter', sans-serif; font-size:12px;">
                            <h4 style="margin-bottom:6px; color:var(--primary); font-size:13px; border-bottom:1px solid var(--border); padding-bottom:3px;">Thermal Pipe Network</h4>
                            <table>
                                <tr><td><b>Segment Type:</b></td><td>${{p.edge_type}}</td></tr>
                                <tr><td><b>Length:</b></td><td>${{parseFloat(p.length).toFixed(1)}} m</td></tr>
                                <tr><td><b>Nominal Diameter:</b></td><td>${{Math.round(p.diameter_mm)}} mm</td></tr>
                                <tr><td><b>Node A:</b></td><td>${{p.A}}</td></tr>
                                <tr><td><b>Node B:</b></td><td>${{p.B}}</td></tr>
                            </table>
                        </div>
                    `);
                }}
            }}).addTo(map);
        }}

        document.getElementById('map-layer-select').addEventListener('change', updateMapLayers);
        document.getElementById('toggle-network-check').addEventListener('change', renderNetwork);

        // Initial GIS rendering
        updateMapLayers();
        renderNetwork();

        // ---------------- PLOTLY CHARTS ---------------- //
        let energyChartsDrawn = false;
        let loadChartsDrawn = false;

        function drawEnergyCharts() {{
            if (energyChartsDrawn) return;
            
            // Pie chart of SRE by affectation
            const sreLabels = Object.keys(sreGrouped);
            const sreValues = Object.values(sreGrouped);
            
            const srePie = [{{
                values: sreValues,
                labels: sreLabels,
                type: 'pie',
                hole: 0.4,
                marker: {{
                    colors: ['#3498DB', '#E74C3C', '#9B59B6', '#95A5A6', '#E67E22', '#F1C40F', '#1ABC9C']
                }},
                textinfo: 'percent+label',
                textposition: 'inside',
            }}];
            
            const pieLayout = {{
                margin: {{l: 20, r: 20, t: 20, b: 20}},
                legend: {{orientation: 'h', y: -0.1}},
                height: 350
            }};
            
            Plotly.newPlot('sre-pie-chart', srePie, pieLayout, {{responsive: true}});

            // Annual energy per type
            const affects = Object.keys(energyGrouped);
            const heatVals = affects.map(a => energyGrouped[a].heat_ecs_annual_kwh);
            const elecVals = affects.map(a => energyGrouped[a].elec_annual_kwh);
            const pvVals = affects.map(a => energyGrouped[a].pv_annual_kwh);

            const typeBar = [
                {{ x: affects, y: heatVals, name: 'Heat Energy (Heating + DHW)', type: 'bar', marker: {{color: '#E74C3C'}} }},
                {{ x: affects, y: elecVals, name: 'Electricity Demand (Excl. Heat)', type: 'bar', marker: {{color: '#3498DB'}} }},
                {{ x: affects, y: pvVals, name: 'PV Solar Generation Potential', type: 'bar', marker: {{color: '#F1C40F'}} }}
            ];

            const barLayout = {{
                barmode: 'group',
                margin: {{l: 50, r: 20, t: 30, b: 50}},
                xaxis: {{title: 'Use / Affectation'}},
                yaxis: {{title: 'Annual Energy [kWh]'}},
                legend: {{orientation: 'h', y: 1.15}},
                height: 350
            }};

            Plotly.newPlot('energy-by-type-chart', typeBar, barLayout, {{responsive: true}});

            // Annual energy per status (etat)
            const etats = Object.keys(energyEtat);
            const heatEtat = etats.map(e => energyEtat[e].heat_ecs_annual_kwh);
            const elecEtat = etats.map(e => energyEtat[e].elec_annual_kwh);
            const pvEtat = etats.map(e => energyEtat[e].pv_annual_kwh);

            const etatBar = [
                {{ x: etats, y: heatEtat, name: 'Heat Energy (Heating + DHW)', type: 'bar', marker: {{color: '#E74C3C'}} }},
                {{ x: etats, y: elecEtat, name: 'Electricity Demand', type: 'bar', marker: {{color: '#3498DB'}} }},
                {{ x: etats, y: pvEtat, name: 'PV Solar Generation Potential', type: 'bar', marker: {{color: '#F1C40F'}} }}
            ];

            const etatLayout = {{
                barmode: 'group',
                margin: {{l: 50, r: 20, t: 30, b: 50}},
                xaxis: {{title: 'Status / Etat'}},
                yaxis: {{title: 'Annual Energy [kWh]'}},
                legend: {{orientation: 'h', y: 1.15}},
                height: 350
            }};

            Plotly.newPlot('energy-by-etat-chart', etatBar, etatLayout, {{responsive: true}});

            energyChartsDrawn = true;
        }}

        function drawLoadCharts() {{
            if (loadChartsDrawn) return;

            // District Electricity Daily Averages
            const dailyElec = [
                {{ x: elecProfile.time_str, y: elecProfile.load_kw, name: 'Electricity Load', type: 'scatter', line: {{color: '#2980B9', width: 2}} }},
                {{ x: elecProfile.time_str, y: elecProfile.pv_kw, name: 'PV Generation', type: 'scatter', line: {{color: '#F1C40F', width: 2}}, opacity: 0.7 }},
                {{ x: elecProfile.time_str, y: elecProfile.self_consumed_kw, name: 'Self-Consumed PV', type: 'scatter', line: {{color: '#2ECC71', width: 2}} }}
            ];
            const elecLayout = {{
                margin: {{l: 50, r: 20, t: 20, b: 40}},
                xaxis: {{title: 'Date'}},
                yaxis: {{title: 'Daily Average Power [kW]'}},
                legend: {{orientation: 'h', y: 1.15}},
                height: 300
            }};
            Plotly.newPlot('district-elec-chart', dailyElec, elecLayout, {{responsive: true}});

            // District Heating Daily Averages
            const dailyHeat = [
                {{ x: heatProfile.time_str, y: heatProfile.total_kw, name: 'Total Thermal Load', type: 'scatter', line: {{color: '#C0392B', width: 2.5}} }},
                {{ x: heatProfile.time_str, y: heatProfile.heating_kw, name: 'Heating only', type: 'scatter', line: {{color: '#E74C3C', width: 1.5, dash: 'dash'}} }},
                {{ x: heatProfile.time_str, y: heatProfile.ecs_kw, name: 'DHW (ECS)', type: 'scatter', line: {{color: '#E67E22', width: 1.5}} }}
            ];
            const heatLayout = {{
                margin: {{l: 50, r: 20, t: 20, b: 40}},
                xaxis: {{title: 'Date'}},
                yaxis: {{title: 'Daily Average Power [kW]'}},
                legend: {{orientation: 'h', y: 1.15}},
                height: 300
            }};
            Plotly.newPlot('district-heat-chart', dailyHeat, heatLayout, {{responsive: true}});

            // DHN Network load curve (total & 8h smoothed)
            const dhnCurves = [
                {{ x: dhnProfile.time_str, y: dhnProfile.total_kw, name: 'Network Peak load', type: 'scatter', line: {{color: '#E74C3C', width: 1}} }},
                {{ x: dhnProfile.time_str, y: dhnProfile.smoothed_kw, name: 'Rolling 8h Average Sizing', type: 'scatter', line: {{color: '#2C3E50', width: 2.5}} }}
            ];
            const dhnLayout = {{
                margin: {{l: 50, r: 20, t: 20, b: 40}},
                xaxis: {{title: 'Date'}},
                yaxis: {{title: 'Power [kW]'}},
                legend: {{orientation: 'h', y: 1.15}},
                height: 300
            }};
            Plotly.newPlot('dhn-load-chart', dhnCurves, dhnLayout, {{responsive: true}});

            // Scheds (Typical Week)
            drawTypicalWeekChart();

            loadChartsDrawn = true;
        }}

        function drawTypicalWeekChart() {{
            const season = document.getElementById('week-season-select').value;
            const hours = Array.from({{length: 168}}, (_, i) => i);
            
            const adminSched = typicalWeeks[`\${{season}}_admin`] || [];
            const indSched = typicalWeeks[`\${{season}}_ind`] || [];

            const schedTraces = [
                {{ x: hours, y: adminSched, name: 'New Administrative Building (Office)', type: 'scatter', line: {{color: '#3498DB', width: 2.5}} }},
                {{ x: hours, y: indSched, name: 'New Industrial Building (Factory)', type: 'scatter', line: {{color: '#E67E22', width: 2.5}} }}
            ];

            const weekTicks = [0, 24, 48, 72, 96, 120, 144, 168];
            const weekLabels = ['Sun 0h', 'Mon 0h', 'Tue 0h', 'Wed 0h', 'Thu 0h', 'Fri 0h', 'Sat 0h', 'Sun 24h'];

            const schedLayout = {{
                margin: {{l: 50, r: 20, t: 20, b: 40}},
                xaxis: {{
                    title: 'Day / Hour of Week',
                    tickvals: weekTicks,
                    ticktext: weekLabels
                }},
                yaxis: {{title: 'Electricity Demand Baseload [kW]'}},
                legend: {{orientation: 'h', y: 1.15}},
                height: 300
            }};

            Plotly.newPlot('typical-week-chart', schedTraces, schedLayout, {{responsive: true}});
        }}

        document.getElementById('week-season-select').addEventListener('change', drawTypicalWeekChart);

    </script>
</body>
</html>
"""

    dashboard_path = os.path.join(RESULTS_DIR, "dashboard.html")
    with open(dashboard_path, "w", encoding="utf-8") as handle:
        handle.write(html_content)
        
    print(f"Interactive dashboard successfully written to: {dashboard_path}")

if __name__ == "__main__":
    main()
