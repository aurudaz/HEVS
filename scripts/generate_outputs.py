from __future__ import annotations

import ast
import csv
import json
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"
LAB1_DIR = RESULTS_DIR / "lab1"
LAB2_DIR = RESULTS_DIR / "lab2"
LAB3_DIR = RESULTS_DIR / "lab3"

OUTPUT_DASHBOARD = ROOT_DIR / "dashboard.html"
OUTPUT_REPORT_MD = ROOT_DIR / "report.md"
OUTPUT_REPORT_PDF = ROOT_DIR / "report.pdf"

DELTA_T_C = 30
FLOW_FACTOR = 3600 / (4.18 * DELTA_T_C)


@dataclass
class Summary:
    generated_at: str
    building_count: int
    sre_total_m2: float
    affect_counts: dict
    annual_heat_kwh: float
    annual_ecs_kwh: float
    annual_total_kwh: float
    peak_kw: float
    peak_foisonnement_kw: float
    lab2_summary: dict
    lab2_peak_load_kw: float
    lab2_peak_pv_kw: float
    lab2_peak_self_kw: float
    lab3_summary: dict
    lab3_peak_kw: float
    lab3_smoothed_peak_kw: float
    resources: list


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def format_number(value: float, decimals: int = 0) -> str:
    formatted = f"{value:,.{decimals}f}"
    return formatted.replace(",", " ")


def dump_json_for_script(data: dict) -> str:
    return json.dumps(data).replace("</", "<\\/")


def load_edge_flows() -> dict[tuple[str, str], float]:
    flows: dict[tuple[str, str], float] = {}
    for row in read_csv(LAB3_DIR / "edge_flows.csv"):
        edge_value = row.get("edge")
        if not edge_value:
            continue
        try:
            edge = ast.literal_eval(edge_value)
        except (ValueError, SyntaxError):
            continue
        if isinstance(edge, (list, tuple)) and len(edge) == 2:
            flows[(str(edge[0]), str(edge[1]))] = to_float(row.get("mass_flow_kg_h"))
    return flows


def load_resources_geojson() -> dict:
    path = ROOT_DIR / "Laboratoire Ronquoz - 3" / "resources_ronquoz.geojson"
    if path.exists():
        return json.loads(path.read_text())
    return {"type": "FeatureCollection", "features": []}


def summarize() -> Summary:
    buildings_geojson = json.loads((LAB1_DIR / "buildings_energy.geojson").read_text())
    properties = [feature.get("properties", {}) for feature in buildings_geojson.get("features", [])]

    building_count = len(properties)
    sre_total = sum(to_float(prop.get("sre")) for prop in properties)
    annual_heat_kwh = sum(to_float(prop.get("heat_annual_kwh")) for prop in properties)
    annual_ecs_kwh = sum(to_float(prop.get("ecs_annual_kwh")) for prop in properties)
    annual_total_kwh = sum(to_float(prop.get("heat_ecs_annual_kwh")) for prop in properties)

    affect_counts: dict[str, int] = {}
    for prop in properties:
        affect = prop.get("affect") or "Inconnu"
        affect_counts[affect] = affect_counts.get(affect, 0) + 1

    lab1_profile = read_csv(LAB1_DIR / "district_profile.csv")
    peak_kw = max(to_float(row["total_kw"]) for row in lab1_profile)

    building_peaks = read_csv(LAB1_DIR / "building_peaks.csv")
    peak_foisonnement_kw = sum(to_float(row["heat_peak_kw_foisonnement"]) for row in building_peaks)

    lab2_summary = json.loads((LAB2_DIR / "district_summary.json").read_text())
    lab2_profile = read_csv(LAB2_DIR / "district_profile.csv")
    lab2_peak_load_kw = max(to_float(row["load_kw"]) for row in lab2_profile)
    lab2_peak_pv_kw = max(to_float(row["pv_kw"]) for row in lab2_profile)
    lab2_peak_self_kw = max(to_float(row["self_consumed_kw"]) for row in lab2_profile)

    lab3_summary = json.loads((LAB3_DIR / "network_summary.json").read_text())
    lab3_load_curve = read_csv(LAB3_DIR / "network_load_curve.csv")
    lab3_peak_kw = max(to_float(row["total_kw"]) for row in lab3_load_curve)
    lab3_smoothed_peak_kw = max(to_float(row["smoothed_kw"]) for row in lab3_load_curve)

    resources = []
    for row in read_csv(LAB3_DIR / "resource_supply.csv"):
        flow = to_float(row["mass_flow_kg_h"])
        if flow <= 0:
            continue
        resources.append(
            {
                "resource": row["resource"],
                "mass_flow_kg_h": flow,
                "power_kw": flow / FLOW_FACTOR,
            }
        )
    resources.sort(key=lambda item: item["power_kw"], reverse=True)

    return Summary(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        building_count=building_count,
        sre_total_m2=sre_total,
        affect_counts=affect_counts,
        annual_heat_kwh=annual_heat_kwh,
        annual_ecs_kwh=annual_ecs_kwh,
        annual_total_kwh=annual_total_kwh,
        peak_kw=peak_kw,
        peak_foisonnement_kw=peak_foisonnement_kw,
        lab2_summary=lab2_summary,
        lab2_peak_load_kw=lab2_peak_load_kw,
        lab2_peak_pv_kw=lab2_peak_pv_kw,
        lab2_peak_self_kw=lab2_peak_self_kw,
        lab3_summary=lab3_summary,
        lab3_peak_kw=lab3_peak_kw,
        lab3_smoothed_peak_kw=lab3_smoothed_peak_kw,
        resources=resources,
    )


