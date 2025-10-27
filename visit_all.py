#!/usr/bin/env python3

import copy
import itertools
import sys
from src.parser import parse_problem
from src.search_algorithms import astar

def compute_path_cost(problem, path):
    """
    Compute the total cost of a path.
    """
    total_cost = 0
    for i in range(len(path) - 1):
        from_node = int(path[i])
        to_node = int(path[i + 1])
        if (from_node, to_node) in problem.edges:
            total_cost += problem.edges[(from_node, to_node)]
        else:
            return float('inf')  # Invalid path
    return total_cost

def visit_all_destinations(problem):
    """
    Find shortest path visiting all destinations, starting from origin.
    """
    # If only one destination, use regular A* search
    if len(problem.destinations) == 1:
        return astar(problem)
    
    # Step 1: Precompute optimal paths between all node pairs
    paths = {}  # Dictionary to store paths: (start, end) -> (cost, path)
    node_count = 0  # Track nodes created during all searches
    
    # Start with origin to all destinations
    for dest in problem.destinations:
        temp_problem = copy.deepcopy(problem)
        temp_problem.destinations = [dest]
        result = astar(temp_problem)
        if result:
            goal, nodes_created, path_string = result
            node_count += nodes_created
            path = path_string.split()
            paths[(problem.origin, dest)] = (
                compute_path_cost(problem, path), 
                path
            )
    
    # Between all pairs of destinations
    for start in problem.destinations:
        for end in problem.destinations:
            if start != end:
                temp_problem = copy.deepcopy(problem)
                temp_problem.origin = start
                temp_problem.destinations = [end]
                result = astar(temp_problem)
                if result:
                    goal, nodes_created, path_string = result
                    node_count += nodes_created
                    path = path_string.split()
                    paths[(start, end)] = (
                        compute_path_cost(problem, path), 
                        path
                    )
    
    # Step 2: Find best order of destinations
    best_order = []
    best_cost = float('inf')
    
    # For small number of destinations, brute force is feasible
    if len(problem.destinations) <= 8:
        # Try all permutations
        for perm in itertools.permutations(problem.destinations):
            order = [problem.origin] + list(perm)
            cost = 0
            valid_path = True
            
            for i in range(len(order) - 1):
                if (order[i], order[i + 1]) in paths:
                    cost += paths[(order[i], order[i + 1])][0]
                else:
                    valid_path = False
                    break
            
            if valid_path and cost < best_cost:
                best_cost = cost
                best_order = list(perm)
    
    # If no valid permutation found or empty destinations
    if not best_order and problem.destinations:
        # Use nearest neighbor heuristic as fallback
        remaining = set(problem.destinations)
        current = problem.origin
        order = []
        
        while remaining:
            next_candidates = [(dest, paths.get((current, dest), (float('inf'), []))[0])
                              for dest in remaining]
            if not next_candidates:
                return None  # No path possible
                
            next_dest, cost = min(next_candidates, key=lambda x: x[1])
            if cost == float('inf'):
                return None  # No path to any remaining destination
                
            order.append(next_dest)
            remaining.remove(next_dest)
            current = next_dest
        
        best_order = order
    
    # If no valid order found
    if not best_order:
        return None
    
    # Step 3: Construct the complete path
    complete_path = [str(problem.origin)]
    
    for i in range(len(best_order)):
        start = problem.origin if i == 0 else best_order[i-1]
        end = best_order[i]
        
        # Skip first node as it's already included
        if (start, end) in paths:
            segment_path = paths[(start, end)][1][1:]
            complete_path.extend(segment_path)
        else:
            return None  # No path found between consecutive points
    
    path_string = " ".join(complete_path)
    return best_order[-1], node_count, path_string

def main():
    """
    Main function to find a path that visits all destinations.
    """
    if len(sys.argv) != 2:
        print("Usage: python visit_all.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    problem = parse_problem(filename)
    
    result = visit_all_destinations(problem)
    
    if result:
        goal, node_count, path = result
        print(f"{sys.argv[1]} visit_all")
        print(f"{goal} {node_count}")
        print(path)
        print(f"\nPath visits all destinations: {', '.join(map(str, problem.destinations))}")
        print(f"Total cost: {compute_path_cost(problem, path.split())}")
    else:
        print(f"{sys.argv[1]} visit_all")
        print("No solution found.")

if __name__ == "__main__":
    main()