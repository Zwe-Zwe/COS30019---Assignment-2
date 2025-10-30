#!/usr/bin/env python3

import re

class Problem:
    """
    Class representing a route finding problem with nodes, edges, origin, and destinations.
    """
    def __init__(self):
        self.nodes = {}  # Dict of node_id: (x, y) coordinates
        self.edges = {}  # Dict of (from_node, to_node): cost
        self.origin = None
        self.destinations = []
    
    def add_node(self, node_id, x, y):
        """Add a node with its coordinates."""
        self.nodes[node_id] = (x, y)
    
    def add_edge(self, from_node, to_node, cost):
        """Add an edge with its cost."""
        self.edges[(from_node, to_node)] = cost
    
    def set_origin(self, node_id):
        """Set the origin node."""
        self.origin = node_id
    
    def add_destination(self, node_id):
        """Add a destination node."""
        self.destinations.append(node_id)
    
    def get_neighbors(self, node_id):
        """Get all neighbors of a node with their costs."""
        neighbors = []
        for (from_node, to_node), cost in self.edges.items():
            if from_node == node_id:
                neighbors.append((to_node, cost))
        return neighbors
    
    def get_euclidean_distance(self, node1, node2):
        """Calculate the Euclidean distance between two nodes."""
        if node1 not in self.nodes or node2 not in self.nodes:
            return float('inf')
        
        x1, y1 = self.nodes[node1]
        x2, y2 = self.nodes[node2]
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def get_manhattan_distance(self, node1, node2):
        """Calculate the Manhattan distance between two nodes."""
        if node1 not in self.nodes or node2 not in self.nodes:
            return float('inf')
        
        x1, y1 = self.nodes[node1]
        x2, y2 = self.nodes[node2]
        return abs(x2 - x1) + abs(y2 - y1)
    
    def __str__(self):
        """String representation of the problem."""
        result = "Nodes:\n"
        for node_id, (x, y) in self.nodes.items():
            result += f"{node_id}: ({x},{y})\n"
        
        result += "Edges:\n"
        for (from_node, to_node), cost in self.edges.items():
            result += f"({from_node},{to_node}): {cost}\n"
        
        result += f"Origin:\n{self.origin}\n"
        
        result += "Destinations:\n"
        result += "; ".join(map(str, self.destinations))
        
        return result

def parse_problem(filename):
    """
    Parse a problem file and return a Problem object.
    
    The file format is as follows:
    Nodes:
    1: (4,1)
    ...
    Edges:
    (2,1): 4
    ...
    Origin:
    2
    Destinations:
    5; 4
    """
    problem = Problem()
    section = None
    
    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            
            # Check for section headers
            if line.endswith(':'):
                section = line[:-1].lower()
                continue
            
            # Parse nodes
            if section == 'nodes':
                # Support optional spaces and negative coordinates
                match = re.match(r'(\d+):\s*\((-?\d+),\s*(-?\d+)\)', line)
                if match:
                    node_id = int(match.group(1))
                    x = int(match.group(2))
                    y = int(match.group(3))
                    problem.add_node(node_id, x, y)
            
            # Parse edges
            elif section == 'edges':
                match = re.match(r'\((\d+),(\d+)\):\s*(\d+)', line)
                if match:
                    from_node = int(match.group(1))
                    to_node = int(match.group(2))
                    cost = int(match.group(3))
                    problem.add_edge(from_node, to_node, cost)
            
            # Parse origin
            elif section == 'origin':
                problem.set_origin(int(line))
            
            # Parse destinations
            elif section == 'destinations':
                destinations = line.split(';')
                for dest in destinations:
                    dest = dest.strip()
                    if dest:
                        problem.add_destination(int(dest))
    
    return problem