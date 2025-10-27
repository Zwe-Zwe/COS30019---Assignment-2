#!/usr/bin/env python3

from collections import deque
import heapq
from src.parser import Problem

class Node:
    """
    A node in the search tree representing a state in the search space.
    """
    def __init__(self, state, parent=None, action=None, path_cost=0):
        self.state = state  # The state (node_id in the graph)
        self.parent = parent  # Parent node in the search tree
        self.action = action  # Action that led to this node
        self.path_cost = path_cost  # Cost from start to this node
        self.depth = 0 if parent is None else parent.depth + 1
        
    def __lt__(self, other):
        """
        Less than comparison for priority queue.
        When all else is equal, nodes should be expanded according to the ascending order.
        """
        return self.state < other.state
    
    def get_path(self):
        """
        Return the path from the root to this node as a list of states.
        """
        node = self
        path = []
        while node:
            path.append(node.state)
            node = node.parent
        return list(reversed(path))
    
    def get_path_string(self):
        """
        Return the path as a string in the required format.
        """
        path = self.get_path()
        return " ".join(map(str, path))

def solution(node, problem, node_count):
    """
    Return the solution in the required format:
    goal node, number of nodes, path
    """
    goal_node = node.state
    path = node.get_path_string()
    return goal_node, node_count, path

def _notify(observer, **payload):
    """
    Send payload to observer callback when provided.
    """
    if observer:
        observer({
            **payload,
            "algorithm": payload.get("algorithm"),
        })


def _goal_signature(node):
    """Return a comparable signature for a goal node."""
    return (
        node.path_cost,
        node.depth,
        tuple(node.get_path()),
    )


def _is_better_goal(candidate, current_best):
    """Determine if the candidate goal improves on the current best solution."""
    if current_best is None:
        return True
    return _goal_signature(candidate) < _goal_signature(current_best)

# Uninformed Search Algorithms

def dfs(problem, observer=None):
    """
    Depth-First Search algorithm.
    Select one option, try it, go back when there are no more options.
    """
    # Initialize the frontier with the origin node
    origin_node = Node(problem.origin)
    frontier = [origin_node]
    # Keep track of explored nodes to avoid cycles
    explored = set()
    # Keep track of the number of nodes created
    node_count = 1
    # Track the best goal encountered so far
    best_node = None
    
    while frontier:
        # Pop the last node (LIFO)
        node = frontier.pop()
        
        # Check if the node is a goal
        if node.state in problem.destinations:
            if _is_better_goal(node, best_node):
                best_node = node
            continue

        # Skip expanding nodes that can no longer improve the best solution
        if best_node and node.path_cost > best_node.path_cost:
            continue

        if node.state in explored:
            continue
        
        # Add the node to the explored set
        explored.add(node.state)
        
        # Get neighbors and add them to the frontier if not already explored
        neighbors = problem.get_neighbors(node.state)
        
        # Sort neighbors by node_id in ascending order
        neighbors.sort(key=lambda x: x[0])
        
        # Reverse the order to ensure DFS expands the smallest node_id last (since we pop from the end)
        neighbors.reverse()
        
        for neighbor_state, cost in neighbors:
            if neighbor_state not in explored and not any(n.state == neighbor_state for n in frontier):
                new_cost = node.path_cost + cost
                if best_node and new_cost > best_node.path_cost:
                    continue
                child = Node(
                    state=neighbor_state,
                    parent=node,
                    action=(node.state, neighbor_state),
                    path_cost=new_cost
                )
                frontier.append(child)
                node_count += 1
        
        _notify(
            observer,
            algorithm="dfs",
            action="expand",
            current=node.state,
            frontier=[n.state for n in frontier],
            explored=sorted(explored),
            path=node.get_path(),
            path_cost=node.path_cost,
            nodes_created=node_count,
        )
    
    if best_node:
        _notify(
            observer,
            algorithm="dfs",
            action="goal",
            current=best_node.state,
            frontier=[n.state for n in frontier],
            explored=sorted(explored),
            path=best_node.get_path(),
            path_cost=best_node.path_cost,
            nodes_created=node_count,
        )
        return solution(best_node, problem, node_count)

    # No solution found
    return None

