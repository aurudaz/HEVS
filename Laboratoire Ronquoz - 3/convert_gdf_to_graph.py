# -*- coding: utf-8 -*-
"""
Created on Tue Oct 24 08:16:25 2023

@author: tristan.rey1
"""
import geopandas as gpd
from shapely.geometry import Point, LineString
import pandas as pd
import networkx as nx



# Create segments from a linestring
def segments(curve):
    return list(map(LineString, zip(curve.coords[:-1], curve.coords[1:])))

# Function to transform a GDF of lines into a GDF of segments
def gdf_linestring_to_segments(streets):
    
    streets_new = gpd.GeoDataFrame()
    
    for loop in streets.index:
        gdf = gpd.GeoDataFrame(segments(streets.at[loop,'geometry']),columns = ['geometry'])
        streets_new = pd.concat([streets_new,gdf])
        
    streets_new = streets_new.reset_index(drop=True)
    
    return streets_new

def gdf_streets_to_graph(streets):

    G = nx.Graph()
    
    # Remove empty geometries
    try:
        streets = streets[~streets.is_empty]  
    except:
        print('INFO : No empty geometry')
    
    # Explode GeoDataFrame to remove MULTI geometries
    streets = streets.explode()
    
    # Transform lines to segments
    streets = gdf_linestring_to_segments(streets)
    
    # Create a graph with the streets
    for street in streets.index:
        G.add_edge((streets.at[street,'geometry'].coords[0]),(streets.at[street,'geometry'].coords[1]),geometry = streets.at[street,'geometry'])
        
    for key in G.nodes.keys():
        G.nodes[key]['x'] = key[0]
        G.nodes[key]['y'] = key[1]
        G.nodes[key]['node_type'] = 'intsect'
        
    return G


def graph_to_gdfs(G,crs):

    gdf_nodes = gpd.GeoDataFrame(index = G.nodes.keys(),  columns = ['geometry','node_type'],crs = crs)
    gdf_edges = gpd.GeoDataFrame(index = G.edges.keys(),  columns = ['edge_type','length','geometry','A','B'],crs = crs)
    
    for key in G.nodes.keys():
        gdf_nodes.at[key,'geometry'] = Point(G.nodes[key]['geometry'])
        gdf_nodes.at[key,'node_type'] = G.nodes[key]['node_type']
        
    for key in G.edges.keys():
        gdf_edges.at[key,'edge_type'] = G.edges[key]['edge_type']
        gdf_edges.at[key,'length'] = G.edges[key]['length']
        gdf_edges.at[key,'geometry'] = G.edges[key]['geometry']
        gdf_edges.at[key,'A'] = key[0]
        gdf_edges.at[key,'B'] = key[1]
        
    ## Rename the street with Str
    for node in gdf_nodes.index:
        str_node = str(node)
        if str_node[0].isdigit():        
            node_name = 'Str_' + str_node
            gdf_nodes.rename(index={node: node_name}, inplace=True) 
            
   ## Rename the street with Str      
    for (u, v) in gdf_edges.index:
        str_u = str(u)
        str_v = str(v)
        if type(u)==tuple:
            u_name = 'Str_' + str_u
        else:
            u_name = u
        if type(v)==tuple:
            v_name = 'Str_' + str_v
        else:
            v_name = v
        # Update the DataFrame with the new edge names
        gdf_edges.rename(index={(u, v): (u_name, v_name)}, inplace=True)
        
        
    # Convert tuple index to str to be able to save it.  
    
    # gdf_edges.index = [gdf_edges.index.map('{0[0]}-{0[1]}'.format)]

    # tmp = gdf_nodes.index.tolist()
    # for loop in range(0,len(tmp)):
    #     if type(tmp[loop]) == tuple:
    #         tmp[loop] = str(tmp[loop])
            
    # gdf_nodes.index = tmp
    

    # gdf_nodes.index = gdf_nodes.index.astype(str)
    
    gdf_edges.index = tuple(gdf_edges.index)
        
        
    return gdf_nodes, gdf_edges


