# COS30019 - Introduction to AI - Assignment 2 Part A

## Route Finding with Tree-Based Search Algorithms

This project implements various tree-based search algorithms to find optimal paths in a 2D graph. The algorithms include both uninformed (DFS, BFS) and informed (GBFS, A*) search strategies, as well as two custom algorithms.

## Requirements

- Python 3.x
- No external dependencies required (only standard libraries are used)

## Project Structure

- `search.py`: Main script for running the search algorithms
- `search_gui.py`: Tkinter-based visualizer for comparing algorithm behaviour
- `src/parser.py`: Module for parsing problem files
- `src/search_algorithms.py`: Implementation of all search algorithms
- `test_cases/`: Directory containing test problem files

## Search Algorithms Implemented

1. **DFS (Depth-First Search)**: Uninformed search that explores as far as possible along each branch before backtracking
2. **BFS (Breadth-First Search)**: Uninformed search that explores all nodes at the present depth before moving to nodes at the next depth level
3. **GBFS (Greedy Best-First Search)**: Informed search that uses a heuristic to estimate the cost to reach the goal
4. **AS (A* Search)**: Informed search that uses both the cost so far and a heuristic to estimate total cost
5. **CUS1 (Iterative Deepening Depth-First Search)**: Custom uninformed search that performs DFS with increasing depth limits
6. **CUS2 (Bidirectional Search)**: Custom informed search that searches simultaneously from both the start and goal nodes

## Usage

```bash
python search.py <filename> <method>
```

Where:
- `<filename>`: Path to the problem file
- `<method>`: One of `dfs`, `bfs`, `gbfs`, `as`, `cus1`, `cus2`

## Problem File Format

The problems are stored in simple text files with the following format:
```
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
```

- **Nodes**: Each line specifies a node and its coordinates (node_id: (x,y))
- **Edges**: Each line specifies an edge and its cost (from_node,to_node): cost
- **Origin**: The starting node
- **Destinations**: One or more destination nodes separated by semicolons

## Output Format

For a successful search, the output will be in the following format:
```
filename method
goal number_of_nodes
path
```

- `filename`: The name of the problem file
- `method`: The search method used
- `goal`: The goal node reached
- `number_of_nodes`: The number of nodes created during the search
- `path`: The sequence of nodes in the solution path

## Example

```
python search.py test_cases/example.txt bfs
```

Sample output:
```
example.txt bfs
5 12
2 3 5
```

## Interactive Visualizer

To explore the search strategies side-by-side:

```bash
python search_gui.py
```

The GUI lets you:
- Load any of the problem definitions in `test_cases/`
- Pick an algorithm and generate a full trace of explored and frontier nodes
- Step through the trace or play it as an animation with adjustable speed
- Inspect the final path, nodes generated, and cumulative cost for each run

This tool uses only the Python standard library (Tkinter). No additional dependencies are required. At the moment, it focuses on the provided coordinate-based graphs—ensure your problem files include node coordinates so that the canvas rendering is meaningful.