def bfs(problem, observer=None):
    """
    Breadth-First Search algorithm.
    Expand all options one level at a time.
    """
    # Initialize the frontier with the origin node
    origin_node = Node(problem.origin)
    frontier = deque([origin_node])
    # Keep track of explored nodes to avoid cycles
    explored = set()
    # Keep track of the number of nodes created
    node_count = 1
    # Track the best goal encountered
    best_node = None
    
    while frontier:
        # Pop the first node (FIFO)
        node = frontier.popleft()
        
        # Check if the node is a goal
        if node.state in problem.destinations:
            if _is_better_goal(node, best_node):
                best_node = node
            continue

        if best_node and node.path_cost > best_node.path_cost:
            continue

        if node.state in explored:
            continue
        
        # Add the node to the explored set
        explored.add(node.state)
        
        # Get neighbors and add them to the frontier if not already explored
        neighbors = problem.get_neighbors(node.state)
        
        # Sort neighbors by node_id in ascending order
        neighbors.sort(key=lambda x: x[0])
        
        for neighbor_state, cost in neighbors:
            if neighbor_state not in explored and not any(n.state == neighbor_state for n in frontier):
                new_cost = node.path_cost + cost
                if best_node and new_cost > best_node.path_cost:
                    continue
                child = Node(
                    state=neighbor_state,
                    parent=node,
                    action=(node.state, neighbor_state),
                    path_cost=new_cost
                )
                frontier.append(child)
                node_count += 1
        
        _notify(
            observer,
            algorithm="bfs",
            action="expand",
            current=node.state,
            frontier=[n.state for n in frontier],
            explored=sorted(explored),
            path=node.get_path(),
            path_cost=node.path_cost,
            nodes_created=node_count,
        )
    
    if best_node:
        _notify(
            observer,
            algorithm="bfs",
            action="goal",
            current=best_node.state,
            frontier=[n.state for n in frontier],
            explored=sorted(explored),
            path=best_node.get_path(),
            path_cost=best_node.path_cost,
            nodes_created=node_count,
        )
        return solution(best_node, problem, node_count)

    # No solution found
    return None

# Informed Search Algorithms

class PriorityNode(Node):
    """
    A node with a priority for use in priority queues.
    """
    def __init__(self, state, parent=None, action=None, path_cost=0, priority=0):
        super().__init__(state, parent, action, path_cost)
        self.priority = priority
    
    def __lt__(self, other):
        """
        Less than comparison for priority queue.
        When priorities are equal, compare states.
        """
        if self.priority == other.priority:
            return self.state < other.state
        return self.priority < other.priority

def gbfs(problem, observer=None):
    """
    Greedy Best-First Search algorithm.
    Use only the heuristic cost to reach the goal from the current node to evaluate the node.
    """
    def h(node_state):
        """
        Heuristic function: minimum Euclidean distance to any goal.
        """
        return min(problem.get_euclidean_distance(node_state, dest) for dest in problem.destinations)
    
    # Initialize the frontier with the origin node
    origin_node = PriorityNode(
        state=problem.origin,
        priority=h(problem.origin)
    )
    
    frontier = [(origin_node.priority, id(origin_node), origin_node)]
    frontier_set = {problem.origin}  # Keep track of nodes in frontier for fast lookup
    heapq.heapify(frontier)
    
    # Keep track of explored nodes to avoid cycles
    explored = set()
    # Keep track of the number of nodes created
    node_count = 1
    # Track the best goal encountered
    best_node = None
    
    while frontier:
        # Pop the node with the lowest heuristic cost
        _, _, node = heapq.heappop(frontier)
        frontier_set.remove(node.state)
        
        # Check if the node is a goal
        if node.state in problem.destinations:
            if _is_better_goal(node, best_node):
                best_node = node
            continue

        if best_node and node.path_cost > best_node.path_cost:
            continue

        if node.state in explored:
            continue
        
        # Add the node to the explored set
        explored.add(node.state)
        
        # Get neighbors and add them to the frontier if not already explored
        neighbors = problem.get_neighbors(node.state)
        
        # Sort neighbors by node_id in ascending order to ensure deterministic expansion
        neighbors.sort(key=lambda x: x[0])
        
        for neighbor_state, cost in neighbors:
            if neighbor_state not in explored and neighbor_state not in frontier_set:
                new_cost = node.path_cost + cost
                if best_node and new_cost > best_node.path_cost:
                    continue
                child = PriorityNode(
                    state=neighbor_state,
                    parent=node,
                    action=(node.state, neighbor_state),
                    path_cost=new_cost,
                    priority=h(neighbor_state)
                )
                heapq.heappush(frontier, (child.priority, id(child), child))
                frontier_set.add(neighbor_state)
                node_count += 1
            elif neighbor_state in frontier_set:
                # If the neighbor is already in the frontier, update its priority if the new priority is lower
                for i, (_, _, existing_node) in enumerate(frontier):
                    if existing_node.state == neighbor_state:
                        new_cost = node.path_cost + cost
                        if best_node and new_cost > best_node.path_cost:
                            break
                        new_priority = h(neighbor_state)
                        if new_priority < existing_node.priority:
                            # Replace the node with the new one with lower priority
                            child = PriorityNode(
                                state=neighbor_state,
                                parent=node,
                                action=(node.state, neighbor_state),
                                path_cost=new_cost,
                                priority=new_priority
                            )
                            frontier[i] = (new_priority, id(child), child)
                            heapq.heapify(frontier)  # Re-heapify after modification
                            node_count += 1
                        break
        
        _notify(
            observer,
            algorithm="gbfs",
            action="expand",
            current=node.state,
            frontier=[n.state for _, _, n in frontier],
            explored=sorted(explored),
            path=node.get_path(),
            path_cost=node.path_cost,
            heuristic=h(node.state),
            nodes_created=node_count,
        )
    
    if best_node:
        _notify(
            observer,
            algorithm="gbfs",
            action="goal",
            current=best_node.state,
            frontier=[n.state for _, _, n in frontier],
            explored=sorted(explored),
            path=best_node.get_path(),
            path_cost=best_node.path_cost,
            heuristic=h(best_node.state),
            nodes_created=node_count,
        )
        return solution(best_node, problem, node_count)

    # No solution found
    return None

