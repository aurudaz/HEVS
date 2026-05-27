# Ronquoz district energy report

Generated: 2026-05-27 11:03 UTC

## Executive summary

- **Buildings analysed:** 196
- **Total SRE:** 744 731 m²
- **Annual heat + ECS:** 26 147.8 MWh/an
- **Peak heat demand (hourly):** 9 259 kW
- **Diversified peak (foisonnement):** 7 222 kW
- **Annual district electricity load:** 23 371.9 MWh/an
- **Annual PV production:** 19 318.9 MWh/an
- **Network length:** 14.77 km
- **Network CAPEX:** 16 736 196 CHF

## Labo 1 – Thermal demand characterization

The heating and ECS demand is derived from SIA 380/1 tables, the building SRE and envelope factors. An hourly profile is built with the MeteoSuisse temperature series and a simplified ECS schedule (08:00–20:00). Thermal inertia and foisonnement factors are applied to approximate diversity between buildings.

**Key outputs**

- Annual heating: 17 905.3 MWh/an
- Annual ECS: 8 242.5 MWh/an
- Annual total heat: 26 147.8 MWh/an
- Peak heat demand (hourly): 9 259 kW
- Peak demand with foisonnement: 7 222 kW

Maps and graphs: SRE by affectation, district heat profile.

## Labo 2 – Electricity and PV self-consumption

Electricity loads are read from the consumption workbook. PV production is modelled with PVGIS profiles for east/west orientations and installed surface. Autoconsumption and autonomy are computed on an hourly basis.

**Key outputs**

- Annual electricity load: 23 371.9 MWh/an
- Annual PV production: 19 318.9 MWh/an
- Autoconsumption: 76.5%
- Autonomy: 63.3%
- Storage capacity for 100% autoconsumption: 4 052.6 MWh
- Peak load: 5 381 kW
- Peak PV: 5 585 kW

Maps and graphs: electricity/heat energy maps, typical weekly profiles.

## Labo 3 – District heating network optimization (focus)

The optimization uses the road network as the backbone and connects buildings/resources to the nearest street edge. Each pipe segment is assigned a diameter from a discrete catalogue and sized to carry the required mass flow at ΔT = 30°C. The objective is to minimize a linearized CAPEX function based on diameter and length. The heat demand is taken from the Labo 1 peak power (after foisonnement).

**Key outputs**

- Network length: 14.77 km
- CAPEX (pipes only): 16 736 196 CHF
- Annual heat served: 26 147.8 MWh/an
- Energy density: 1 770.3 MWh/km/an
- Peak heat demand (hourly): 9 259 kW
- Smoothed peak (8h rolling): 8 752 kW

**Supply dispatch (optimized)**

| Resource | Power (kW) | Mass flow (kg/h) |
| --- | --- | --- |
| rhone | 4 161.1 | 119 457 |
| nappe | 2 000.0 | 57 416 |
| nappe_ste_marguerite | 713.6 | 20 485 |
| cad | 347.6 | 9 980 |

### Limitations and why the sizing can be too large

- **Peak-based sizing:** the network is sized to the hourly peak demand. Short peaks drive large diameters even when the energy-weighted demand is lower. The 8‑hour smoothed peak is about 8 752 kW, which is below the instantaneous peak of 9 259 kW.
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
| Buildings | 196 |
| Total SRE | 744 731 m² |
| Annual heat + ECS | 26 147.8 MWh/an |
| Peak heat demand | 9 259 kW |
| Diversified peak | 7 222 kW |
| Annual electricity load | 23 371.9 MWh/an |
| Annual PV production | 19 318.9 MWh/an |
| Network length | 14.77 km |
| Pipe CAPEX | 16 736 196 CHF |
