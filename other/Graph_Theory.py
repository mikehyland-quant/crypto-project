#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from itertools import permutations


def find_all_node_permutations(nodes, min_num=2):
    unique_items = sorted(set(nodes))
    all_paths = []
    for r in range(min_num, len(unique_items) + 1):
        all_paths.extend(permutations(unique_items, r))
    return all_paths


def create_list_of_edges(nodes, edges, near_attr, far_attr): 
    
    edge_list = []
    
    for i in range(len(nodes) - 1):
        node_a = nodes[i]
        node_b = nodes[i + 1]

        near_node = min(node_a, node_b)
        far_node  = max(node_a, node_b)

        next_edge = next(
            (obj for obj in edges
             if getattr(obj, near_attr) == near_node and getattr(obj, far_attr) == far_node),
             None
            )

        if next_edge is not None:
            if near_node == node_a:
                edge_list.append((next_edge, +1))
            else:
                edge_list.append((next_edge, -1))
            continue

        return None  

    return edge_list


def prepend_edge(heads_list, head_attr, edge_list, near_attr, far_attr): 
    
    first_edge, first_direction = edge_list[0]

    if first_direction == 1:
        first_node = getattr(first_edge, near_attr) 
    elif first_direction == -1:
        first_node = getattr(first_edge, far_attr)
    else:
        return None
        
    # Find a head edge whose far node connects to current first node
    pre_edge = next(
        (obj for obj in heads_list
         if getattr(obj, head_attr) == first_node),
        None
    )

    if pre_edge is None:
        return None

    # If pre_edge ends at first_node, direction is +1
    pre_direction = +1

    return [(pre_edge, pre_direction)] + edge_list

    