def astar(problem, observer=None):
    """
    A* Search algorithm.
    Use both the cost to reach the goal from the current node and the cost to reach this node to evaluate the node.
    """
    def h(node_state):
        """
        Heuristic function: minimum Euclidean distance to any goal.
        """
        return min(problem.get_euclidean_distance(node_state, dest) for dest in problem.destinations)
    
    # Initialize the frontier with the origin node
    origin_node = PriorityNode(
        state=problem.origin,
        priority=h(problem.origin)
    )
    
    frontier = [(origin_node.priority, id(origin_node), origin_node)]
    frontier_set = {problem.origin: 0}  # Keep track of nodes in frontier with their path costs
    heapq.heapify(frontier)
    
    # Keep track of explored nodes to avoid cycles
    explored = set()
    # Keep track of the number of nodes created
    node_count = 1
    # Track the best goal encountered
    best_node = None
    
    while frontier:
        if best_node and frontier and frontier[0][0] > best_node.path_cost:
            break
        # Pop the node with the lowest f-cost (g + h)
        _, _, node = heapq.heappop(frontier)
        frontier_set.pop(node.state, None)
        
        # Check if the node is a goal
        if node.state in problem.destinations:
            if _is_better_goal(node, best_node):
                best_node = node
            continue

        if best_node and node.path_cost > best_node.path_cost:
            continue
        
        # Add the node to the explored set
        explored.add(node.state)
        
        # Get neighbors and add them to the frontier if not already explored
        neighbors = problem.get_neighbors(node.state)
        
        # Sort neighbors by node_id in ascending order to ensure deterministic expansion
        neighbors.sort(key=lambda x: x[0])
        
        for neighbor_state, cost in neighbors:
            # Calculate the new path cost to this neighbor
            new_cost = node.path_cost + cost
            
            if neighbor_state not in explored and neighbor_state not in frontier_set:
                if best_node and new_cost > best_node.path_cost:
                    continue
                # Create a new node
                child = PriorityNode(
                    state=neighbor_state,
                    parent=node,
                    action=(node.state, neighbor_state),
                    path_cost=new_cost,
                    priority=new_cost + h(neighbor_state)
                )
                heapq.heappush(frontier, (child.priority, id(child), child))
                frontier_set[neighbor_state] = new_cost
                node_count += 1
            elif neighbor_state in frontier_set and new_cost < frontier_set[neighbor_state]:
                if best_node and new_cost > best_node.path_cost:
                    continue
                # If the neighbor is already in the frontier, update its priority if the new path cost is lower
                for i, (_, _, existing_node) in enumerate(frontier):
                    if existing_node.state == neighbor_state:
                        # Replace the node with the new one with lower priority
                        child = PriorityNode(
                            state=neighbor_state,
                            parent=node,
                            action=(node.state, neighbor_state),
                            path_cost=new_cost,
                            priority=new_cost + h(neighbor_state)
                        )
                        frontier[i] = (child.priority, id(child), child)
                        heapq.heapify(frontier)  # Re-heapify after modification
                        frontier_set[neighbor_state] = new_cost
                        node_count += 1
                        break
        
        _notify(
            observer,
            algorithm="astar",
            action="expand",
            current=node.state,
            frontier=[n.state for _, _, n in frontier],
            explored=sorted(explored),
            path=node.get_path(),
            path_cost=node.path_cost,
            heuristic=h(node.state),
            f_cost=node.path_cost + h(node.state),
            nodes_created=node_count,
        )
    
    if best_node:
        _notify(
            observer,
            algorithm="astar",
            action="goal",
            current=best_node.state,
            frontier=[n.state for _, _, n in frontier],
            explored=sorted(explored),
            path=best_node.get_path(),
            path_cost=best_node.path_cost,
            heuristic=h(best_node.state),
            f_cost=best_node.path_cost + h(best_node.state),
            nodes_created=node_count,
        )
        return solution(best_node, problem, node_count)

    # No solution found
    return None

