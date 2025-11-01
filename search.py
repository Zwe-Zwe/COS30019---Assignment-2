#!/usr/bin/env python3

import sys
import os
from src.parser import parse_problem
from src.search_algorithms import dfs, bfs, gbfs, astar, cus1, cus2

def main():
    """
    Main function that handles command-line arguments and runs the search algorithm.
    Usage: python search.py <filename> <method>
    """
    # Check if the correct number of arguments is provided
    if len(sys.argv) != 3:
        print("Usage: python search.py <filename> <method>")
        sys.exit(1)
    
    # Get the filename and method from the command line arguments
    filename = sys.argv[1]
    method = sys.argv[2].lower()
    
    # Check if the file exists
    if not os.path.exists(filename):
        print(f"Error: File {filename} does not exist.")
        sys.exit(1)
    
    # Parse the problem from the file
    problem = parse_problem(filename)
    
    # Run the appropriate search algorithm based on the method
    if method == "dfs":
        result = dfs(problem)
    elif method == "bfs":
        result = bfs(problem)
    elif method == "gbfs":
        result = gbfs(problem)
    elif method == "as":
        result = astar(problem)
    elif method == "cus1":
        result = cus1(problem)
    elif method == "cus2":
        result = cus2(problem)
    else:
        print(f"Error: Unknown method {method}. Available methods: dfs, bfs, gbfs, as, cus1, cus2")
        sys.exit(1)
    
    # If no solution is found
    if not result:
        print(f"File Name: {os.path.basename(filename)}")
        print(f"Method: {method.upper()}")
        print(f"Goal: None")
        print(f"Number of Nodes: 0")
        print(f"Path: No solution found")
        return
    
    # Check if result has 3 or 4 values and handle accordingly
    if len(result) == 3:
        goal, num_nodes, path = result
        expanded_nodes = num_nodes  # Default if not provided
    else:
        goal, num_nodes, expanded_nodes, path = result
    
    # Format path with arrows
    path_formatted = " -> ".join(path.split())
    
    # Print the result in the required format
    print(f"File Name: {os.path.basename(filename)}")
    print(f"Method: {method.upper()}")
    print(f"Goal: {goal}")
    print(f"Number of Nodes: {num_nodes}")
    print(f"Path: {path_formatted}")

if __name__ == "__main__":
    main()