def graph_to_dfs(DHN):
    
    
    ### Convert the Graph to the DataFrame: maybe it will be better for energy balance !!!
    
    ## Transfer the nodes
    DHN_nodes = {node: data for node, data in DHN.nodes(data=True)}  
    node_list = [node for node in DHN.nodes] 
    geo_list = [data['geometry'] for node, data in DHN.nodes(data=True)] 
    node_type_list = [data['node_type'] for node, data in DHN.nodes(data=True)] 
    
    
    df_nodes = pd.DataFrame(index = node_list, columns = ['geometry', 'node_type'])
    df_nodes['geometry'] = geo_list
    df_nodes['node_type'] = node_type_list
    ## Rename the street with Str
    for node in df_nodes.index:
        str_node = str(node)
        if str_node[0].isdigit():        
            node_name = 'Str_' + str_node
            df_nodes.rename(index={node: node_name}, inplace=True)        
    
    
    ## Transfer the edges
    DHN_edges = {(u, v): data for u, v, data in DHN.edges(data=True)} 
    edge_list = [edge for edge in DHN.edges] 
    length_list = [data['length'] for u, v, data in DHN.edges(data=True)] 
    edge_type_list = [data['edge_type'] for u, v, data in DHN.edges(data=True)]
    
    df_edges = pd.DataFrame(index = edge_list, columns = ['edge_type', 'length'])
    df_edges['length'] = length_list
    df_edges['edge_type'] = edge_type_list
    ## Rename the street with Str      
    for (u, v) in df_edges.index:
        str_u = str(u)
        str_v = str(v)
        if str_u[0].isdigit():
            u_name = 'Str_' + str_u
        else:
            u_name = u
        if str_v[0].isdigit():
            v_name = 'Str_' + str_v
        else:
            v_name = v
        # Update the DataFrame with the new edge names
        df_edges.rename(index={(u, v): (u_name, v_name)}, inplace=True)
        
    ## Add the columns for ID of each edge
    df_edges['ID_edge'] = list(range(len(df_edges.index)))
    list_u = []
    list_v = []
    for (u, v) in df_edges.index:
        list_u.append(u)
        list_v.append(v)
    df_edges['A'] = list_u
    df_edges['B'] = list_v
    
    return df_edges, df_nodes


    
    
    
    #%%
# import matplotlib.pyplot as plt
# # Visualize the graph
# plt.figure(figsize=(60, 40))

# # tmp = dict.fromkeys((G.nodes))
# # for loop in tmp.keys():
# #     tmp[loop] = list(G.nodes)[loop]
    
# tmp = dict(G.nodes)
# for loop in tmp.keys():
#     tmp[loop] = loop

# nx.draw_networkx_nodes(G, tmp, node_color='blue', node_size=300, alpha=0.8)
# nx.draw_networkx_edges(G, tmp, width=1.0, alpha=0.5, edge_color='black', style='solid')

# # Set axis properties
# plt.xticks([])
# plt.yticks([])
# plt.axis('on')

# plt.title('DHN Network Graph')
# plt.show()
# # plt.legend()


# streets['Point_A'] = Point(0,0)
# streets['Point_B'] = Point(0,0)

# for loop_street in streets.index:
#     point_A = Point(streets.at[loop_street,'geometry'].coords[0])
#     point_B = Point(streets.at[loop_street,'geometry'].coords[1])
    
#     streets.at[loop_street,'Point_A'] = point_A
#     streets.at[loop_street,'Point_B'] = point_B
    
# all_points = gpd.GeoDataFrame(geometry = streets['Point_A'].to_list() + streets['Point_B'].to_list())

# geom_list = []

# for geom in all_points.geometry:
#     if geom not in geom_list:
#         geom_list = geom_list + [geom]
    

# def deduplicate(geo_data: np.ndarray # shape == (N, 4)
#         ) -> np.ndarray:             # deduplicated data with origin order
#     data = geo_data.reshape(-1, 2, 2)
#     dt = f'f{data.itemsize}' # f4 or f8
#     data = data.view([('x', dt), ('y', dt)]) 
#     # eliminate differences
#     ixs = np.argsort(data, -2, order=('x', 'y'))
#     data_no_df = np.take_along_axis(data, ixs, axis=-2) # sorted by 'x' then by 'y'
#     # get unique
#     unique_sorted_data, uni_ixs = np.unique(data_no_df, True, axis=0)
#     uni_ixs.sort() # inplace sort 1d-array
#     data_deduplicated = geo_data[uni_ixs] # unique, originally ordered and shaped
#     return data_deduplicated

# def solution(frame):
#     linestring = frame.geometry
#     coordinates = [list(x.coords) for x in linestring]
#     matrix = np.array(coordinates)
#     result = deduplicate(matrix)
#     final_result = [list(map(tuple, pair)) for pair in result.tolist()]
#     lines = [Point(pair) for pair in final_result]
#     return gpd.GeoDataFrame(geometry = lines)

# # test = solution(all_points)

# test2 = gpd.GeoDataFrame(geometry = all_points['geometry'].unique())
    

# streets_new[0] = streets_new[0].rename('geometry')

    
# streets_new = streets_new.rename({'0':'geometry'})

# streets = streets.explode()

# streets['ID_street'] = ['Street_{}'.format(x) for x in range(0,streets.shape[0])]
# streets['points'] = Point(0,0)

# for loop_ind in streets.index:
#     streets.at[loop_ind,'points'] = np.vstack(streets.at[loop_ind,'geometry'].coords.xy).T.tolist()
    
    
# nb_points = 0
# for loop_street in streets.index:
#     nb_points += len(streets.at[loop_street,'points']) 
    
# points = gpd.GeoDataFrame()    
    
# counter = 0
# for loop_street in range(0,streets.shape[0]):
#     for loop_point in range()
    

# len([[2593220.635106509, 1119071.3671955534], [2593282.4703557203, 1119087.620470317], [2593302.0070864228, 1118996.9140255074]])



