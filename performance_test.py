#!/usr/bin/env python3

import os
import sys
import time
from src.parser import parse_problem
from src.search_algorithms import dfs, bfs, gbfs, astar, cus1, cus2

def run_test(filename, algorithm_name, algorithm_func):
    print(f"\nRunning {algorithm_name} on {os.path.basename(filename)}")
    problem = parse_problem(filename)
    
    start_time = time.time()
    result = algorithm_func(problem)
    end_time = time.time()
    
    execution_time = end_time - start_time
    
    if result:
        goal, node_count, path = result
        print(f"Goal: {goal}")
        print(f"Nodes created: {node_count}")
        print(f"Path: {path}")
        print(f"Path length: {len(path.split())}")
        print(f"Execution time: {execution_time:.6f} seconds")
        return {
            'algorithm': algorithm_name,
            'goal': goal,
            'nodes': node_count,
            'path_length': len(path.split()),
            'time': execution_time
        }
    else:
        print("No solution found")
        return {
            'algorithm': algorithm_name,
            'goal': None,
            'nodes': None,
            'path_length': None,
            'time': execution_time
        }

def main():
    if len(sys.argv) != 2:
        print("Usage: python performance_test.py <test_directory>")
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
        ("IDDFS", cus1),
        ("Bidirectional", cus2)
    ]
    
    test_files = []
    for filename in os.listdir(test_dir):
        if filename.endswith('.txt'):
            test_files.append(os.path.join(test_dir, filename))
    
    results = []
    
    print(f"Running performance tests on {len(test_files)} test files")
    
    for filename in sorted(test_files):
        print(f"\n===== Testing {os.path.basename(filename)} =====")
        file_results = []
        
        for algorithm_name, algorithm_func in algorithms:
            result = run_test(filename, algorithm_name, algorithm_func)
            file_results.append(result)
        
        results.append({
            'file': os.path.basename(filename),
            'results': file_results
        })
    
    # Print summary table
    print("\n===== Performance Summary =====")
    print("File                 | Algorithm      | Goal | Nodes | Path Length | Time (s)")
    print("-" * 80)
    
    for file_result in results:
        filename = file_result['file']
        for result in file_result['results']:
            if result['goal'] is not None:
                print(f"{filename:20} | {result['algorithm']:14} | {result['goal']:4} | {result['nodes']:5} | {result['path_length']:11} | {result['time']:.6f}")
            else:
                print(f"{filename:20} | {result['algorithm']:14} | None | None  | None        | {result['time']:.6f}")

if __name__ == "__main__":
    main()