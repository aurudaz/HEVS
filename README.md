# Ronquoz district energy dashboard & report

This repository contains the three lab workflows (Labo 1–3) and the generated dashboard + report that consolidate all maps, graphs, and key numbers. The focus is on Labo 3 (district heating network optimization) with an explicit discussion of sizing limitations.

## Outputs

- **dashboard.html** – Interactive dashboard with all maps and graphs.
- **report.pdf** – PDF report with detailed explanation and Labo 3 focus.
- **report.md** – Markdown source for the report (easy to edit).

## How to view the dashboard

Because the dashboard loads GeoJSON and online map tiles, open it through a local web server:

```bash
cd /tmp/workspace/aurudaz/HEVS
python -m http.server
```

Then open [http://localhost:8000/dashboard.html](http://localhost:8000/dashboard.html).

## How to regenerate the outputs

The generator uses only the Python standard library.

```bash
python scripts/generate_outputs.py
```

This rewrites `dashboard.html`, `report.md`, and `report.pdf` from the data in `results/`.

## Summary of key numbers

| Category | Value |
| --- | --- |
| Buildings | 196 |
| Total SRE | 744 731 m² |
| Annual heat + ECS | 26 147.8 MWh/an |
| Peak heat demand | 9 259 kW |
| Diversified peak (foisonnement) | 7 222 kW |
| Annual electricity load | 23 371.9 MWh/an |
| Annual PV production | 19 318.9 MWh/an |
| Network length | 14.77 km |
| Pipe CAPEX | 16 736 196 CHF |

## Labo 3 focus – sizing limitations

The current network sizing is intentionally conservative:

- The optimization uses the **hourly peak demand**. Short peaks inflate pipe diameters compared to a percentile or smoothed design.
- **Foisonnement is applied only once**, so the optimized network still assumes the diversified peak occurs simultaneously in every branch.
- **Thermal losses, pumping limits, and return temperature constraints** are not modeled, so margins are absorbed by oversizing.
- **Resource dispatch is static** (max power only), with no cost or availability constraints.

For sizing closer to operational reality, the report proposes re-sizing based on a design percentile (e.g., 95th) or the 8‑hour rolling peak and adding losses + hydraulic constraints.

## Files of interest

- `results/lab1/*` – Heat + ECS profiles and SRE distribution.
- `results/lab2/*` – Electricity load and PV self-consumption outputs.
- `results/lab3/*` – Network edges, optimization summaries, and load curves.

If you need additional views or KPIs, update `scripts/generate_outputs.py` and re-run it.
