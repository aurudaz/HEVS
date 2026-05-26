from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
import pulp

from helpers import compute_df_edges_df_nodes

ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results" / "lab3"

BUILDINGS_PATH = ROOT_DIR / "results" / "lab1" / "buildings_energy.geojson"
RESOURCES_PATH = ROOT_DIR / "Laboratoire Ronquoz - 3" / "resources_ronquoz.geojson"
STREETS_PATH = ROOT_DIR / "Laboratoire Ronquoz - 3" / "road_network_ronquoz.geojson"
DISTRICT_PROFILE_PATH = ROOT_DIR / "results" / "lab1" / "district_profile.csv"

CP_KJ_PER_KG_K = 4.18
DELTA_T = 30
FLOW_FACTOR = 3600 / (CP_KJ_PER_KG_K * DELTA_T)

DIAMETERS_M = [0.025, 0.032, 0.04, 0.05, 0.065, 0.08, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]


def build_optimization(df_edges: pd.DataFrame, df_nodes: pd.DataFrame, resources: pd.DataFrame) -> tuple[pulp.LpProblem, dict]:
    edges = list(df_edges.index)
    nodes = list(df_nodes.index)

    directed_edges = []
    for u, v in edges:
        directed_edges.append((u, v))
        directed_edges.append((v, u))

    model = pulp.LpProblem("ronquoz_dhn", pulp.LpMinimize)

    m_flow = pulp.LpVariable.dicts("m_flow", directed_edges, lowBound=0)
    m_edge = pulp.LpVariable.dicts("m_edge", edges, lowBound=0)
    d_select = {
        edge: pulp.LpVariable.dicts(f"d_{edge}", DIAMETERS_M, lowBound=0, upBound=1, cat="Binary")
        for edge in edges
    }

    d_value = {
        edge: pulp.lpSum(diameter * d_select[edge][diameter] for diameter in DIAMETERS_M)
        for edge in edges
    }

    for edge in edges:
        model += pulp.lpSum(d_select[edge][diameter] for diameter in DIAMETERS_M) == 1
        model += m_edge[edge] >= m_flow[(edge[0], edge[1])]
        model += m_edge[edge] >= m_flow[(edge[1], edge[0])]
        model += m_edge[edge] <= (765000 * d_value[edge] - 14500)

    resource_limits = {row["name"]: row["max_power_kw"] * FLOW_FACTOR for _, row in resources.iterrows()}
    resource_supply = {
        node: pulp.LpVariable(f"supply_{node}", lowBound=0, upBound=resource_limits.get(node, 0))
        for node in nodes
    }

    demands = {}
    for node, row in df_nodes.iterrows():
        if row["node_type"] == "building":
            demands[node] = float(row.get("maxpowerqhw", 0)) * FLOW_FACTOR
        else:
            demands[node] = 0.0

    for node in nodes:
        inflow = pulp.lpSum(m_flow[(u, v)] for (u, v) in directed_edges if v == node)
        outflow = pulp.lpSum(m_flow[(u, v)] for (u, v) in directed_edges if u == node)
        model += inflow + resource_supply[node] - outflow == demands[node]

    total_cost = pulp.lpSum(
        (5553 * d_value[edge] + 951.35) * float(df_edges.at[edge, "length"]) for edge in edges
    )
    model += total_cost

    return model, {
        "m_flow": m_flow,
        "m_edge": m_edge,
        "d_value": d_value,
        "d_select": d_select,
        "resource_supply": resource_supply,
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    df_edges, df_nodes, buildings, resources, streets, gdf_nodes, gdf_edges = compute_df_edges_df_nodes(
        BUILDINGS_PATH, RESOURCES_PATH, STREETS_PATH
    )

    building_powers = buildings.set_index("id_unique")["maxpowerqhw"].to_dict()
    df_nodes = df_nodes.copy()
    df_nodes["maxpowerqhw"] = 0.0
    for node in df_nodes.index:
        if df_nodes.at[node, "node_type"] == "building":
            raw_id = str(node).replace("Bat_", "")
            df_nodes.at[node, "maxpowerqhw"] = float(building_powers.get(raw_id, 0.0))

    model, variables = build_optimization(df_edges, df_nodes, resources)
    model.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=120))

    diameters = {}
    for edge, d_var in variables["d_value"].items():
        diameters[edge] = pulp.value(d_var)

    gdf_edges = gdf_edges.copy()
    gdf_edges["diameter_m"] = [diameters.get(edge, 0) for edge in gdf_edges.index]
    gdf_edges["diameter_mm"] = gdf_edges["diameter_m"] * 1000
    gdf_edges.to_file(RESULTS_DIR / "network_edges.geojson", driver="GeoJSON")

    edge_flows = {edge: pulp.value(var) for edge, var in variables["m_edge"].items()}
    pd.DataFrame({"edge": list(edge_flows.keys()), "mass_flow_kg_h": list(edge_flows.values())}).to_csv(
        RESULTS_DIR / "edge_flows.csv", index=False
    )

    pd.DataFrame(
        {
            "node": df_nodes.index,
            "node_type": df_nodes["node_type"].values,
            "maxpowerqhw": df_nodes["maxpowerqhw"].values,
        }
    ).to_csv(RESULTS_DIR / "nodes_summary.csv", index=False)

    supply = {node: pulp.value(var) for node, var in variables["resource_supply"].items()}
    pd.DataFrame({"resource": list(supply.keys()), "mass_flow_kg_h": list(supply.values())}).to_csv(
        RESULTS_DIR / "resource_supply.csv", index=False
    )

    total_length_m = float(df_edges["length"].sum())
    total_cost_chf = float(((5553 * gdf_edges["diameter_m"] + 951.35) * gdf_edges["length"]).sum())

    annual_heat_kwh = 0.0
    peak_kw = 0.0
    smoothed_peak_kw = 0.0
    if DISTRICT_PROFILE_PATH.exists():
        district_profile = pd.read_csv(DISTRICT_PROFILE_PATH, parse_dates=["time"])
        total_kw = district_profile["total_kw"].astype(float)
        annual_heat_kwh = float(total_kw.sum())
        peak_kw = float(total_kw.max())
        smoothed_kw = total_kw.rolling(window=8, center=True, min_periods=1).mean()
        smoothed_peak_kw = float(smoothed_kw.max())

        load_curve = pd.DataFrame(
            {
                "time": district_profile["time"],
                "total_kw": total_kw,
                "smoothed_kw": smoothed_kw,
            }
        )
        load_curve.to_csv(RESULTS_DIR / "network_load_curve.csv", index=False)

        try:
            import plotly.graph_objects as go

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=load_curve["time"],
                    y=load_curve["total_kw"],
                    mode="lines",
                    name="Charge totale",
                    line={"width": 1},
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=load_curve["time"],
                    y=load_curve["smoothed_kw"],
                    mode="lines",
                    name="Moyenne glissante 8h",
                    line={"width": 3},
                )
            )
            fig.update_layout(
                title="Courbe de charge du réseau",
                yaxis_title="Puissance (kW)",
                xaxis_title="Heure",
                hovermode="x unified",
            )
            fig.write_html(RESULTS_DIR / "network_load_curve.html", include_plotlyjs="cdn")
        except ImportError:
            pass

    annual_heat_mwh = annual_heat_kwh / 1000 if annual_heat_kwh else 0.0
    energy_density_mwh_per_m = annual_heat_mwh / total_length_m if total_length_m else 0.0

    summary = {
        "total_length_m": total_length_m,
        "total_length_km": total_length_m / 1000 if total_length_m else 0.0,
        "total_cost_chf": total_cost_chf,
        "annual_heat_kwh": annual_heat_kwh,
        "annual_heat_mwh": annual_heat_mwh,
        "energy_density_mwh_per_m_per_year": energy_density_mwh_per_m,
        "peak_kw": peak_kw,
        "smoothed_peak_kw": smoothed_peak_kw,
    }
    pd.DataFrame([summary]).to_csv(RESULTS_DIR / "network_summary.csv", index=False)
    (RESULTS_DIR / "network_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
