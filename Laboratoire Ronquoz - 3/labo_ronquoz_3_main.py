from helpers import compute_df_edges_df_nodes

import os
import geopandas as gpd

from shapely.geometry import Point, LineString

# MODIFY YOUR FILE PATHS HERE
buildings_file_path = '../results/gis_data.geojson'
resources_file_path = '../data/resources_ronquoz.geojson'
streets_file_path = '../data/road_network_ronquoz.geojson'

# Create results directory
if not os.path.exists("../results"):
    os.makedirs("../results")


# Maximum pressure drop accepted in the pipes in [Pa/m]
dP_max = 100         
       
# Delta T assumed between supply and return of the DHN                 
dT = 30

df_edges, df_nodes, buildings, resources, streets = compute_df_edges_df_nodes(buildings_file_path, resources_file_path, streets_file_path)