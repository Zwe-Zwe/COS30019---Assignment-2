#!/usr/bin/env python3
"""
Performance testing harness for all search algorithms.
Tests all algorithms on all test files and produces a formatted comparison table.
"""

import os
import sys
import time
from src.parser import parse_problem
from src.search_algorithms import dfs, bfs, gbfs, astar, cus1, cus2

def compute_path_cost(problem, path_nodes):
    """Calculate the total cost of a path."""
    if not path_nodes or len(path_nodes) < 2:
        return None
    cost = 0
    for i in range(len(path_nodes) - 1):
        edge_cost = problem.edges.get((path_nodes[i], path_nodes[i + 1]))
        if edge_cost is None:
            return None
        cost += edge_cost
    return cost

def run_test(filename, algorithm_name, algorithm_func):
    """Run a single algorithm on a test file and return metrics."""
    problem = parse_problem(filename)
    
    start_time = time.perf_counter()
    result = algorithm_func(problem)
    end_time = time.perf_counter()
    
    execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
    
    if result:
        goal, node_count, path = result
        path_nodes = [int(x) for x in path.split()]
        path_cost = compute_path_cost(problem, path_nodes)
        return {
            'algorithm': algorithm_name,
            'goal': goal,
            'nodes': node_count,
            'path_length': len(path_nodes),
            'path_cost': path_cost,
            'time_ms': execution_time,
            'path': path
        }
    else:
        return {
            'algorithm': algorithm_name,
            'goal': None,
            'nodes': 0,
            'path_length': 0,
            'path_cost': None,
            'time_ms': execution_time,
            'path': None
        }

def main():
    if len(sys.argv) != 2:
        print("Usage: python performance_test.py <test_directory>")
        print("Example: python performance_test.py test_cases")
        sys.exit(1)
    
    test_dir = sys.argv[1]
    
    if not os.path.isdir(test_dir):
        print(f"Error: {test_dir} is not a directory")
        sys.exit(1)
    
    # Define algorithms to test
    algorithms = [
        ("DFS", dfs),
        ("BFS", bfs),
        ("GBFS", gbfs),
        ("A*", astar),
        ("CUS1", cus1),
        ("CUS2", cus2)
    ]
    
    # Collect test files
    test_files = sorted([
        os.path.join(test_dir, f) 
        for f in os.listdir(test_dir) 
        if f.endswith('.txt')
    ])
    
    if not test_files:
        print(f"No .txt files found in {test_dir}")
        sys.exit(1)
    
    print(f"\n{'='*100}")
    print(f"Performance Test Suite - {len(test_files)} test file(s), {len(algorithms)} algorithm(s)")
    print(f"{'='*100}\n")
    
    all_results = []
    
    # Run tests
    for test_file in test_files:
        filename = os.path.basename(test_file)
        print(f"Testing: {filename}")
        
        file_results = []
        for algo_name, algo_func in algorithms:
            try:
                result = run_test(test_file, algo_name, algo_func)
                file_results.append(result)
                status = "[OK]" if result['goal'] is not None else "[--]"
                print(f"  {status} {algo_name:6} - Goal: {result['goal'] or 'None':4} | Nodes: {result['nodes']:5} | Time: {result['time_ms']:7.2f}ms")
            except Exception as e:
                print(f"  [!!] {algo_name:6} - ERROR: {str(e)}")
                file_results.append({
                    'algorithm': algo_name,
                    'goal': None,
                    'nodes': 0,
                    'path_length': 0,
                    'path_cost': None,
                    'time_ms': 0,
                    'path': None,
                    'error': str(e)
                })
        
        all_results.append({
            'file': filename,
            'results': file_results
        })
        print()
    
    # Print results in compact format
    print(f"\n{'='*100}")
    print(f"Performance Test Suite - {len(all_results)} test file(s), {len(algorithms)} algorithm(s)")
    print(f"{'='*100}\n")
    
    # Print results grouped by file
    for file_data in all_results:
        filename = file_data['file']
        print(f"Testing: {filename}")
        
        for result in file_data['results']:
            algo = result['algorithm']
            goal = result['goal']
            nodes = result['nodes']
            path_len = result['path_length']
            time_ms = result['time_ms']
            path = result['path']
            
            # Determine status indicator
            if goal is not None:
                status = "[OK]"
                goal_str = f"{goal:>4}"
                nodes_str = f"{nodes:>6}"
                path_len_str = f"{path_len:>3}"
                time_str = f"{time_ms:>8.2f}ms"
                path_str = f" | Path: {path}" if path else ""
            else:
                status = "[--]"
                goal_str = "None"
                nodes_str = f"{nodes:>6}"
                path_len_str = "  0"
                time_str = f"{time_ms:>8.2f}ms"
                path_str = ""
            
            print(f"  {status} {algo:<6} - Goal: {goal_str} | Nodes: {nodes_str} | PathLen: {path_len_str} | Time: {time_str}{path_str}")
        
        print()  # Blank line between files

if __name__ == "__main__":
    main()