from convert_gdf_to_graph import gdf_streets_to_graph, graph_to_gdfs, graph_to_dfs

from pathlib import Path

import geopandas as gpd
import networkx as nx
import pickle
from shapely.geometry import Point
from shapely.geometry import LineString
import matplotlib.pyplot as plt

import geopy.distance
import osmnx as ox
from shapely import ops

import warnings
import math
from shapely import wkt
warnings.filterwarnings("ignore")

ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results" / "lab3"

# =============================================================================
# DATA READING AND PRE-TREATMENT
# =============================================================================

def compute_df_edges_df_nodes(buildings_file_path, resources_file_path, streets_file_path):
    
    init_crs = 2056
    
    res_id_head_build = 'id_unique'

    # Buildings, sources and network files reading
    buildings = gpd.read_file(buildings_file_path,crs = init_crs)
    
    # Remove buildings with no power
    
    buildings = buildings[buildings['maxpowerqhw']!=0].reset_index(drop=True)
    resources = gpd.read_file(resources_file_path,crs = init_crs)
    streets = gpd.read_file(streets_file_path,crs = init_crs)
    
    # CRS re-projection
    if init_crs != 2056:
        buildings = buildings.to_crs(2056)
        resources = resources.to_crs(2056)
        streets = streets.to_crs(2056)
    
    # Round geometries precision to 2 decimals (1cm in CRS 2056) to avoid numerical issues
    for elem in buildings.index:
        buildings.at[elem,'geometry'] = wkt.loads(wkt.dumps(buildings.at[elem,'geometry'], rounding_precision=1))
    
    for elem in streets.index:
        streets.at[elem,'geometry'] = wkt.loads(wkt.dumps(streets.at[elem,'geometry'], rounding_precision=1))
    
    for elem in resources.index:
        resources.at[elem,'geometry'] = wkt.loads(wkt.dumps(resources.at[elem,'geometry'], rounding_precision=1))
    
    buildings['centroid'] = buildings.centroid
    
    
    
    for i in range(len(buildings.index)):
        buildings[res_id_head_build][i] = 'Bat_' + str(buildings[res_id_head_build][i])
    
    # =============================================================================
    # CONVERSION TO GRAPH AND GRAPH MANIPULATIONS
    # =============================================================================
    
    # Convert the network GeoDataFrame to a graph
    graph_streets = gdf_streets_to_graph(streets)
    
    # Initialize graph
    G = graph_initialization(graph_streets,buildings, resources)
    
    # Connect buildings and resources to the street network
    G = connect_buildings_resources(G)
    
    # Compute network weight for each segment
    G = set_graph_weight(G,init_crs)
    
    # Plot of the graph
    plot_graph(G,100)
    
    
    # Convert resulting graph to gdf
    gdf_nodes,gdf_edges = graph_to_gdfs(G,init_crs)
    
    # Convert the graph to a DataFrame
    df_edges,df_nodes = graph_to_dfs(G)
    
    
    return df_edges, df_nodes, buildings, resources, streets, gdf_nodes, gdf_edges