def wrap_lines(lines: Iterable[str], width: int) -> list[str]:
    wrapped: list[str] = []
    for line in lines:
        if not line.strip():
            wrapped.append("")
            continue
        wrapped.extend(textwrap.wrap(line, width=width, replace_whitespace=False))
    return wrapped


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_pdf(path: Path, lines: list[str]) -> None:
    lines_per_page = 48
    pages = [lines[i : i + lines_per_page] for i in range(0, len(lines), lines_per_page)]

    objects: list[str] = []
    font_obj_id = 3

    for page_index, page_lines in enumerate(pages, start=0):
        content_lines = ["BT", "/F1 11 Tf", "72 770 Td"]
        for line in page_lines:
            content_lines.append(f"({escape_pdf_text(line)}) Tj")
            content_lines.append("0 -14 Td")
        content_lines.append("ET")
        content_stream = "\n".join(content_lines)
        content_obj = f"<< /Length {len(content_stream.encode('utf-8'))} >>\nstream\n{content_stream}\nendstream"
        objects.append(content_obj)

        content_obj_id = 4 + page_index * 2
        page_obj = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Contents {content_obj_id} 0 R "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> >>"
        )
        objects.append(page_obj)

    kids = " ".join(f"{5 + idx * 2} 0 R" for idx in range(len(pages)))
    pages_obj = f"<< /Type /Pages /Kids [ {kids} ] /Count {len(pages)} >>"
    catalog_obj = "<< /Type /Catalog /Pages 2 0 R >>"
    font_obj = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    ordered_objects = [catalog_obj, pages_obj, font_obj] + objects

    output = ["%PDF-1.4"]
    xref_positions = [0]

    for obj_index, obj_content in enumerate(ordered_objects, start=1):
        xref_positions.append(sum(len(chunk.encode("utf-8")) + 1 for chunk in output))
        output.append(f"{obj_index} 0 obj")
        output.append(obj_content)
        output.append("endobj")

    xref_start = sum(len(chunk.encode("utf-8")) + 1 for chunk in output)
    output.append(f"xref\n0 {len(ordered_objects)+1}")
    output.append("0000000000 65535 f ")
    for pos in xref_positions[1:]:
        output.append(f"{pos:010d} 00000 n ")

    output.append(
        "trailer\n"
        f"<< /Size {len(ordered_objects)+1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF"
    )

    path.write_bytes("\n".join(output).encode("utf-8"))


