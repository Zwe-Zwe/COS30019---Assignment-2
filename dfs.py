import math

# ---------- Graph Definition ----------
nodes = {
    1: (4, 1),
    2: (2, 2),
    3: (4, 4),
    4: (6, 3),
    5: (5, 6),
    6: (7, 5),
}

edges = {
    (2, 1): 4,
    (3, 1): 5,
    (1, 3): 5,
    (2, 3): 4,
    (3, 2): 5,
    (4, 1): 6,
    (1, 4): 6,
    (4, 3): 5,
    (3, 5): 6,
    (5, 3): 6,
    (4, 5): 7,
    (5, 4): 8,
    (6, 3): 7,
    (3, 6): 7,
}

origin = 2
goals = {4, 5}


# ---------- Helper Functions ----------
def get_neighbors(node_id):
    """Return a list of (neighbor, cost) for directed edges."""
    return [(v, cost) for (u, v), cost in edges.items() if u == node_id]


def euclidean(a, b):
    ax, ay = nodes[a]
    bx, by = nodes[b]
    return math.sqrt((ax - bx) ** 2 + (ay - by) ** 2)


# ---------- DFS Implementation ----------
def dfs(start, goals):
    stack = [(start, [start], 0)]  # (node, path, cost)
    explored = []

    while stack:
        node, path, cost = stack.pop()
        if node in explored:
            continue
        explored.append(node)

        if node in goals:
            return {
                "goal": node,
                "explored": explored,
                "path": path,
                "path_length": cost,
            }

        # Push neighbors in descending order so smaller ID expands first (DFS stack LIFO)
        for neighbor, edge_cost in sorted(get_neighbors(node), reverse=True):
            if neighbor not in explored:
                stack.append((neighbor, path + [neighbor], cost + edge_cost))

    return None


# ---------- Run the Test ----------
result = dfs(origin, goals)

# ---------- Display ----------
if result:
    print(f"Nodes Explored: {result['explored']}")
    print(f"Goal Found: {result['goal']}")
    print(f"Path Length: {result['path_length']}")
    print("Path:", " -> ".join(map(str, result['path'])))
else:
    print("No goal found.")