def data_import(zone_file_path,buildings_file_path,resources_file_path,init_crs):
    '''
    Import data and format it for the next steps.

    Parameters
    ----------
    zone_file_path : str
        Path towards the .geojson file containing the zone from which one wants
        to extract the streets network.
    buildings_file_path : str
        Path towards the .geojson file containing the buildings that one wants to integrate
        in the DHN design process.
    resources_file_path : str
        Path towards the .geojson file containing the resources that one wants to integrate
        in the DHN design process.
    init_crs : int
        epsg code of the coordinate reference system, ex. for WGS 1984 : 4326, for LV95 : 2056

    Returns
    -------
    graph_street : nx.Graph()
        Graph containing the streets network
    buildings : GeoDataFrame
        GeoDataFrame containing the buildings that one wants to integrate
        in the DHN design process.
    resources : GeoDataFrame
        GeoDataFrame containing the resources that one wants to integrate
        in the DHN design process.

    '''
    
    print('INFO : Importing data...')

    # =============================================================================
    #     Zone importation
    # =============================================================================
    zone = gpd.read_file(zone_file_path)
    polygon = zone.geometry.iloc[0]  # Assuming you want to use the first geometry
    
    # Creation of an undirected graph with the streets imported from OSM, based on the polygon
    # Specify the streets type you want to include with network_type
    graph_street = ox.graph_from_polygon(polygon, network_type='all').to_undirected()  
        
    # =============================================================================
    #     Buildings importation
    # =============================================================================
    # Read file    
    buildings = gpd.read_file(buildings_file_path)
    
    # Project to WGS84
    buildings = buildings.to_crs(4326) # WGS 84
    
    # Keep only buildings inside the area of interest
    buildings = buildings[buildings.geometry.within(polygon)==True]
    
    # Set new ID for the buildings
    buildings['ID_python'] = range(0,buildings.shape[0])
    buildings.set_index('ID_python', inplace= True)
    buildings = buildings.rename_axis("id_unique")
    buildings.reset_index(inplace = True)
    
    # Get the centroid of each building: # GeoDataFrame
    buildings['centroid'] = buildings.centroid
    
    for i in range(len(buildings.index)):
        buildings['id_unique'][i] = 'Bat_' + str(float(buildings['id_unique'][i]))
      
    # =============================================================================
    #     Resources importation
    # =============================================================================
    # Read file
    resources = gpd.read_file(resources_file_path)
    # Set ID
    resources['name'] = resources['Nom']
    # Keep only desired columns
    resources = resources[['geometry','name']] #GeoDataFrame
    
    buildings.to_excel('../results/buildings.xlsx')
    
    return graph_street, buildings, resources


#%%

def graph_initialization(graph_street, buildings, resources):
    '''
    Connect resources and buildings to the streets network graph given in input.

    Parameters
    ----------
    graph_street : nx.Graph()
        Graph containing the streets network
    buildings : GeoDataFrame
        GeoDataFrame containing the buildings that one wants to integrate
        in the DHN design process.
    resources : GeoDataFrame
        GeoDataFrame containing the resources that one wants to integrate
        in the DHN design process.

    Returns
    -------
    G : nx.Graph()
        Graph containing the streets network, buildings and resources

    '''
    
    print('INFO : Creating graph...')

    # Create an empty graph
    G = nx.Graph()
    
    # Add nodes to the graph for each building 
    for i, building in buildings.iterrows():
        G.add_node(building['id_unique'], geometry=building.geometry.centroid, node_type='building')
           
    # Add a resource node to the graph
    for i, resource in resources.iterrows():
        G.add_node(resource['name'], geometry=resource.geometry.centroid, node_type='resource')
        
    
    # Add the edges and related nodes of Graph_street to the G
    # Iterate over nodes in graph_street
    for node, data in graph_street.nodes(data=True):
        x = data['x']
        y = data['y']
        
        G.add_node(node, geometry = Point(x, y), node_type = 'intsect')
        G.nodes[node].update(data)
        
    for u, v, data in graph_street.edges(data=True): 
        
        G.add_edge(u, v, edge_type = 'street')    
        G[u][v].update(data)
        
    return G
    
 
    
# --------------- Nearest Point of buildingss and resources to the Street ------------- #

