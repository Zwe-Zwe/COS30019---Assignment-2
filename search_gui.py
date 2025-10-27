#!/usr/bin/env python3
"""
Interactive visualisation tool for the search algorithms included in this project.

Launch with: python search_gui.py
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from src.parser import parse_problem
from src.search_algorithms import dfs, bfs, gbfs, astar, cus1, cus2


ALGORITHMS = {
    "Depth-First Search (DFS)": dfs,
    "Breadth-First Search (BFS)": bfs,
    "Greedy Best-First Search (GBFS)": gbfs,
    "A* Search": astar,
    "Custom 1 - Iterative Deepening DFS": cus1,
    "Custom 2 - Bidirectional Search": cus2,
}


class SearchVisualizer(tk.Tk):
    CANVAS_WIDTH = 800
    CANVAS_HEIGHT = 640

    COLOR_DEFAULT = "#d9d9d9"
    COLOR_START = "#74c476"
    COLOR_GOAL = "#ef3b2c"
    COLOR_EXPLORED = "#6baed6"
    COLOR_EXPLORED_BACK = "#9c9ede"
    COLOR_FRONTIER = "#ffd700"
    COLOR_FRONTIER_BACK = "#fdae6b"
    COLOR_CURRENT = "#ff7f0e"
    COLOR_PATH = "#2ca02c"

    def __init__(self):
        super().__init__()
        self.title("Search Algorithm Visualizer")
        self.geometry("1920x1080")

        self.problem = None
        self.problem_path = None
        self.node_items = {}
        self.node_labels = {}
        self.node_positions = {}
        self.edge_items = {}
        self.edge_labels = {}
        self.base_colors = {}
        self.trace = []
        self.trace_index = 0
        self.playing = False
        self.path_overlay_items = []
        self.result_summary = {}

        self.speed_var = tk.IntVar(value=400)
        self.file_var = tk.StringVar()
        self.algorithm_var = tk.StringVar(value=list(ALGORITHMS.keys())[0])
        self.step_info_var = tk.StringVar(value="Steps will appear here once an algorithm runs.")
        self.metrics_var = tk.StringVar(value="Load a problem file to begin.")

        self._build_layout()
        self._populate_problem_files()

    # ---------------------------------------------------------------------- UI
    def _build_layout(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        controls = ttk.Frame(self, padding=12)
        controls.grid(row=0, column=0, sticky="ns")
        controls.columnconfigure(0, weight=1)

        ttk.Label(controls, text="Problem File").grid(row=0, column=0, sticky="w")
        self.file_combo = ttk.Combobox(
            controls,
            textvariable=self.file_var,
            state="readonly",
            width=32,
        )
        self.file_combo.grid(row=1, column=0, sticky="ew")
        self.file_combo.bind("<<ComboboxSelected>>", lambda _event: self.load_problem())

        file_buttons = ttk.Frame(controls)
        file_buttons.grid(row=2, column=0, pady=(4, 12), sticky="ew")
        ttk.Button(file_buttons, text="Browse…", command=self._browse_file).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(file_buttons, text="Reload", command=self.load_problem).pack(side=tk.LEFT)

        ttk.Label(controls, text="Algorithm").grid(row=3, column=0, sticky="w")
        self.algorithm_combo = ttk.Combobox(
            controls,
            textvariable=self.algorithm_var,
            values=list(ALGORITHMS.keys()),
            state="readonly",
            width=32,
        )
        self.algorithm_combo.grid(row=4, column=0, sticky="ew", pady=(0, 12))

        run_buttons = ttk.Frame(controls)
        run_buttons.grid(row=5, column=0, pady=(0, 8), sticky="ew")
        ttk.Button(run_buttons, text="Run Algorithm", command=self.run_algorithm).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(run_buttons, text="Step", command=self.step_once).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(run_buttons, text="Reset", command=self.reset_visualization).pack(side=tk.LEFT)

        play_buttons = ttk.Frame(controls)
        play_buttons.grid(row=6, column=0, pady=(0, 12), sticky="ew")
        ttk.Button(play_buttons, text="Play", command=self.play_animation).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(play_buttons, text="Pause", command=self.pause_animation).pack(side=tk.LEFT)

        speed_frame = ttk.Frame(controls)
        speed_frame.grid(row=7, column=0, pady=(0, 12), sticky="ew")
        ttk.Label(speed_frame, text="Animation speed (ms)").pack(anchor="w")
        self.speed_scale = ttk.Scale(
            speed_frame,
            from_=50,
            to=2000,
            orient=tk.HORIZONTAL,
            command=self._on_speed_change,
        )
        self.speed_scale.pack(fill="x")
        self.speed_scale.set(self.speed_var.get())

        metrics_frame = ttk.LabelFrame(controls, text="Metrics", padding=8)
        metrics_frame.grid(row=8, column=0, sticky="ew")
        ttk.Label(metrics_frame, textvariable=self.metrics_var, justify=tk.LEFT).pack(anchor="w")

        step_frame = ttk.LabelFrame(controls, text="Step details", padding=8)
        step_frame.grid(row=9, column=0, sticky="ew", pady=(12, 0))
        ttk.Label(step_frame, textvariable=self.step_info_var, justify=tk.LEFT, wraplength=260).pack(anchor="w")

        self.canvas = tk.Canvas(self, width=self.CANVAS_WIDTH, height=self.CANVAS_HEIGHT, bg="white")
        self.canvas.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")

    def _populate_problem_files(self):
        test_cases_dir = os.path.join(os.getcwd(), "test_cases")
        files = []
        if os.path.isdir(test_cases_dir):
            for name in sorted(os.listdir(test_cases_dir)):
                if name.lower().endswith(".txt"):
                    files.append(os.path.join("test_cases", name))
        if not files:
            files.append("")
        self.file_combo["values"] = files
        if files and files[0]:
            self.file_combo.current(0)
            self.load_problem()

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select problem definition",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=os.getcwd(),
        )
        if path:
            rel_path = os.path.relpath(path, os.getcwd())
            self.file_var.set(rel_path)
            if rel_path not in self.file_combo["values"]:
                self.file_combo["values"] = (*self.file_combo["values"], rel_path)
            self.load_problem()

    # --------------------------------------------------------------- Problem IO
    def load_problem(self):
        path = self.file_var.get()
        if not path:
            return
        try:
            full_path = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
            self.problem = parse_problem(full_path)
            self.problem_path = full_path
            self._draw_problem()
            self.metrics_var.set(f"Loaded: {path}\nNodes: {len(self.problem.nodes)}  Edges: {len(self.problem.edges)}")
            self.step_info_var.set("Ready to run an algorithm.")
            self.trace = []
            self.trace_index = 0
        except FileNotFoundError:
            messagebox.showerror("File not found", f"Could not locate {path}")
        except Exception as exc:
            messagebox.showerror("Parse error", f"Failed to parse {path}\n\n{exc}")

    def _draw_problem(self):
        self.canvas.delete("all")
        self.node_items.clear()
        self.node_labels.clear()
        self.node_positions.clear()
        self.edge_items.clear()
        self.edge_labels.clear()
        self.base_colors.clear()
        self.path_overlay_items.clear()

        if not self.problem:
            return

        positions = self._scale_positions(self.problem.nodes)
        self.node_positions.update(positions)

        # Draw edges first so they sit underneath nodes.
        for (from_node, to_node), cost in self.problem.edges.items():
            if from_node not in positions or to_node not in positions:
                continue
            x1, y1 = positions[from_node]
            x2, y2 = positions[to_node]
            line = self.canvas.create_line(x1, y1, x2, y2, fill="#b3b3b3", width=2, arrow=tk.LAST)
            self.edge_items[(from_node, to_node)] = line

            label_x = (x1 + x2) / 2
            label_y = (y1 + y2) / 2
            label = self.canvas.create_text(label_x, label_y, text=str(cost), fill="#666666", font=("Arial", 9))
            self.edge_labels[(from_node, to_node)] = label

        # Draw nodes
        for node_id, (x, y) in positions.items():
            fill = self.COLOR_DEFAULT
            if node_id == self.problem.origin:
                fill = self.COLOR_START
            elif node_id in self.problem.destinations:
                fill = self.COLOR_GOAL
            oval = self.canvas.create_oval(x - 18, y - 18, x + 18, y + 18, fill=fill, outline="#333333", width=2)
            label = self.canvas.create_text(x, y, text=str(node_id), font=("Arial", 11, "bold"))
            self.node_items[node_id] = oval
            self.node_labels[node_id] = label
            self.base_colors[node_id] = fill

    @staticmethod
    def _scale_positions(nodes, margin=60):
        if not nodes:
            return {}
        xs = [coord[0] for coord in nodes.values()]
        ys = [coord[1] for coord in nodes.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)
        width = SearchVisualizer.CANVAS_WIDTH - 2 * margin
        height = SearchVisualizer.CANVAS_HEIGHT - 2 * margin
        scale = min(width / span_x, height / span_y)
        positions = {}
        for node_id, (x, y) in nodes.items():
            canvas_x = margin + (x - min_x) * scale
            canvas_y = SearchVisualizer.CANVAS_HEIGHT - (margin + (y - min_y) * scale)
            positions[node_id] = (canvas_x, canvas_y)
        return positions

    # ------------------------------------------------------------- Run control
    def run_algorithm(self):
        if not self.problem:
            messagebox.showinfo("No problem loaded", "Please load a problem definition first.")
            return
        algorithm_name = self.algorithm_var.get()
        algorithm_fn = ALGORITHMS.get(algorithm_name)
        if not algorithm_fn:
            messagebox.showerror("Algorithm missing", f"Unknown algorithm: {algorithm_name}")
            return

        self.pause_animation()
        self.reset_visualization(redraw=False)

        trace = []

        def observer(event):
            snapshot = {}
            for key, value in event.items():
                if isinstance(value, set):
                    snapshot[key] = sorted(value)
                elif isinstance(value, (list, tuple)):
                    snapshot[key] = list(value)
                else:
                    snapshot[key] = value
            trace.append(snapshot)

        result = algorithm_fn(self.problem, observer=observer)
        if not result:
            messagebox.showinfo("No solution", "The selected algorithm did not find a path.")
            return

        goal, nodes_created, path_str = result
        path_nodes = [int(token) for token in path_str.split()] if path_str else []
        path_cost = self._compute_path_cost(path_nodes)
        self.result_summary = {
            "algorithm": algorithm_name,
            "goal": goal,
            "nodes_created": nodes_created,
            "path": path_nodes,
            "path_cost": path_cost,
            "trace_length": len(trace),
        }

        self.metrics_var.set(
            f"Algorithm: {algorithm_name}\n"
            f"Goal reached: {goal}\n"
            f"Nodes generated: {nodes_created}\n"
            f"Recorded steps: {len(trace)}\n"
            f"Path cost: {path_cost if path_nodes else 'N/A'}\n"
            f"Path: {' → '.join(map(str, path_nodes)) if path_nodes else 'None'}"
        )

        self.trace = trace
        self.trace_index = 0
        self.step_info_var.set("Trace ready. Use Step or Play to visualise.")

        if self.trace:
            self._apply_step(self.trace[0])
            self.trace_index = 1

    def play_animation(self):
        if not self.trace:
            return
        self.playing = True
        self._animate()

    def pause_animation(self):
        self.playing = False

    def _animate(self):
        if not self.playing:
            return
        if self.trace_index >= len(self.trace):
            self.playing = False
            return
        self._apply_step(self.trace[self.trace_index])
        self.trace_index += 1
        self.after(self.speed_var.get(), self._animate)

    def step_once(self):
        if not self.trace or self.trace_index >= len(self.trace):
            return
        self._apply_step(self.trace[self.trace_index])
        self.trace_index += 1

    def reset_visualization(self, redraw=True):
        self.pause_animation()
        if redraw and self.problem:
            self._draw_problem()
        else:
            for node_id, item in self.node_items.items():
                self.canvas.itemconfig(item, fill=self.base_colors.get(node_id, self.COLOR_DEFAULT))
        for item in self.path_overlay_items:
            self.canvas.delete(item)
        self.path_overlay_items.clear()
        self.trace_index = 0
        self.step_info_var.set("Visualization reset.")

    # ----------------------------------------------------------------- Helpers
    def _on_speed_change(self, value):
        self.speed_var.set(int(float(value)))

    def _apply_step(self, step):
        # Reset node colours to baseline for this step.
        for node_id, item in self.node_items.items():
            self.canvas.itemconfig(item, fill=self.base_colors.get(node_id, self.COLOR_DEFAULT))

        explored = step.get("explored", [])
        for node_id in explored:
            if node_id == self.problem.origin or node_id in self.problem.destinations:
                continue
            self.canvas.itemconfig(self.node_items.get(node_id), fill=self.COLOR_EXPLORED)

        explored_forward = step.get("explored_forward", [])
        for node_id in explored_forward:
            if node_id == self.problem.origin or node_id in self.problem.destinations:
                continue
            self.canvas.itemconfig(self.node_items.get(node_id), fill=self.COLOR_EXPLORED)

        explored_backward = step.get("explored_backward", [])
        for node_id in explored_backward:
            if node_id == self.problem.origin or node_id in self.problem.destinations:
                continue
            self.canvas.itemconfig(self.node_items.get(node_id), fill=self.COLOR_EXPLORED_BACK)

        for node_id in step.get("frontier", []):
            if node_id == self.problem.origin or node_id in self.problem.destinations:
                continue
            self.canvas.itemconfig(self.node_items.get(node_id), fill=self.COLOR_FRONTIER)

        for node_id in step.get("frontier_forward", []):
            if node_id == self.problem.origin or node_id in self.problem.destinations:
                continue
            self.canvas.itemconfig(self.node_items.get(node_id), fill=self.COLOR_FRONTIER)

        for node_id in step.get("frontier_backward", []):
            if node_id == self.problem.origin or node_id in self.problem.destinations:
                continue
            self.canvas.itemconfig(self.node_items.get(node_id), fill=self.COLOR_FRONTIER_BACK)

        current = step.get("current")
        if current in self.node_items:
            self.canvas.itemconfig(self.node_items[current], fill=self.COLOR_CURRENT)

        self._maybe_highlight_path(step)
        self.step_info_var.set(self._describe_step(step))

    def _maybe_highlight_path(self, step):
        action = step.get("action")
        if action != "goal" or not self.result_summary.get("path"):
            return
        for item in self.path_overlay_items:
            self.canvas.delete(item)
        self.path_overlay_items.clear()
        path_nodes = self.result_summary["path"]
        for idx in range(len(path_nodes) - 1):
            start = path_nodes[idx]
            end = path_nodes[idx + 1]
            if start not in self.node_positions or end not in self.node_positions:
                continue
            x1, y1 = self.node_positions[start]
            x2, y2 = self.node_positions[end]
            line = self.canvas.create_line(x1, y1, x2, y2, fill=self.COLOR_PATH, width=4)
            self.path_overlay_items.append(line)

    def _describe_step(self, step):
        action = step.get("action", "")
        algo = step.get("algorithm", "")
        current = step.get("current", "—")
        frontier = step.get("frontier")
        if frontier is None:
            frontier = step.get("frontier_forward")
        explored = step.get("explored")
        if explored is None:
            explored = step.get("explored_forward")
        info = [f"Algorithm: {algo}", f"Action: {action}", f"Current node: {current}"]
        if frontier is not None:
            info.append(f"Frontier: {', '.join(map(str, frontier)) or '∅'}")
        if explored is not None:
            info.append(f"Explored: {', '.join(map(str, explored)) or '∅'}")
        if "depth_limit" in step:
            info.append(f"Depth limit: {step['depth_limit']}")
        if "path_cost" in step:
            info.append(f"Path cost so far: {step['path_cost']}")
        return "\n".join(info)

    def _compute_path_cost(self, path_nodes):
        if not path_nodes:
            return None
        cost = 0
        for idx in range(len(path_nodes) - 1):
            edge_cost = self.problem.edges.get((path_nodes[idx], path_nodes[idx + 1]))
            if edge_cost is None:
                return None
            cost += edge_cost
        return cost


def main():
    app = SearchVisualizer()
    app.mainloop()


if __name__ == "__main__":
    main()
