Ronquoz 21 - Energy Planning & Sizing Results (Horizon 2060)
===========================================================

This directory contains the results of all three laboratories for the Ronquoz district.

Directory Structure:
-------------------
- results/lab1/ : Heating and Domestic Hot Water (DHW) demand calculations, profiles, and SRE grouping.
- results/lab2/ : Electrical consumption, solar PV generation, self-consumption/autonomy calculations, and storage sizing.
- results/lab3/ : Sized thermal network edges, node mass flows, optimized pipe diameters, and sizing summaries.
- results/maps/ : High-resolution Geopandas maps showing choropleths of energy demands, powers, and network diameters.
- results/plots/: Interactive Plotly.js-based HTML charts of hourly and weekly profiles.
- results/dashboard.html : A complete, self-contained, interactive GIS and Energy dashboard combining all data layers!

Dashboard:
----------
To view the results in an interactive web browser, open the file:
results/dashboard.html

It contains:
1. An interactive GIS Leaflet map with 9 toggleable building layers (affectation, phase, annual heat, annual elec, specific ratios, autonomy, max power, etc.) and the sized piping network (styled by diameter).
2. Grouped Plotly charts showing energy distribution by affectation and building status.
3. Interactive time-series charts showing typical week electricity schedules (Admin vs. Industry) and annual load curves.
4. Comprehensive key indicators and written answers for all three laboratories.

Report:
-------
For a complete, academically styled lab report with formulas, methodology, results, and detailed answers to all specific questions, refer to the file:
report_ronquoz.md (located in the parent directory)
