from src.parser import parse_problem
from src.search_algorithms import cus2
import sys


def obs(event):
    alg = event.get("algorithm")
    action = event.get("action")
    curr = event.get("current")
    ff = event.get("frontier_forward")
    fb = event.get("frontier_backward")
    ef = event.get("explored_forward")
    eb = event.get("explored_backward")
    path = event.get("path")
    path_cost = event.get("path_cost")
    print(f"[{action}] curr={curr} cost={path_cost} ff={ff} fb={fb} ef={ef} eb={eb} path={path}")


if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else "test_cases/test_case_4_symmetric_cross_graph.txt"
    prob = parse_problem(filename)
    print("ORIGIN:", prob.origin)
    print("DESTS:", prob.destinations)
    print("NODES:", len(prob.nodes))
    print("EDGES:", len(prob.edges))
    print("Neighbors(origin):", prob.get_neighbors(prob.origin))
    print("Neighbors(target):", prob.get_neighbors(prob.destinations[0]))
    res = cus2(prob, observer=obs)
    print("RESULT:", res)