# Custom Search Algorithms

def cus1(problem, observer=None):
    """
    Custom Search Strategy 1: Iterative Deepening Depth-First Search (IDDFS).
    An uninformed method to find a path to reach the goal.
    """
    # Implement IDDFS - starts with depth 0 and increases depth limit until a solution is found
    node_count = 1
    depth_limit = 0
    
    while True:
        # Track visited nodes for this depth limit
        visited = set()
        
        # Use a stack for DFS
        stack = [(Node(problem.origin), 0)]
        best_node = None
        
        while stack:
            node, depth = stack.pop()
            
            # Check if the node is a goal
            if node.state in problem.destinations:
                if _is_better_goal(node, best_node):
                    best_node = node
                continue
            
            # Continue only if we haven't reached the depth limit
            if depth < depth_limit:
                # Mark the node as visited
                visited.add(node.state)
                
                # Get neighbors
                neighbors = problem.get_neighbors(node.state)
                
                # Sort neighbors by node_id in ascending order
                neighbors.sort(key=lambda x: x[0])
                
                # Reverse the order to ensure DFS expands the smallest node_id last (since we pop from the end)
                neighbors.reverse()
                
                for neighbor_state, cost in neighbors:
                    if neighbor_state not in visited:
                        new_cost = node.path_cost + cost
                        if best_node and new_cost > best_node.path_cost:
                            continue
                        child = Node(
                            state=neighbor_state,
                            parent=node,
                            action=(node.state, neighbor_state),
                            path_cost=new_cost
                        )
                        stack.append((child, depth + 1))
                        node_count += 1
                
                _notify(
                    observer,
                    algorithm="cus1",
                    action="expand",
                    current=node.state,
                    frontier=[n.state for n, _ in stack],
                    explored=sorted(visited),
                    path=node.get_path(),
                    path_cost=node.path_cost,
                    depth=depth,
                    depth_limit=depth_limit,
                    nodes_created=node_count,
                )

        if best_node:
            _notify(
                observer,
                algorithm="cus1",
                action="goal",
                current=best_node.state,
                frontier=[n.state for n, _ in stack],
                explored=sorted(visited),
                path=best_node.get_path(),
                path_cost=best_node.path_cost,
                depth=best_node.depth,
                depth_limit=depth_limit,
                nodes_created=node_count,
            )
            return solution(best_node, problem, node_count)
        
        # Increase the depth limit for the next iteration
        depth_limit += 1
        
        # If the depth limit gets too large, we might be in an infinite loop
        if depth_limit > 1000:
            return None