def build_report_markdown(summary: Summary) -> str:
    lab2 = summary.lab2_summary
    lab3 = summary.lab3_summary

    resources_table = "\n".join(
        f"| {item['resource']} | {format_number(item['power_kw'], 1)} | {format_number(item['mass_flow_kg_h'], 0)} |"
        for item in summary.resources
    )

    return f"""# Ronquoz district energy report

Generated: {summary.generated_at}

## Executive summary

- **Buildings analysed:** {summary.building_count}
- **Total SRE:** {format_number(summary.sre_total_m2, 0)} m²
- **Annual heat + ECS:** {format_number(summary.annual_total_kwh / 1000, 1)} MWh/an
- **Peak heat demand (hourly):** {format_number(summary.peak_kw, 0)} kW
- **Diversified peak (foisonnement):** {format_number(summary.peak_foisonnement_kw, 0)} kW
- **Annual district electricity load:** {format_number(lab2['district_load_kwh'] / 1000, 1)} MWh/an
- **Annual PV production:** {format_number(lab2['district_pv_kwh'] / 1000, 1)} MWh/an
- **Network length:** {format_number(lab3['total_length_km'], 2)} km
- **Network CAPEX:** {format_number(lab3['total_cost_chf'], 0)} CHF

## Labo 1 – Thermal demand characterization

The heating and ECS demand is derived from SIA 380/1 tables, the building SRE and envelope factors. An hourly profile is built with the MeteoSuisse temperature series and a simplified ECS schedule (08:00–20:00). Thermal inertia and foisonnement factors are applied to approximate diversity between buildings.

**Key outputs**

- Annual heating: {format_number(summary.annual_heat_kwh / 1000, 1)} MWh/an
- Annual ECS: {format_number(summary.annual_ecs_kwh / 1000, 1)} MWh/an
- Annual total heat: {format_number(summary.annual_total_kwh / 1000, 1)} MWh/an
- Peak heat demand (hourly): {format_number(summary.peak_kw, 0)} kW
- Peak demand with foisonnement: {format_number(summary.peak_foisonnement_kw, 0)} kW

Maps and graphs: SRE by affectation, district heat profile.

## Labo 2 – Electricity and PV self-consumption

Electricity loads are read from the consumption workbook. PV production is modelled with PVGIS profiles for east/west orientations and installed surface. Autoconsumption and autonomy are computed on an hourly basis.

**Key outputs**

- Annual electricity load: {format_number(lab2['district_load_kwh'] / 1000, 1)} MWh/an
- Annual PV production: {format_number(lab2['district_pv_kwh'] / 1000, 1)} MWh/an
- Autoconsumption: {lab2['district_autoconsumption'] * 100:.1f}%
- Autonomy: {lab2['district_autonomy'] * 100:.1f}%
- Storage capacity for 100% autoconsumption: {format_number(lab2['storage_capacity_kwh_for_100pct_autoconsumption'] / 1000, 1)} MWh
- Peak load: {format_number(summary.lab2_peak_load_kw, 0)} kW
- Peak PV: {format_number(summary.lab2_peak_pv_kw, 0)} kW

Maps and graphs: electricity/heat energy maps, typical weekly profiles.

## Labo 3 – District heating network optimization (focus)

The optimization uses the road network as the backbone and connects buildings/resources to the nearest street edge. Each pipe segment is assigned a diameter from a discrete catalogue and sized to carry the required mass flow at ΔT = 30°C. The objective is to minimize a linearized CAPEX function based on diameter and length. The heat demand is taken from the Labo 1 peak power (after foisonnement).

**Key outputs**

- Network length: {format_number(lab3['total_length_km'], 2)} km
- CAPEX (pipes only): {format_number(lab3['total_cost_chf'], 0)} CHF
- Annual heat served: {format_number(lab3['annual_heat_mwh'], 1)} MWh/an
- Energy density: {format_number(lab3['energy_density_mwh_per_m_per_year'] * 1000, 1)} MWh/km/an
- Peak heat demand (hourly): {format_number(summary.lab3_peak_kw, 0)} kW
- Smoothed peak (8h rolling): {format_number(summary.lab3_smoothed_peak_kw, 0)} kW

**Supply dispatch (optimized)**

| Resource | Power (kW) | Mass flow (kg/h) |
| --- | --- | --- |
{resources_table}

### Limitations and why the sizing can be too large

- **Peak-based sizing:** the network is sized to the hourly peak demand. Short peaks drive large diameters even when the energy-weighted demand is lower. The 8‑hour smoothed peak is about {format_number(summary.lab3_smoothed_peak_kw, 0)} kW, which is below the instantaneous peak of {format_number(summary.lab3_peak_kw, 0)} kW.
- **No temporal diversity inside the optimization:** foisonnement is applied once to the building peaks, but the optimization still assumes the full diversified peak occurs simultaneously on every branch.
- **No thermal losses or return temperature constraints:** heat losses, pump constraints, and operational limits are not modelled, so margins are implicitly absorbed by pipe sizing rather than control strategies.
- **Static resource dispatch:** resources are constrained only by max power, with no cost hierarchy, startup limits, or seasonal availability.

### Suggested next steps

- Re-size pipes based on a design percentile (e.g., 95th) or use the 8‑hour smoothed peak as the reference.
- Add pipe heat losses, pumping power, and velocity constraints to avoid overly large diameters.
- Validate demand with measured profiles and update foisonnement per affectation.
- Evaluate staged deployment to prioritize high energy density corridors.

## Summary of key numbers

| Category | Value |
| --- | --- |
| Buildings | {summary.building_count} |
| Total SRE | {format_number(summary.sre_total_m2, 0)} m² |
| Annual heat + ECS | {format_number(summary.annual_total_kwh / 1000, 1)} MWh/an |
| Peak heat demand | {format_number(summary.peak_kw, 0)} kW |
| Diversified peak | {format_number(summary.peak_foisonnement_kw, 0)} kW |
| Annual electricity load | {format_number(lab2['district_load_kwh'] / 1000, 1)} MWh/an |
| Annual PV production | {format_number(lab2['district_pv_kwh'] / 1000, 1)} MWh/an |
| Network length | {format_number(lab3['total_length_km'], 2)} km |
| Pipe CAPEX | {format_number(lab3['total_cost_chf'], 0)} CHF |
"""