def connect_buildings_resources(G):
    '''
    Connect buildings and resources to the closest point of the streets network

    Parameters
    ----------
    G : nx.Graph()
        Graph containing the streets network, buildings and resources

    Returns
    -------
    G : nx.Graph()
        Graph containing the streets network and buildngs / ressources connected to it

    '''
    
    print('INFO : Connecting buildings and resources to the graph...')

    building_nodes = {node: data for node, data in G.nodes(data=True) if data['node_type'] == 'building'}
    street_nodes = {node: data for node, data in G.nodes(data=True) if data['node_type'] == 'intsect'}
    
    
    for building_node, building_data in building_nodes.items():
        building_geometry = building_data['geometry']
        building_point = building_geometry.centroid
    
        nearest_street_point = None
        min_distance = float('inf')
        near_u = None
        near_v = None
        
        for u, v, data in G.edges(data=True):
            if data['edge_type'] == 'street' or data['edge_type'] =='connection-street':
                street_geometry = LineString([G.nodes[u]['geometry'], G.nodes[v]['geometry']])
                distance = street_geometry.distance(building_point)
                
                if distance < min_distance:
                    min_distance = distance
                    #nearest_street_point = street_geometry.interpolate(street_geometry.project(building_point))
                    nearest_street_point = ops.nearest_points(building_point,street_geometry)
                    nearest_street_point = nearest_street_point[1]
                    nearest_street_point = Point(nearest_street_point.x, nearest_street_point.y)
                    near_u = u
                    near_v = v
        
        # Create a line between the building point and the nearest street point
        line = LineString([building_point, nearest_street_point])
    
        # Find the intersection point of the line and the nearest street edge
        # intersection_point = nearest_street_point.intersection(line)
        intersection_point = nearest_street_point
        
        
        # Add the connection point as a new node in the graph
        connection_point_name = 'connection_' + building_node
        G.add_node(connection_point_name, geometry=intersection_point, node_type='connection_building_street')
        G.add_edge(building_node, connection_point_name, edge_type='building-street', geometry = line,data = True)
        G.add_edge(near_u, connection_point_name, edge_type='connection-street', geometry = LineString([G.nodes[near_u]['geometry'],G.nodes[connection_point_name]['geometry']]))
        G.add_edge(connection_point_name, near_v, edge_type='connection-street', geometry = LineString([G.nodes[connection_point_name]['geometry'],G.nodes[near_v]['geometry']]))

        
        G.remove_edge(near_u, near_v)
    
           
    # Nearest Point of resource to the Street
    
    resource_nodes = {node: data for node, data in G.nodes(data=True) if data.get('node_type') == 'resource'}
    
    for resource_node, resource_data in resource_nodes.items():
        resource_geometry = resource_data['geometry']
        resource_point = resource_geometry.centroid
        
        nearest_street_point = None
        min_distance = float('inf')
        near_u = None
        near_v = None
        # Iterate over street edges
        for u, v, data in G.edges(data=True):
            if data['edge_type'] == 'street' or data['edge_type'] =='connection-street':
                street_geometry = LineString([G.nodes[u]['geometry'], G.nodes[v]['geometry']])
                distance = street_geometry.distance(resource_point)
                
                # Check if the distance is the new minimum
                if distance < min_distance:
                    min_distance = distance
                    
                    # Find the nearest point on the street edge
                    #nearest_street_point = street_geometry.interpolate(street_geometry.project(resource_point))
                    nearest_street_point = ops.nearest_points(resource_point,street_geometry)
                    nearest_street_point = nearest_street_point[1]
                    # Convert it to tuple
                    nearest_street_point = (nearest_street_point.x , nearest_street_point.y)
                    near_u = u
                    near_v = v
                                  
        # Create a line between the building point and the nearest street point
        line = LineString([resource_point, nearest_street_point])
        
        # Find the intersection point of the line and the nearest street edge
        # intersection_point = nearest_street_point.intersection(line)
        intersection_point = nearest_street_point
                       
        
        street_geometry = LineString([G.nodes[near_u]['geometry'], G.nodes[near_v]['geometry']])
        
        # Add the connection point as a new node in the graph
        connection_point_name = 'connection_' + str(resource_node)
        G.add_node(connection_point_name, geometry=intersection_point, node_type='connection_resource_street')
        G.add_edge(resource_node, connection_point_name, edge_type='resource-street',geometry = line, data = True)          
        G.add_edge(near_u, connection_point_name, edge_type='connection-street',geometry = LineString([G.nodes[near_u]['geometry'],G.nodes[connection_point_name]['geometry']]))
        G.add_edge(connection_point_name, near_v, edge_type='connection-street',geometry = LineString([G.nodes[connection_point_name]['geometry'],G.nodes[near_v]['geometry']]))
        G.remove_edge(near_u, near_v)
        
    return G


def remove_no_power(G,buildings,res_power_head,res_id_head_build):
    for building in buildings.index:
        if buildings.at[building, res_power_head] == 0:
            G.remove_node(buildings.at[building,res_id_head_build])
            # G.remove_edge(buildings.at[building,res_id_head_build],'connexion_{}'.format(buildings.at[building,res_id_head_build]))
            
    return G
   
