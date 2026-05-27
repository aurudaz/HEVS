#!/usr/bin/env python3
"""
Numerical Simulation Course - Lab "Ronquoz"
Visualizations Generator using Plotly and Geopandas.

This script reads the pre-computed simulation results from the Ronquoz district
and generates a set of professional-grade interactive Plotly graphs and Geopandas maps.

Requirements:
    pip install geopandas matplotlib plotly pandas numpy folium jinja2

Usage:
    python3 generate_visualizations.py
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

def generate_geopandas_maps():
    """Generates high-resolution choropleth maps of the district using Geopandas and Matplotlib."""
    try:
        import geopandas as gpd
        import matplotlib.pyplot as plt
    except ImportError:
        print("[WARNING] geopandas or matplotlib is not installed. Skipping Geopandas maps generation.")
        return

    print("Generating Geopandas maps...")
    ensure_dir(os.path.join(RESULTS_DIR, "maps"))

    # Load buildings
    if not os.path.exists(BUILDINGS_GEOJSON):
        print(f"[ERROR] Buildings GeoJSON not found at {BUILDINGS_GEOJSON}")
        return
    
    gdf = gpd.read_file(BUILDINGS_GEOJSON)

    # Pre-calculate specific metrics
    gdf['heat_sre_ratio'] = gdf.apply(
        lambda r: r['heat_ecs_annual_kwh'] / r['sre'] if r['sre'] > 0 else 0.0, axis=1
    )
    gdf['elec_sre_ratio'] = gdf.apply(
        lambda r: r['elec_annual_kwh'] / r['sre'] if r['sre'] > 0 else 0.0, axis=1
    )

    maps_to_generate = [
        {
            "column": "heat_ecs_annual_kwh",
            "title": "Annual Heat Demand (Heating + DHW) [kWh]",
            "cmap": "OrRd",
            "filename": "map_heat_energy.png"
        },
        {
            "column": "elec_annual_kwh",
            "title": "Annual Electricity Consumption [kWh]",
            "cmap": "Blues",
            "filename": "map_electric_energy.png"
        },
        {
            "column": "maxpowerqhw",
            "title": "Yearly Max Heating Power (Foisonné) [kW]",
            "cmap": "YlOrRd",
            "filename": "map_max_power.png"
        },
        {
            "column": "heat_sre_ratio",
            "title": "Specific Heating Demand [kWh/m² SRE]",
            "cmap": "magma",
            "filename": "map_heat_sre.png"
        },
        {
            "column": "elec_sre_ratio",
            "title": "Specific Electricity Demand [kWh/m² SRE]",
            "cmap": "viridis",
            "filename": "map_electric_sre.png"
        },
        {
            "column": "pv_annual_kwh",
            "title": "Annual Photovoltaic Generation Potential [kWh]",
            "cmap": "YlOrYg",
            "filename": "map_pv_generation.png"
        },
        {
            "column": "autonomy",
            "title": "Electrical Autonomy Rate [0 - 1.0]",
            "cmap": "RdYlGn",
            "filename": "map_elec_autonomy.png"
        }
    ]

    for m in maps_to_generate:
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        # Plot styled background or boundary
        gdf.plot(color='#EEEEEE', ax=ax)
        # Plot choropleth
        gdf[gdf[m['column']] > 0].plot(
            column=m['column'],
            cmap=m['cmap'],
            legend=True,
            ax=ax,
            edgecolor='black',
            linewidth=0.4,
            legend_kwds={'shrink': 0.7, 'label': m['title']}
        )
        ax.set_title(m['title'], fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        fig.savefig(os.path.join(RESULTS_DIR, "maps", m['filename']), dpi=300, bbox_inches='tight')
        plt.close(fig)
        print(f"  - Saved results/maps/{m['filename']}")

    # Generate Thermal Network Pipe Map
    if os.path.exists(NETWORK_GEOJSON):
        gdf_edges = gpd.read_file(NETWORK_GEOJSON)
        fig, ax = plt.subplots(1, 1, figsize=(14, 10))
        
        # Plot buildings for context
        gdf.plot(color='#E5E7E9', ax=ax, edgecolor='#BDC3C7', linewidth=0.3)
        
        # Plot pipes colored by nominal diameter and width proportional to diameter
        widths = gdf_edges['diameter_mm'].fillna(25).astype(float) * 0.02 + 1.0
        gdf_edges.plot(
            column='diameter_mm',
            cmap='coolwarm',
            legend=True,
            ax=ax,
            linewidth=widths,
            legend_kwds={'shrink': 0.7, 'label': 'Nominal Pipe Diameter [mm]'}
        )
        ax.set_title('Sized District Heating Network (DHN) Pipe Diameters', fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        fig.savefig(os.path.join(RESULTS_DIR, "maps", "map_network_diameters.png"), dpi=300, bbox_inches='tight')
        plt.close(fig)
        print("  - Saved results/maps/map_network_diameters.png")

        # Interactive Folium explore HTML maps
        try:
            gdf_edges.explore(column='diameter_mm', cmap='coolwarm').save(os.path.join(RESULTS_DIR, "maps", "map_network_interactive.html"))
            gdf.explore(column='heat_ecs_annual_kwh', cmap='OrRd').save(os.path.join(RESULTS_DIR, "maps", "map_heat_interactive.html"))
            print("  - Generated interactive HTML Folium maps in results/maps/")
        except Exception as e:
            print(f"  - Skip interactive Folium map generation: {e}")

def generate_plotly_graphs():
    """Generates interactive Plotly visualizations for energy consumption, schedules, and load curves."""
    try:
        import plotly.graph_objects as go
        import plotly.express as px
    except ImportError:
        print("[WARNING] plotly is not installed. Skipping Plotly graphs generation.")
        return

    print("Generating Plotly graphs...")
    ensure_dir(os.path.join(RESULTS_DIR, "plots"))

    # Load buildings data for grouping
    if not os.path.exists(BUILDINGS_GEOJSON):
        print(f"[ERROR] Buildings GeoJSON not found at {BUILDINGS_GEOJSON}")
        return
    with open(BUILDINGS_GEOJSON) as f:
        data = json.load(f)
    properties = [feature['properties'] for feature in data['features']]
    df_build = pd.DataFrame(properties)

    # Graph 1: Energy Heat & Elec per Type (Affectation)
    df_affect = df_build.groupby('affect')[['heat_ecs_annual_kwh', 'elec_annual_kwh', 'pv_annual_kwh']].sum().reset_index()
    fig1 = go.Figure(data=[
        go.Bar(name='Heat Energy (Heating + DHW)', x=df_affect['affect'], y=df_affect['heat_ecs_annual_kwh'], marker_color='#E74C3C'),
        go.Bar(name='Electricity Demand (Excl. Heat)', x=df_affect['affect'], y=df_affect['elec_annual_kwh'], marker_color='#3498DB'),
        go.Bar(name='PV Solar Generation', x=df_affect['affect'], y=df_affect['pv_annual_kwh'], marker_color='#F1C40F')
    ])
    fig1.update_layout(
        title='Annual Heat vs. Electricity vs. PV Generation by Building Use (Affectation)',
        xaxis_title='Use / Affectation',
        yaxis_title='Annual Energy [kWh]',
        barmode='group',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig1.write_html(os.path.join(RESULTS_DIR, "plots", "graph_energy_by_type.html"))
    print("  - Saved results/plots/graph_energy_by_type.html")

    # Graph 2: Energy Heat & Elec per New/Old (Etat)
    df_etat = df_build.groupby('etat')[['heat_ecs_annual_kwh', 'elec_annual_kwh', 'pv_annual_kwh']].sum().reset_index()
    fig2 = go.Figure(data=[
        go.Bar(name='Heat Energy (Heating + DHW)', x=df_etat['etat'], y=df_etat['heat_ecs_annual_kwh'], marker_color='#E74C3C'),
        go.Bar(name='Electricity Demand', x=df_etat['etat'], y=df_etat['elec_annual_kwh'], marker_color='#3498DB'),
        go.Bar(name='PV Solar Generation', x=df_etat['etat'], y=df_etat['pv_annual_kwh'], marker_color='#F1C40F')
    ])
    fig2.update_layout(
        title='Annual Heat vs. Electricity vs. PV Generation by Building Status (Etat)',
        xaxis_title='Building Status (Etat)',
        yaxis_title='Annual Energy [kWh]',
        barmode='group',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig2.write_html(os.path.join(RESULTS_DIR, "plots", "graph_energy_by_etat.html"))
    print("  - Saved results/plots/graph_energy_by_etat.html")

    # Graph 3: SRE Distribution Pie Chart
    df_sre = df_build.groupby('affect')['sre'].sum().reset_index()
    fig3 = px.pie(
        df_sre, 
        values='sre', 
        names='affect', 
        title='Energy Reference Area (SRE) Distribution by Use',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig3.update_traces(textposition='inside', textinfo='percent+label')
    fig3.update_layout(template='plotly_white')
    fig3.write_html(os.path.join(RESULTS_DIR, "plots", "graph_sre_by_affectation.html"))
    print("  - Saved results/plots/graph_sre_by_affectation.html")

    # Graph 4: Typical Week Electrical Profiles (Summer, Winter, Inter-seasons)
    if os.path.exists(ELEC_CONSUMPTION_CSV):
        df_elec = pd.read_csv(ELEC_CONSUMPTION_CSV)
        # Select Admin (H4-12) and Industry (H3-8)
        admin_id, ind_id = 'H4-12', 'H3-8'
        
        if admin_id in df_elec.columns and ind_id in df_elec.columns:
            # We want weeks starting Jan 1st (winter, hours 0-167), April 1st (mid, hours 2160-2327), July 1st (summer, hours 4344-4511)
            hours = np.arange(168)
            
            fig4 = go.Figure()
            # Winter
            fig4.add_trace(go.Scatter(x=hours, y=df_elec.loc[0:167, admin_id], name='Admin - Winter', line=dict(color='#2C3E50', width=2)))
            fig4.add_trace(go.Scatter(x=hours, y=df_elec.loc[0:167, ind_id], name='Industry - Winter', line=dict(color='#E67E22', width=2)))
            
            # Midseason
            fig4.add_trace(go.Scatter(x=hours, y=df_elec.loc[2160:2327, admin_id], name='Admin - Midseason', line=dict(color='#2980B9', width=2, dash='dash')))
            fig4.add_trace(go.Scatter(x=hours, y=df_elec.loc[2160:2327, ind_id], name='Industry - Midseason', line=dict(color='#D35400', width=2, dash='dash')))
            
            # Summer
            fig4.add_trace(go.Scatter(x=hours, y=df_elec.loc[4344:4511, admin_id], name='Admin - Summer', line=dict(color='#16A085', width=2, dash='dot')))
            fig4.add_trace(go.Scatter(x=hours, y=df_elec.loc[4344:4511, ind_id], name='Industry - Summer', line=dict(color='#C0392B', width=2, dash='dot')))
            
            fig4.update_layout(
                title='Hourly Electrical Consumption Profiles over Typical Weeks',
                xaxis_title='Hour of the Week',
                yaxis_title='Electrical Power [kW]',
                template='plotly_white',
                xaxis=dict(tickmode='array', tickvals=list(range(0, 169, 24)), ticktext=['Sun 0:00', 'Mon 0:00', 'Tue 0:00', 'Wed 0:00', 'Thu 0:00', 'Fri 0:00', 'Sat 0:00', 'Sun 24:00']),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig4.write_html(os.path.join(RESULTS_DIR, "plots", "graph_typical_weeks.html"))
            print("  - Saved results/plots/graph_typical_weeks.html")

    # Graph 5: District Electricity Load and PV Generation Profile
    if os.path.exists(DISTRICT_ELEC_CSV):
        df_dist_elec = pd.read_csv(DISTRICT_ELEC_CSV)
        # Resample to daily average for readability or plot hourly with range slider
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(x=df_dist_elec['time'], y=df_dist_elec['load_kw'], name='Electricity Load', line=dict(color='#2980B9', width=1.5)))
        fig5.add_trace(go.Scatter(x=df_dist_elec['time'], y=df_dist_elec['pv_kw'], name='PV Generation', line=dict(color='rgba(241, 196, 15, 0.4)', width=1.5)))
        fig5.add_trace(go.Scatter(x=df_dist_elec['time'], y=df_dist_elec['self_consumed_kw'], name='Self-Consumed PV', line=dict(color='#27AE60', width=1.5)))
        
        fig5.update_layout(
            title='District Hourly Electrical Load & Solar PV Generation Profile',
            xaxis_title='Date / Time',
            yaxis_title='Power [kW]',
            template='plotly_white',
            xaxis=dict(rangeslider=dict(visible=True)),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig5.write_html(os.path.join(RESULTS_DIR, "plots", "graph_district_electric_profile.html"))
        print("  - Saved results/plots/graph_district_electric_profile.html")

    # Graph 6: District Thermal Sizing Load Curve (raw and smoothed)
    if os.path.exists(DHN_LOAD_CSV):
        df_dhn = pd.read_csv(DHN_LOAD_CSV)
        fig6 = go.Figure()
        fig6.add_trace(go.Scatter(x=df_dhn['time'], y=df_dhn['total_kw'], name='Raw Sizing Power', line=dict(color='#C0392B', width=1)))
        fig6.add_trace(go.Scatter(x=df_dhn['time'], y=df_dhn['smoothed_kw'], name='Smoothed Power (8h Moving Avg)', line=dict(color='#2C3E50', width=2.5)))
        
        fig6.update_layout(
            title='District Heating Network Sizing Load Curve',
            xaxis_title='Date / Time',
            yaxis_title='Power [kW]',
            template='plotly_white',
            xaxis=dict(rangeslider=dict(visible=True)),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig6.write_html(os.path.join(RESULTS_DIR, "plots", "graph_dhn_load_curve.html"))
        print("  - Saved results/plots/graph_dhn_load_curve.html")

if __name__ == "__main__":
    generate_plotly_graphs()
    generate_geopandas_maps()
    print("Visualization generation run complete!")