def build_report_text(summary: Summary) -> list[str]:
    lab2 = summary.lab2_summary
    lab3 = summary.lab3_summary
    lines = [
        "Ronquoz district energy report",
        f"Generated: {summary.generated_at}",
        "",
        "Executive summary",
        f"- Buildings analysed: {summary.building_count}",
        f"- Total SRE: {format_number(summary.sre_total_m2, 0)} m2",
        f"- Annual heat + ECS: {format_number(summary.annual_total_kwh / 1000, 1)} MWh/an",
        f"- Peak heat demand (hourly): {format_number(summary.peak_kw, 0)} kW",
        f"- Diversified peak (foisonnement): {format_number(summary.peak_foisonnement_kw, 0)} kW",
        f"- Annual district electricity load: {format_number(lab2['district_load_kwh'] / 1000, 1)} MWh/an",
        f"- Annual PV production: {format_number(lab2['district_pv_kwh'] / 1000, 1)} MWh/an",
        f"- Network length: {format_number(lab3['total_length_km'], 2)} km",
        f"- Network CAPEX: {format_number(lab3['total_cost_chf'], 0)} CHF",
        "",
        "Labo 1 - Thermal demand characterization",
        "The heating and ECS demand is derived from SIA 380/1 tables, the building SRE",
        "and envelope factors. An hourly profile is built with the MeteoSuisse temperature",
        "series and a simplified ECS schedule (08:00-20:00). Thermal inertia and",
        "foisonnement factors are applied to approximate diversity between buildings.",
        "",
        "Key outputs:",
        f"- Annual heating: {format_number(summary.annual_heat_kwh / 1000, 1)} MWh/an",
        f"- Annual ECS: {format_number(summary.annual_ecs_kwh / 1000, 1)} MWh/an",
        f"- Annual total heat: {format_number(summary.annual_total_kwh / 1000, 1)} MWh/an",
        f"- Peak heat demand (hourly): {format_number(summary.peak_kw, 0)} kW",
        f"- Peak demand with foisonnement: {format_number(summary.peak_foisonnement_kw, 0)} kW",
        "",
        "Labo 2 - Electricity and PV self-consumption",
        "Electricity loads are read from the consumption workbook. PV production is",
        "modelled with PVGIS profiles for east/west orientations and installed surface.",
        "Autoconsumption and autonomy are computed on an hourly basis.",
        "",
        "Key outputs:",
        f"- Annual electricity load: {format_number(lab2['district_load_kwh'] / 1000, 1)} MWh/an",
        f"- Annual PV production: {format_number(lab2['district_pv_kwh'] / 1000, 1)} MWh/an",
        f"- Autoconsumption: {lab2['district_autoconsumption'] * 100:.1f}%",
        f"- Autonomy: {lab2['district_autonomy'] * 100:.1f}%",
        f"- Storage capacity for 100% autoconsumption: {format_number(lab2['storage_capacity_kwh_for_100pct_autoconsumption'] / 1000, 1)} MWh",
        f"- Peak load: {format_number(summary.lab2_peak_load_kw, 0)} kW",
        f"- Peak PV: {format_number(summary.lab2_peak_pv_kw, 0)} kW",
        "",
        "Labo 3 - District heating network optimization (focus)",
        "The optimization uses the road network as the backbone and connects buildings",
        "and resources to the nearest street edge. Each pipe segment is assigned a",
        "diameter from a discrete catalogue and sized to carry the required mass flow",
        "at Delta T = 30C. The objective is to minimize a linearized CAPEX function",
        "based on diameter and length. The heat demand is taken from the Labo 1",
        "peak power (after foisonnement).",
        "",
        "Key outputs:",
        f"- Network length: {format_number(lab3['total_length_km'], 2)} km",
        f"- CAPEX (pipes only): {format_number(lab3['total_cost_chf'], 0)} CHF",
        f"- Annual heat served: {format_number(lab3['annual_heat_mwh'], 1)} MWh/an",
        f"- Energy density: {format_number(lab3['energy_density_mwh_per_m_per_year'] * 1000, 1)} MWh/km/an",
        f"- Peak heat demand (hourly): {format_number(summary.lab3_peak_kw, 0)} kW",
        f"- Smoothed peak (8h rolling): {format_number(summary.lab3_smoothed_peak_kw, 0)} kW",
        "",
        "Supply dispatch (optimized):",
    ]

    for item in summary.resources:
        lines.append(
            f"- {item['resource']}: {format_number(item['power_kw'], 1)} kW "
            f"({format_number(item['mass_flow_kg_h'], 0)} kg/h)"
        )

    lines += [
        "",
        "Limitations and why the sizing can be too large:",
        "- Peak-based sizing: the network is sized to the hourly peak demand. Short peaks",
        "  drive large diameters even when the energy-weighted demand is lower. The",
        f"  8-hour smoothed peak is about {format_number(summary.lab3_smoothed_peak_kw, 0)} kW",
        f"  versus {format_number(summary.lab3_peak_kw, 0)} kW instantaneous.",
        "- No temporal diversity inside the optimization: foisonnement is applied once",
        "  to building peaks, but the optimization still assumes the full diversified",
        "  peak occurs simultaneously on every branch.",
        "- No thermal losses or return temperature constraints: heat losses, pump",
        "  constraints, and operational limits are not modelled, so margins are implicitly",
        "  absorbed by pipe sizing rather than control strategies.",
        "- Static resource dispatch: resources are constrained only by max power,",
        "  with no cost hierarchy, startup limits, or seasonal availability.",
        "",
        "Suggested next steps:",
        "- Re-size pipes based on a design percentile (e.g., 95th) or use the 8-hour",
        "  smoothed peak as the reference.",
        "- Add pipe heat losses, pumping power, and velocity constraints to avoid",
        "  overly large diameters.",
        "- Validate demand with measured profiles and update foisonnement per",
        "  affectation.",
        "- Evaluate staged deployment to prioritize high energy density corridors.",
    ]

    return wrap_lines(lines, width=100)