def plot_graph(G,_dpi):
    '''
    Plot the graph given as input.

    Parameters
    ----------
    G : nx.Graph()
        Graph containing the streets network, buildings and resources

    Returns
    -------
    None.

    '''
    
    print('INFO : Plotting the graph...')

    # Get node positions from their geometry
    node_positions = {}
    node_sizes = []
    node_colors = []
    
    
    for node in G.nodes:
        geometry = G.nodes[node]['geometry']
        node_type = G.nodes[node]['node_type']
        
        if isinstance(geometry, tuple):
            node_positions[node] = geometry
        elif isinstance(geometry, Point):
            node_positions[node] = (geometry.x,geometry.y)
        else:
            centroid = geometry.centroid
            node_positions[node] = (centroid.x, centroid.y)
       
        # Plot buildings in red
        if node_type == 'building':
            node_sizes.append(300)
            node_colors.append('red')
            
        # Plot resources in green
        elif node_type == 'resource':
            node_sizes.append(300)
            node_colors.append('green')
            
        # Plot intersections in gray
        elif node_type == 'intsect':
            node_sizes.append(30)
            node_colors.append('gray')
            
        # Plot building connections in blue
        elif node_type == 'connection_building_street':
            node_sizes.append(30)
            node_colors.append('blue')
            
        # Plot resources connections in brown
        elif node_type == 'connection_resource_street':
            node_sizes.append(30)
            node_colors.append('brown')
    
    # Visualize the graph
    plt.figure(figsize=(60, 40))
    nx.draw_networkx_nodes(G, node_positions, node_color=node_colors, node_size=node_sizes, alpha=0.8)
    nx.draw_networkx_edges(G, node_positions, width=1.0, alpha=0.5, edge_color='black', style='solid')
    
    # Set axis properties
    plt.xticks([])
    plt.yticks([])
    plt.axis('on')
    
    plt.title('DHN Graph',fontsize=30)
    # plt.legend()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(RESULTS_DIR / "network_graph.png", dpi=_dpi)
    plt.close()
    
    
    return

def set_graph_weight(G,init_crs):
    '''
    Set the length and weight of the edges of the graph given as input

    Parameters
    ----------
    G : nx.Graph()
        Graph containing the streets network, buildings and resources

    Returns
    -------
    G : nx.Graph()
        Graph containing the streets network (with weight and length), buildings and resources

    '''
    
    print('INFO : Setting graph weights...')
    
    geometry = {}
    node_positions = {}
    
    # Add edge weights to the graph
    for u, v, data in G.edges(data=True):
        
        node_u = G.nodes[u]
        node_v = G.nodes[v]
        geometry['u'] = node_u['geometry']
        geometry['v'] = node_v['geometry']
        
        for key, value in geometry.items(): 
            if isinstance(value, tuple):
              node_positions[key] = value       
            
            elif isinstance(value, Point):
              node_positions[key] = (value.x, value.y)
            else:
              centroid = value.centroid
              node_positions[key] = (centroid.x, centroid.y)
              
        if init_crs==4326:
        
            edge_length = geopy.distance.geodesic(node_positions['u'], node_positions['v']).meters
            
        else:
            x1 = node_positions['u'][0]
            x2 = node_positions['v'][0]
            y1 = node_positions['u'][1]
            y2 = node_positions['v'][1]
            
            edge_length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
          
        data['length'] = edge_length  # Assigning the real length as the weight
        data['weight'] = data['length']
        
    if nx.is_connected(G) == True:
        print('INFO : The network graph is connected')
    else:
        print('WARNING : The graph of the network is NOT connected')
            
    return G
    

def save_graph(G,filepath):
    '''
    Save the graph G as a .pickle file.

    Parameters
    ----------
    G : nx.Graph()
        Graph containing the streets network (with weight and length), buildings and resources
    filepath : str
        Path where the graph will be saved.

    Returns
    -------
    None.

    '''
    print('INFO : Saving graph...')
    with open(filepath,'wb') as f: 
        pickle.dump(G, f)
    return
    

def graph_creation(zone_file_path,buildings_file_path,resources_file_path,graph_path,init_crs):
    
    graph_street, buildings, resources = data_import(zone_file_path,buildings_file_path,resources_file_path, init_crs)
    
    G = graph_initialization(graph_street, buildings, resources)

    G = connect_buildings_resources(G)
    
    G = set_graph_weight(G,init_crs)
    
    save_graph(G,graph_path)

    plot_graph(G)

    return G, buildings