def cus2(problem, observer=None):
    """
    Custom Search Strategy 2: Bidirectional Search.
    An informed method to find a shortest path (with least moves) to reach the goal.
    """
    # Check if there are multiple destinations
    if len(problem.destinations) > 1:
        # For multiple destinations, choose the one closest to origin as the target for bidirectional search
        # This is a simplification, as true bidirectional search with multiple targets would be more complex
        target = min(problem.destinations, 
                    key=lambda dest: problem.get_euclidean_distance(problem.origin, dest))
    else:
        # For a single destination
        target = problem.destinations[0]
    
    # Initialize forward search from origin
    forward_frontier = deque([Node(problem.origin)])
    forward_explored = {problem.origin: Node(problem.origin)}
    
    # Initialize backward search from target
    backward_frontier = deque([Node(target)])
    backward_explored = {target: Node(target)}
    
    # Keep track of the number of nodes created
    node_count = 2  # One for origin, one for target
    
    # Keep track of the best intersection node and path cost
    best_intersection = None
    best_cost = float('inf')
    
    while forward_frontier and backward_frontier:
        # Forward search step
        if forward_frontier:
            forward_node = forward_frontier.popleft()
            
            # Check if forward search has reached any node explored by backward search
            if forward_node.state in backward_explored:
                # Found an intersection - check if it's better than current best
                backward_node = backward_explored[forward_node.state]
                total_cost = forward_node.path_cost + backward_node.path_cost
                if total_cost < best_cost:
                    best_intersection = (forward_node, backward_node)
                    best_cost = total_cost
            
            # Expand forward node
            neighbors = problem.get_neighbors(forward_node.state)
            neighbors.sort(key=lambda x: x[0])  # Sort by node ID in ascending order
            
            for neighbor_state, cost in neighbors:
                # Calculate new path cost
                new_cost = forward_node.path_cost + cost
                
                if neighbor_state not in forward_explored or new_cost < forward_explored[neighbor_state].path_cost:
                    # Create new node
                    child = Node(
                        state=neighbor_state,
                        parent=forward_node,
                        action=(forward_node.state, neighbor_state),
                        path_cost=new_cost
                    )
                    forward_frontier.append(child)
                    forward_explored[neighbor_state] = child
                    node_count += 1
            
            _notify(
                observer,
                algorithm="cus2",
                action="forward_expand",
                current=forward_node.state,
                frontier_forward=[n.state for n in forward_frontier],
                frontier_backward=[n.state for n in backward_frontier],
                explored_forward=sorted(forward_explored.keys()),
                explored_backward=sorted(backward_explored.keys()),
                path=forward_node.get_path(),
                path_cost=forward_node.path_cost,
                nodes_created=node_count,
            )
        
        # Backward search step
        if backward_frontier:
            backward_node = backward_frontier.popleft()
            
            # Check if backward search has reached any node explored by forward search
            if backward_node.state in forward_explored:
                # Found an intersection - check if it's better than current best
                forward_node = forward_explored[backward_node.state]
                total_cost = forward_node.path_cost + backward_node.path_cost
                if total_cost < best_cost:
                    best_intersection = (forward_node, backward_node)
                    best_cost = total_cost
            
            # Find all nodes that have edges TO this node (reverse neighbors)
            # This is more complex because we need to search all edges
            reverse_neighbors = []
            for (from_node, to_node), edge_cost in problem.edges.items():
                if to_node == backward_node.state:
                    reverse_neighbors.append((from_node, edge_cost))
            
            reverse_neighbors.sort(key=lambda x: x[0])  # Sort by node ID in ascending order
            
            for neighbor_state, cost in reverse_neighbors:
                # Calculate new path cost
                new_cost = backward_node.path_cost + cost
                
                if neighbor_state not in backward_explored or new_cost < backward_explored[neighbor_state].path_cost:
                    # Create new node
                    child = Node(
                        state=neighbor_state,
                        parent=backward_node,
                        action=(neighbor_state, backward_node.state),  # Note the reversed action
                        path_cost=new_cost
                    )
                    backward_frontier.append(child)
                    backward_explored[neighbor_state] = child
                    node_count += 1
            
            _notify(
                observer,
                algorithm="cus2",
                action="backward_expand",
                current=backward_node.state,
                frontier_forward=[n.state for n in forward_frontier],
                frontier_backward=[n.state for n in backward_frontier],
                explored_forward=sorted(forward_explored.keys()),
                explored_backward=sorted(backward_explored.keys()),
                path=backward_node.get_path(),
                path_cost=backward_node.path_cost,
                nodes_created=node_count,
            )
    
    # Check if an intersection was found
    if best_intersection:
        forward_node, backward_node = best_intersection
        
        # Construct complete path
        # First, get the path from origin to intersection
        forward_path = forward_node.get_path()
        
        # Then, get the path from target to intersection (reversed)
        backward_path = backward_node.get_path()
        backward_path.reverse()
        
        # Remove duplicate intersection node
        backward_path.pop(0)
        
        # Combine paths
        complete_path = forward_path + backward_path
        
        # Create a new node with the complete path
        result_node = Node(target)
        result_node.path_cost = best_cost
        
        # Override the get_path method to return our complete path
        def custom_path():
            return " ".join(map(str, complete_path))
        
        result_node.get_path_string = custom_path
        
        _notify(
            observer,
            algorithm="cus2",
            action="goal",
            current=target,
            frontier_forward=[n.state for n in forward_frontier],
            frontier_backward=[n.state for n in backward_frontier],
            explored_forward=sorted(forward_explored.keys()),
            explored_backward=sorted(backward_explored.keys()),
            path=list(complete_path),
            path_cost=best_cost,
            nodes_created=node_count,
        )

        return solution(result_node, problem, node_count)
    
    # No solution found
    return None