def build_dashboard(summary: Summary) -> str:
    lab2 = summary.lab2_summary
    lab3 = summary.lab3_summary

    def json_for_script(path: Path) -> str:
        data = json.loads(path.read_text())
        return dump_json_for_script(data)

    buildings_heat = json_for_script(LAB1_DIR / "buildings_energy.geojson")
    buildings_elec = json_for_script(LAB2_DIR / "buildings_electricity.geojson")
    network_edges_data = json.loads((LAB3_DIR / "network_edges.geojson").read_text())
    edge_flows = load_edge_flows()
    for feature in network_edges_data.get("features", []):
        props = feature.setdefault("properties", {})
        node_a = props.get("A") or props.get("level_0")
        node_b = props.get("B") or props.get("level_1")
        flow = 0.0
        if node_a is not None and node_b is not None:
            edge_key = (str(node_a), str(node_b))
            flow = edge_flows.get(edge_key)
            if flow is None:
                flow = edge_flows.get((edge_key[1], edge_key[0]), 0.0)
        props["mass_flow_kg_h"] = flow
        props["power_kw"] = flow / FLOW_FACTOR if flow else 0.0
        props["delta_t_c"] = DELTA_T_C
    network_edges = dump_json_for_script(network_edges_data)
    resources = dump_json_for_script(load_resources_geojson())

    cards = [
        ("Buildings", f"{summary.building_count}"),
        ("Total SRE", f"{format_number(summary.sre_total_m2, 0)} m²"),
        ("Annual heat + ECS", f"{format_number(summary.annual_total_kwh / 1000, 1)} MWh"),
        ("Peak heat", f"{format_number(summary.peak_kw, 0)} kW"),
        ("Diversified peak", f"{format_number(summary.peak_foisonnement_kw, 0)} kW"),
        ("PV production", f"{format_number(lab2['district_pv_kwh'] / 1000, 1)} MWh"),
        ("Network length", f"{format_number(lab3['total_length_km'], 2)} km"),
        ("Pipe CAPEX", f"{format_number(lab3['total_cost_chf'], 0)} CHF"),
    ]
    cards_html = "".join(
        f"<div class='card'><div class='card-title'>{title}</div><div class='card-value'>{value}</div></div>"
        for title, value in cards
    )

    resource_rows = "".join(
        f"<tr><td>{item['resource']}</td><td>{format_number(item['power_kw'], 1)}</td><td>{format_number(item['mass_flow_kg_h'], 0)}</td></tr>"
        for item in summary.resources
    )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Ronquoz District Energy Dashboard</title>
  <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\" />
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; color: #1c1c1c; background: #f6f7f9; }}
    header {{ padding: 24px 32px; background: #1b3b5f; color: #fff; }}
    header h1 {{ margin: 0 0 6px 0; font-size: 26px; }}
    header p {{ margin: 0; opacity: 0.85; }}
    main {{ padding: 24px 32px 48px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }}
    .card {{ background: #fff; padding: 14px 16px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }}
    .card-title {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #5a6675; }}
    .card-value {{ margin-top: 6px; font-size: 18px; font-weight: 600; }}
    .section {{ background: #fff; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }}
    .section h2 {{ margin-top: 0; }}
    .grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
    .figure img {{ width: 100%; border-radius: 8px; border: 1px solid #e2e6ea; }}
    .map {{ height: 360px; border-radius: 8px; border: 1px solid #e2e6ea; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 8px 6px; border-bottom: 1px solid #e6eaee; text-align: left; }}
    th {{ background: #f2f4f7; }}
    footer {{ margin-top: 24px; font-size: 12px; color: #6a7280; }}
  </style>
</head>
<body>
<header>
  <h1>Ronquoz District Energy Dashboard</h1>
  <p>Generated: {summary.generated_at}</p>
</header>
<main>
  <section class=\"cards\">{cards_html}</section>

  <section class=\"section\">
    <h2>Maps</h2>
    <div class=\"grid-2\">
      <div>
        <h3>Labo 1 – Annual heat + ECS (kWh)</h3>
        <div id=\"map-heat\" class=\"map\"></div>
      </div>
      <div>
        <h3>Labo 2 – Annual electricity (kWh)</h3>
        <div id=\"map-elec\" class=\"map\"></div>
      </div>
    </div>
    <div style=\"margin-top:16px\">
      <h3>Labo 3 – Full heat network (diameter, power, temperatures)</h3>
      <div id=\"map-network\" class=\"map\"></div>
    </div>
  </section>

  <section class=\"section\">
    <h2>Graphs</h2>
    <div class=\"grid-2\">
      <div class=\"figure\">
        <h3>Labo 1 – District heat profile</h3>
        <img src=\"results/lab1/district_profile.png\" alt=\"District heat profile\" />
      </div>
      <div class=\"figure\">
        <h3>Labo 1 – SRE by affectation</h3>
        <img src=\"results/lab1/sre_by_affectation.png\" alt=\"SRE by affectation\" />
      </div>
      <div class=\"figure\">
        <h3>Labo 2 – Typical week profiles</h3>
        <img src=\"results/lab2/typical_week_profiles.png\" alt=\"Typical week profiles\" />
      </div>
      <div class=\"figure\">
        <h3>Labo 3 – Network load curve</h3>
        <img src=\"results/lab3/network_load_curve.png\" alt=\"Network load curve\" />
      </div>
      <div class=\"figure\">
        <h3>Labo 3 – Network graph</h3>
        <img src=\"results/lab3/network_graph.png\" alt=\"Network graph\" />
      </div>
    </div>
  </section>

  <section class=\"section\">
    <h2>Labo 3 – Supply dispatch (optimized)</h2>
    <table>
      <thead><tr><th>Resource</th><th>Power (kW)</th><th>Mass flow (kg/h)</th></tr></thead>
      <tbody>
        {resource_rows}
      </tbody>
    </table>
  </section>

  <section class=\"section\">
    <h2>Limitations and oversizing risk</h2>
    <ul>
      <li>Pipe sizing is driven by the hourly peak demand (instantaneous). Short peaks inflate diameters compared to an energy‑weighted or percentile design.</li>
      <li>Foisonnement is applied only once; the optimization still assumes the diversified peak occurs simultaneously on every branch.</li>
      <li>Thermal losses, pump constraints, and return temperature limits are not modelled, so safety margins are absorbed by pipe sizing.</li>
      <li>Resource dispatch is static (max power only) without cost or availability constraints.</li>
    </ul>
  </section>

  <footer>
    Open this dashboard via a local web server (e.g., <code>python -m http.server</code>) to allow the maps to load geojson data and tiles.
  </footer>
</main>

<script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\"></script>
<script>
  const buildingsHeat = {buildings_heat};
  const buildingsElec = {buildings_elec};
  const networkEdges = {network_edges};
const resources = {resources};

  function getNumericValues(geojson, key) {{
    return geojson.features
      .map(f => Number(f.properties?.[key]))
      .filter(v => !Number.isNaN(v));
  }}

  function colorScale(value, min, max) {{
    const ratio = (value - min) / (max - min || 1);
    const colors = ['#eff3ff', '#bdd7e7', '#6baed6', '#3182bd', '#08519c'];
    const index = Math.max(0, Math.min(colors.length - 1, Math.floor(ratio * (colors.length - 1))));
    return colors[index];
  }}

  function formatNumber(value, decimals = 0) {{
    const number = Number(value);
    if (Number.isNaN(number)) {{
      return '0';
    }}
    return number.toFixed(decimals);
  }}

  function addResources(map, geojson) {{
    if (!geojson || !geojson.features || geojson.features.length === 0) {{
      return null;
    }}
    const layer = L.geoJSON(geojson, {{
      pointToLayer: (feature, latlng) =>
        L.circleMarker(latlng, {{
          radius: 6,
          color: '#1b3b5f',
          weight: 2,
          fillColor: '#1b3b5f',
          fillOpacity: 0.9
        }}),
      onEachFeature: (feature, layer) => {{
        const props = feature.properties || {{}};
        const name = props.name || props.id || 'Resource';
        const maxPower = Number(props.max_power_kw) || 0;
        const minPower = Number(props.min_power_kw) || 0;
        const supply = props.t_supply;
        const deltaT = props.delta_t;
        const network = props.reseau || '';
        const lines = [
          `<strong>${{name}}</strong>`,
          network ? `Network: ${{network}}` : null,
          `Max power: ${{formatNumber(maxPower, 0)}} kW`,
          minPower ? `Min power: ${{formatNumber(minPower, 0)}} kW` : null,
          Number.isFinite(supply) ? `Supply: ${{formatNumber(supply, 0)}} °C` : null,
          Number.isFinite(deltaT) ? `ΔT: ${{formatNumber(deltaT, 0)}} °C` : null
        ].filter(Boolean);
        layer.bindTooltip(lines.join('<br>'));
      }}
    }}).addTo(map);
    return layer;
  }}

  function createChoropleth(mapId, geojson, valueKey, label) {{
    const map = L.map(mapId);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const values = getNumericValues(geojson, valueKey);
    const min = Math.min(...values);
    const max = Math.max(...values);

    const layer = L.geoJSON(geojson, {{
      style: feature => {{
        const value = Number(feature.properties?.[valueKey]) || 0;
        return {{
          color: '#394b59',
          weight: 0.7,
          fillOpacity: 0.75,
          fillColor: colorScale(value, min, max)
        }};
      }},
      onEachFeature: (feature, layer) => {{
        const value = Number(feature.properties?.[valueKey]) || 0;
        const id = feature.properties?.id_unique || feature.properties?.ID || 'N/A';
        layer.bindTooltip(`${{label}}<br><strong>${{id}}</strong><br>${{value.toFixed(0)}}`);
      }}
    }}).addTo(map);

    map.fitBounds(layer.getBounds(), {{ padding: [10, 10] }});
  }}

  function createNetworkMap(mapId, geojson, resourceGeojson) {{
    const map = L.map(mapId);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const layer = L.geoJSON(geojson, {{
      style: feature => {{
        const diameter = Number(feature.properties?.diameter_mm) || 0;
        return {{
          color: '#d35400',
          weight: Math.max(1.5, Math.min(6, diameter / 50)),
          opacity: 0.9
        }};
      }},
      onEachFeature: (feature, layer) => {{
        const props = feature.properties || {{}};
        const diameter = Number(props.diameter_mm) || 0;
        const flow = Number(props.mass_flow_kg_h) || 0;
        const power = Number(props.power_kw) || 0;
        const deltaT = Number(props.delta_t_c) || 0;
        const edgeLabel = props.A && props.B ? `${{props.A}} → ${{props.B}}` : 'Network edge';
        const lines = [
          `<strong>${{edgeLabel}}</strong>`,
          `Diameter: ${{formatNumber(diameter, 0)}} mm`,
          `Flow: ${{formatNumber(flow, 0)}} kg/h`,
          `Power: ${{formatNumber(power, 1)}} kW`,
          `ΔT (model): ${{formatNumber(deltaT, 0)}} °C`
        ];
        layer.bindTooltip(lines.join('<br>'));
      }}
    }}).addTo(map);

    const resourceLayer = addResources(map, resourceGeojson);
    const boundsLayer = resourceLayer ? L.featureGroup([layer, resourceLayer]) : layer;
    map.fitBounds(boundsLayer.getBounds(), {{ padding: [10, 10] }});
  }}

  createChoropleth('map-heat', buildingsHeat, 'heat_ecs_annual_kwh', 'Annual heat + ECS (kWh)');
  createChoropleth('map-elec', buildingsElec, 'elec_annual_kwh', 'Annual electricity (kWh)');
  createNetworkMap('map-network', networkEdges, resources);
</script>
</body>
</html>"""


def main() -> None:
    summary = summarize()

    OUTPUT_REPORT_MD.write_text(build_report_markdown(summary))
    report_lines = build_report_text(summary)
    write_pdf(OUTPUT_REPORT_PDF, report_lines)
    OUTPUT_DASHBOARD.write_text(build_dashboard(summary))

    print(f"Wrote {OUTPUT_REPORT_MD}")
    print(f"Wrote {OUTPUT_REPORT_PDF}")
    print(f"Wrote {OUTPUT_DASHBOARD}")


if __name__ == "__main__":
    main()
