#!/usr/bin/env python3
"""
Search GUI (redesigned from scratch):
• Clean, informative layout
• Run and compare all 6 algorithms side-by-side
• Interactive graph preview and per-algorithm path overlay
• Safe shutdown when the window close (red cross) is clicked

Launch with: python search_gui.py
"""

import os
import sys
import threading
import time
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from src.parser import parse_problem
from src.search_algorithms import dfs, bfs, gbfs, astar, cus1, cus2


ALGO_FUNCS = {
    "DFS": dfs,
    "BFS": bfs,
    "GBFS": gbfs,
    "A*": astar,
    "CUS1": cus1,
    "CUS2": cus2,
}

ALGO_HELP = {
    "DFS": "Depth-first; memory efficient; not optimal; can go deep into dead-ends.",
    "BFS": "Breadth-first; optimal on unweighted graphs by steps; higher memory.",
    "GBFS": "Greedy best-first using Euclidean heuristic; fast but not optimal.",
    "A*": "f=g+h with Euclidean heuristic; often optimal and efficient.",
    "CUS1": "Iterative Deepening DFS; complete like BFS with low memory.",
    "CUS2": "Bidirectional A* (informed); expands from start and goal and meets in the middle.",
}


class SearchGUI(tk.Tk):
    """New compact GUI with comparison panel and canvas renderer (no matplotlib)."""

    def __init__(self):
        super().__init__()
        self.title("AI Search Visualizer")
        self.geometry("1200x800")
        self.configure(bg="#f5f5f5")
        try:
            self.state("zoomed")
        except Exception:
            pass

        # Core state
        self.problem = None
        self.problem_path = None
        self.results = {}  # algo -> metrics dict
        self.current_algo_to_draw = None
        self.draw_edge_costs = tk.BooleanVar(value=True)
        self.show_legend = tk.BooleanVar(value=True)
        self._run_thread = None
        self._stop_flag = threading.Event()

        # Animation state
        self.trace = []
        self.trace_index = 0
        self.playing = False
        self.anim_timer = None
        self.anim_speed = tk.IntVar(value=300)  # ms
        self.anim_algo = tk.StringVar(value="A*")
        self.anim_result_path = []
        # Thread-safe queue for trace steps from worker thread
        self.trace_queue = queue.Queue()


        self._build_layout()
        self._populate_test_files()
        
        # Start periodic check for trace steps from worker thread
        self._process_trace_queue()

        # Ensure hard exit on window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- Layout ----------
    def _build_layout(self):
        # Configure grid: main canvas area with sidebar
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

        # ===== MAIN: Canvas area (Graph + Tree side by side) =====
        canvas_container = tk.Frame(self, bg="#f5f5f5")
        canvas_container.grid(row=0, column=0, sticky="nsew", padx=(0, 1))
        canvas_container.columnconfigure(0, weight=1)
        canvas_container.columnconfigure(1, weight=1)
        canvas_container.rowconfigure(0, weight=1)
        
        # Left: Graph canvas
        graph_frame = tk.Frame(canvas_container, bg="#ffffff", relief="flat")
        graph_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 1))
        
        self.canvas = tk.Canvas(graph_frame, background="#ffffff", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._redraw_canvas())
        
        # Right: Tree canvas
        tree_frame = tk.Frame(canvas_container, bg="#ffffff", relief="flat")
        tree_frame.grid(row=0, column=1, sticky="nsew")
        
        self.tree_canvas = tk.Canvas(tree_frame, background="#fafafa", highlightthickness=0)
        self.tree_canvas.pack(fill="both", expand=True)
        self.tree_canvas.bind("<Configure>", lambda e: self._redraw_tree_canvas())

        # ===== SIDEBAR: Minimal Controls =====
        sidebar = tk.Frame(self, bg="#2c3e50", width=280)
        sidebar.grid(row=0, column=1, sticky="nsew")
        sidebar.grid_propagate(False)

        # Title
        title_frame = tk.Frame(sidebar, bg="#2c3e50")
        title_frame.pack(fill="x", pady=(20, 30))
        tk.Label(title_frame, text="Search Visualizer", font=("Segoe UI", 18, "bold"), 
                bg="#2c3e50", fg="#ecf0f1").pack()

        # File selection
        file_frame = tk.Frame(sidebar, bg="#2c3e50")
        file_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        tk.Label(file_frame, text="Test Case", font=("Segoe UI", 10, "bold"), 
                bg="#2c3e50", fg="#95a5a6", anchor="w").pack(fill="x", pady=(0, 8))
        
        self.file_var = tk.StringVar()
        self.file_combo = ttk.Combobox(file_frame, textvariable=self.file_var, state="readonly", 
                                      width=22, font=("Segoe UI", 9))
        self.file_combo.pack(fill="x", pady=(0, 6))
        self.file_combo.bind("<<ComboboxSelected>>", lambda e: self._load_problem())
        
        tk.Button(file_frame, text="Browse", command=self._browse_file, 
                 bg="#3498db", fg="white", relief="flat", padx=10, pady=4,
                 font=("Segoe UI", 9), cursor="hand2",
                 activebackground="#2980b9", activeforeground="white").pack(fill="x")
        
        self.file_info = tk.Label(file_frame, text="No file loaded", 
                                  fg="#7f8c8d", bg="#2c3e50", font=("Segoe UI", 8),
                                  wraplength=240, justify="left", anchor="w")
        self.file_info.pack(fill="x", pady=(6, 0))

        # Algorithm selection
        algo_frame = tk.Frame(sidebar, bg="#2c3e50")
        algo_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        tk.Label(algo_frame, text="Algorithm", font=("Segoe UI", 10, "bold"), 
                bg="#2c3e50", fg="#95a5a6", anchor="w").pack(fill="x", pady=(0, 8))
        
        algo_names = list(ALGO_FUNCS.keys())
        self.anim_algo_combo = ttk.Combobox(algo_frame, textvariable=self.anim_algo, 
                                           values=algo_names, state="readonly", 
                                           width=22, font=("Segoe UI", 9))
        self.anim_algo_combo.pack(fill="x")

        # Animation controls
        anim_frame = tk.Frame(sidebar, bg="#2c3e50")
        anim_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Control buttons
        btn_frame = tk.Frame(anim_frame, bg="#2c3e50")
        btn_frame.pack(fill="x", pady=(0, 12))
        
        self.play_btn = tk.Button(btn_frame, text="▶ Play", command=self._play_animation,
                                  bg="#27ae60", fg="white", relief="flat", padx=15, pady=10,
                                  font=("Segoe UI", 11, "bold"), cursor="hand2",
                                  activebackground="#229954", activeforeground="white")
        self.play_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))
        
        self.pause_btn = tk.Button(btn_frame, text="⏸", command=self._pause_animation,
                                   bg="#e74c3c", fg="white", relief="flat", padx=10, pady=10,
                                   font=("Segoe UI", 11), cursor="hand2",
                                   activebackground="#c0392b", activeforeground="white")
        self.pause_btn.pack(side="left", padx=(0, 4))
        
        self.reset_btn = tk.Button(btn_frame, text="⏹", command=self._reset_animation,
                                   bg="#95a5a6", fg="white", relief="flat", padx=10, pady=10,
                                   font=("Segoe UI", 11), cursor="hand2",
                                   activebackground="#7f8c8d", activeforeground="white")
        self.reset_btn.pack(side="left")
        
        # Speed control
        speed_frame = tk.Frame(anim_frame, bg="#2c3e50")
        speed_frame.pack(fill="x", pady=(0, 8))
        
        tk.Label(speed_frame, text="Speed", font=("Segoe UI", 9), 
                bg="#2c3e50", fg="#95a5a6").pack(anchor="w", pady=(0, 4))
        self.anim_speed_scale = ttk.Scale(speed_frame, from_=50, to=1500, orient="horizontal",
                                          command=lambda v: self.anim_speed.set(int(float(v))))
        self.anim_speed_scale.set(self.anim_speed.get())
        self.anim_speed_scale.pack(fill="x")
        
        # Step slider
        step_frame = tk.Frame(anim_frame, bg="#2c3e50")
        step_frame.pack(fill="x", pady=(0, 12))
        
        step_info_frame = tk.Frame(step_frame, bg="#2c3e50")
        step_info_frame.pack(fill="x", pady=(0, 6))
        tk.Label(step_info_frame, text="Step", font=("Segoe UI", 9), 
                bg="#2c3e50", fg="#95a5a6").pack(side="left")
        self.step_info_label = tk.Label(step_info_frame, text="0/0", font=("Segoe UI", 9, "bold"),
                                        bg="#2c3e50", fg="#ecf0f1")
        self.step_info_label.pack(side="right")
        
        self.anim_step_var = tk.IntVar(value=0)
        self.anim_step_slider = ttk.Scale(step_frame, from_=0, to=0, orient="horizontal",
                                          variable=self.anim_step_var, command=self._on_anim_slider)
        self.anim_step_slider.configure(state="disabled")
        self.anim_step_slider.pack(fill="x")

        # Status
        self.status = tk.Label(sidebar, text="Ready", anchor="w", padx=20, pady=10,
                               bg="#34495e", fg="#ecf0f1", font=("Segoe UI", 9))
        self.status.pack(side="bottom", fill="x")

    # ---------- File ops ----------
    def _populate_test_files(self):
        test_dir = os.path.join(os.getcwd(), "test_cases")
        options = []
        if os.path.isdir(test_dir):
            for name in sorted(os.listdir(test_dir)):
                if name.lower().endswith(".txt"):
                    options.append(os.path.join("test_cases", name))
        self.file_combo.configure(values=options)
        if options:
            self.file_combo.current(0)
            self._load_problem()

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select test case",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=os.getcwd(),
        )
        if path:
            rel = os.path.relpath(path, os.getcwd())
            current = list(self.file_combo["values"])
            if rel not in current:
                current.append(rel)
                self.file_combo.configure(values=current)
            self.file_combo.set(rel)
            self._load_problem()

    def _load_problem(self):
        path = self.file_var.get()
        if not path:
            return
        full = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
        try:
            self.problem = parse_problem(full)
            self.problem_path = full
            n_nodes = len(self.problem.nodes)
            n_edges = len(self.problem.edges)
            self.file_info.configure(text=f"{os.path.basename(path)} — {n_nodes} nodes, {n_edges} edges")
            self.current_algo_to_draw = None
            # reset animation state
            self._reset_animation(clear_only=True)
            self._redraw_canvas()
            self._redraw_tree_canvas()
            self._set_status("Problem loaded.")
        except Exception as e:
            messagebox.showerror("Failed to load", str(e))

    # ---------- Draw ----------
    def _world_bounds(self):
        if not self.problem or not self.problem.nodes:
            return (0, 1, 0, 1)
        xs = [x for (x, _) in self.problem.nodes.values()]
        ys = [y for (_, y) in self.problem.nodes.values()]
        padding = 1
        return (min(xs) - padding, max(xs) + padding, min(ys) - padding, max(ys) + padding)

    def _world_to_canvas(self, x, y, bbox):
        x_min, x_max, y_min, y_max = bbox
        cw = max(self.canvas.winfo_width(), 1)
        ch = max(self.canvas.winfo_height(), 1)
        if x_max == x_min:
            sx = 1.0
        else:
            sx = (cw - 40) / (x_max - x_min)
        if y_max == y_min:
            sy = 1.0
        else:
            sy = (ch - 40) / (y_max - y_min)
        # Keep aspect by using same scale
        s = min(sx, sy)
        ox = 20 - x_min * s + (cw - (x_max - x_min) * s - 40) / 2
        oy = 20 - y_min * s + (ch - (y_max - y_min) * s - 40) / 2
        cx = ox + x * s
        cy = ch - (oy + y * s)  # invert Y for canvas
        return cx, cy

    def _redraw_canvas(self):
        self.canvas.delete("all")
        if not self.problem:
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text="Load a test case to view the graph",
                fill="#666",
                font=("Segoe UI", 14, "italic"),
            )
            return

        bbox = self._world_bounds()

        # Draw edges (with arrows and costs)
        # First pass: collect edge positions to avoid overlaps
        edge_info = {}
        for (u, v), cost in self.problem.edges.items():
            if u not in self.problem.nodes or v not in self.problem.nodes:
                continue
            x1, y1 = self.problem.nodes[u]
            x2, y2 = self.problem.nodes[v]
            c1 = self._world_to_canvas(x1, y1, bbox)
            c2 = self._world_to_canvas(x2, y2, bbox)
            
            # Check if reverse edge exists to determine offset
            has_reverse = (v, u) in self.problem.edges
            edge_key = tuple(sorted([u, v]))  # Use sorted tuple as key for bidirectional edges
            
            if edge_key not in edge_info:
                edge_info[edge_key] = []
            edge_info[edge_key].append(((u, v), cost, c1, c2, has_reverse))
        
        # Draw edges and labels with smart positioning
        for edge_key, edges_list in edge_info.items():
            for idx, ((u, v), cost, c1, c2, has_reverse) in enumerate(edges_list):
                self.canvas.create_line(*c1, *c2, fill="#e0e0e0", width=1.5, arrow="last", arrowshape=(8, 10, 3))
                
                # Draw edge cost label with smart offset
                dx = c2[0] - c1[0]
                dy = c2[1] - c1[1]
                length = (dx*dx + dy*dy) ** 0.5 or 1.0
                # Position at midpoint along edge, slightly offset along the edge for bidirectional
                t = 0.55 if (has_reverse and idx == 0) else 0.45 if (has_reverse and len(edges_list) > 1) else 0.5
                px = c1[0] + dx * t
                py = c1[1] + dy * t
                # Perpendicular offset to avoid overlapping the line
                nx = -dy / length
                ny = dx / length
                # For bidirectional edges, offset more to separate them
                if has_reverse and len(edges_list) > 1:
                    # First edge goes to one side, second goes to opposite
                    side = 1 if idx == 0 else -1
                    off = 18 * side  # Larger offset for bidirectional
                else:
                    # Single direction or first edge
                    side = 1 if u < v else -1
                    off = 14 * side
                lx = px + nx * off
                ly = py + ny * off
                # Draw cost label
                text_id = self.canvas.create_text(lx, ly, text=str(cost), fill="#666", font=("Segoe UI", 8))
                bx1, by1, bx2, by2 = self.canvas.bbox(text_id)
                pad = 3
                rect_id = self.canvas.create_rectangle(bx1 - pad, by1 - pad, bx2 + pad, by2 + pad, 
                                                      fill="#ffffff", outline="#e0e0e0", width=1)
                self.canvas.tag_lower(rect_id)
                self.canvas.tag_raise(text_id)

        # Draw final path if animation completed
        if self.anim_result_path and len(self.anim_result_path) >= 2 and not self.trace:
            for i in range(len(self.anim_result_path) - 1):
                u, v = self.anim_result_path[i], self.anim_result_path[i + 1]
                if u in self.problem.nodes and v in self.problem.nodes:
                    x1, y1 = self.problem.nodes[u]
                    x2, y2 = self.problem.nodes[v]
                    c1 = self._world_to_canvas(x1, y1, bbox)
                    c2 = self._world_to_canvas(x2, y2, bbox)
                    self.canvas.create_line(*c1, *c2, fill="#27ae60", width=3)

        # Draw nodes
        for nid, (x, y) in self.problem.nodes.items():
            cx, cy = self._world_to_canvas(x, y, bbox)
            r = 16
            if nid == self.problem.origin:
                fill, outline = "#34a853", "#0f9d58"
            elif nid in self.problem.destinations:
                fill, outline = "#ea4335", "#c5221f"
            else:
                fill, outline = "#80868b", "#5f6368"
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline=outline, width=2)
            self.canvas.create_text(cx, cy, text=str(nid), fill="#ffffff", font=("Segoe UI", 10, "bold"))

        # If in animation mode and we have a step, overlay it
        if self.trace and 0 <= self.trace_index < len(self.trace):
            self._draw_step_on_canvas(self.trace[self.trace_index])

        # Legend overlay (simplified, always visible)
        self._draw_legend()

    # ---------- Run / Compare ----------
    def _run_selected(self):
        to_run = [name for name, var in self.selected_algos.items() if var.get()]
        if not to_run:
            messagebox.showinfo("No algorithms", "Please select at least one algorithm to run.")
            return
        self._start_run(to_run)

    def _run_all(self):
        self._start_run(list(ALGO_FUNCS.keys()))

    def _start_run(self, algo_list):
        if not self.problem:
            messagebox.showinfo("No problem", "Load a test case first.")
            return
        if self._run_thread and self._run_thread.is_alive():
            messagebox.showwarning("Busy", "A run is already in progress.")
            return

        self._stop_flag.clear()
        self.results.clear()
        self._refresh_table()
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", "Running algorithms...\n")
        self.summary_text.configure(state="disabled")
        self._set_status("Running...")

        def worker():
            try:
                for name in algo_list:
                    if self._stop_flag.is_set():
                        break
                    fn = ALGO_FUNCS[name]
                    t0 = time.perf_counter()
                    try:
                        result = fn(self.problem, observer=None)
                    except Exception as e:
                        err_msg = str(e)
                        self.after(0, lambda n=name, msg=err_msg: messagebox.showerror(f"Error in {n}", f"Algorithm {n} failed:\n{msg}"))
                        result = None
                    t1 = time.perf_counter()

                    if not result:
                        metrics = {
                            "goal": None,
                            "nodes": 0,
                            "path": [],
                            "cost": None,
                            "time_ms": (t1 - t0) * 1000,
                            "trace": 0,
                        }
                    else:
                        goal, nodes_created, path_str = result
                        path_nodes = [int(tok) for tok in path_str.split()] if path_str else []
                        cost = self._compute_path_cost(path_nodes)
                        metrics = {
                            "goal": goal,
                            "nodes": nodes_created,
                            "path": path_nodes,
                            "cost": cost,
                            "time_ms": (t1 - t0) * 1000,
                            "trace": 0,  # no observer in compare mode
                        }
                    self.results[name] = metrics
                    self.after(0, self._refresh_table)

                self.after(0, self._update_summary)
                self.after(0, lambda: self._set_status("Done."))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: messagebox.showerror("Runtime Error", f"An error occurred while running algorithms:\n{msg}"))
                self.after(0, lambda msg=err_msg: self._set_status(f"Error: {msg}"))

        self._run_thread = threading.Thread(target=worker, daemon=True)
        self._run_thread.start()

    def _update_summary(self):
        if not self.results:
            return
        # Find winners per metric (smaller is better for time, nodes, cost; larger for path len sometimes not desired)
        best_time = min((v["time_ms"], k) for k, v in self.results.items()) if self.results else (None, None)
        best_nodes = min(((v["nodes"], k) for k, v in self.results.items() if v["nodes"] is not None), default=(None, None))
        # Cost can be None when path invalid; filter
        costs = [(v["cost"], k) for k, v in self.results.items() if v["cost"] is not None]
        best_cost = min(costs) if costs else (None, None)

        lines = []
        lines.append("Summary of winners (lower is better):")
        if best_time[1] is not None:
            lines.append(f"• Fastest: {best_time[1]} ({best_time[0]:.3f} ms)")
        if best_nodes[1] is not None:
            lines.append(f"• Least Nodes Created: {best_nodes[1]} ({best_nodes[0]})")
        if best_cost[1] is not None:
            lines.append(f"• Lowest Path Cost: {best_cost[1]} ({best_cost[0]})")

        # Add per-algorithm short lines
        lines.append("\nPer-algorithm:")
        for name in ALGO_FUNCS:
            if name in self.results:
                r = self.results[name]
                goal = r["goal"] if r["goal"] is not None else "None"
                cost = r["cost"] if r["cost"] is not None else "—"
                lines.append(f"- {name}: goal={goal}, cost={cost}, nodes={r['nodes']}, time={r['time_ms']:.2f} ms")

        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert("1.0", "\n".join(lines))
        self.summary_text.configure(state="disabled")

    def _refresh_table(self):
        for i in self.table.get_children():
            self.table.delete(i)
        for name in ALGO_FUNCS:
            if name not in self.results:
                continue
            r = self.results[name]
            goal = r["goal"] if r["goal"] is not None else "None"
            cost = r["cost"] if r["cost"] is not None else "—"
            path_len = len(r["path"]) if r["path"] else 0
            path_str = " → ".join(map(str, r["path"])) if r["path"] else "—"
            self.table.insert("", tk.END, iid=name, values=(name, goal, cost, path_len, path_str, r["nodes"], f"{r['time_ms']:.2f}", r["trace"]))

    def _on_table_select(self, _):
        sel = self.table.selection()
        if not sel:
            return
        algo = sel[0]
        if algo in self.results:
            self.current_algo_to_draw = algo
            self._redraw_canvas()
            # Status includes path preview
            path = self.results[algo].get("path") or []
            self._set_status(f"Selected {algo}. Path: {' '.join(map(str, path)) if path else '—'}")

    # ---------- Utils ----------
    def _compute_path_cost(self, path_nodes):
        if not self.problem or len(path_nodes) < 2:
            return None
        cost = 0
        for i in range(len(path_nodes) - 1):
            edge_cost = self.problem.edges.get((path_nodes[i], path_nodes[i + 1]))
            if edge_cost is None:
                return None
            cost += edge_cost
        return cost

    # ---------- Animation mode ----------
    def _run_animated(self):
        if not self.problem:
            messagebox.showinfo("No problem", "Load a test case first.")
            return
        if self._run_thread and self._run_thread.is_alive():
            messagebox.showwarning("Busy", "A run is already in progress.")
            return
        algo = self.anim_algo.get()
        if algo not in ALGO_FUNCS:
            messagebox.showerror("Unknown algorithm", algo)
            return

        # reset state
        self._pause_animation()
        self.trace = []
        self.trace_index = 0
        self.anim_result_path = []
        self.anim_step_slider.configure(state="disabled", to=0)
        self.current_algo_to_draw = None
        self._redraw_canvas()
        self._set_status(f"Running {algo}...")

        def observer(event):
            # snapshot mutable structures
            snap = {}
            for k, v in event.items():
                if isinstance(v, set):
                    snap[k] = sorted(v)
                elif isinstance(v, (list, tuple)):
                    snap[k] = list(v)
                else:
                    snap[k] = v
            # Put in queue for thread-safe access from worker thread
            self.trace_queue.put(snap)

        def worker():
            try:
                fn = ALGO_FUNCS[algo]
                t0 = time.perf_counter()
                try:
                    result = fn(self.problem, observer=observer)
                except Exception as e:
                    err_msg = str(e)
                    self.after(0, lambda msg=err_msg, alg=algo: messagebox.showerror(f"Error in {alg}", f"Algorithm {alg} failed:\n{msg}"))
                    self.after(0, lambda msg=err_msg: self._set_status(f"Error: {msg}"))
                    return
                t1 = time.perf_counter()
                
                if result:
                    goal, nodes_created, path_str = result
                    path_nodes = [int(tok) for tok in path_str.split()] if path_str else []
                    self.anim_result_path = path_nodes
                    
                    # Store result in results dict for table display
                    cost = self._compute_path_cost(path_nodes)
                    metrics = {
                        "goal": goal,
                        "nodes": nodes_created,
                        "path": path_nodes,
                        "cost": cost,
                        "time_ms": (t1 - t0) * 1000,
                        "trace": len(self.trace),
                    }
                self.results[algo] = metrics
                self.after(0, self._refresh_table)
                
                # Mark that algorithm finished - trace queue processor will check when queue is empty
                self.trace_queue.put(None)  # Sentinel to mark completion
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: messagebox.showerror("Runtime Error", f"An error occurred while running animation:\n{msg}"))
                self.after(0, lambda msg=err_msg: self._set_status(f"Error: {msg}"))

        self._stop_flag.clear()
        self._run_thread = threading.Thread(target=worker, daemon=True)
        self._run_thread.start()

    def _process_trace_queue(self):
        """Periodically process trace steps from the queue (thread-safe)."""
        try:
            while True:
                step = self.trace_queue.get_nowait()
                if step is None:
                    # Sentinel - algorithm finished
                    self.after(100, self._check_animation_complete)
                else:
                    self._append_trace_step(step)
        except queue.Empty:
            pass
        # Check again soon
        self.after(10, self._process_trace_queue)
    
    def _check_animation_complete(self):
        """Check if animation is ready after algorithm completes."""
        # Process any remaining items in queue
        self._process_trace_queue()
        # Now check if we have trace steps
        self._on_animation_ready()
    
    def _append_trace_step(self, step):
        self.trace.append(step)
        # Update slider range
        if len(self.trace) == 1:
            self.anim_step_slider.configure(state="normal")
        self.anim_step_slider.configure(to=max(0, len(self.trace) - 1))
        # Update step info
        self._update_step_info()
        # Draw first step immediately
        if len(self.trace) == 1:
            self.trace_index = 0
            self._redraw_canvas()
    
    def _update_step_info(self):
        """Update the step information display in sidebar."""
        if hasattr(self, 'step_info_label'):
            if self.trace:
                current = self.trace_index + 1
                total = len(self.trace)
                self.step_info_label.configure(text=f"{current}/{total}")
            else:
                self.step_info_label.configure(text="0/0")
    
    def _on_animation_ready(self):
        # Process any pending GUI updates to ensure trace steps are appended
        self.update_idletasks()
        # Give a small delay for any remaining callbacks
        def check_ready(count=0):
            total = len(self.trace)
            if total > 0:
                self._set_status(f"Ready: {total} steps")
                self.anim_step_slider.configure(to=max(0, total - 1))
                # Auto-start animation
                self.playing = True
                self._tick_animation()
            elif count < 10:  # Try up to 10 times (1 second total)
                # If still no trace, wait a bit more for callbacks
                next_count = count + 1
                self.after(100, lambda c=next_count: check_ready(c))
            else:
                # If no trace after waiting, something went wrong
                self._set_status(f"No trace generated")
        check_ready()

    def _play_animation(self):
        # Process any pending GUI updates first
        self.update_idletasks()
        
        # If no trace, automatically run the algorithm first
        if not self.trace:
            if not self.problem:
                messagebox.showinfo("No problem", "Load a test case first.")
                return
            if self._run_thread and self._run_thread.is_alive():
                messagebox.showinfo("Please wait", "Algorithm is still running. Please wait for it to complete.")
                return
            
            # Auto-run the selected algorithm
            self._run_animated()
            return
        
        # Start playing the animation
        self.playing = True
        self._tick_animation()

    def _pause_animation(self):
        self.playing = False
        if self.anim_timer is not None:
            try:
                self.after_cancel(self.anim_timer)
            except Exception:
                pass
            self.anim_timer = None

    def _reset_animation(self, clear_only=False):
        self._pause_animation()
        self.trace_index = 0
        if not clear_only:
            self.trace = []
            self.anim_result_path = []
            self.anim_step_slider.configure(state="disabled", to=0)
        self._update_step_info()
        self._redraw_canvas()
        self._redraw_tree_canvas()

    def _tick_animation(self):
        if not self.playing:
            return
        if not self.trace:
            self.playing = False
            return
        if self.trace_index >= len(self.trace):
            self.playing = False
            return
        self._redraw_canvas()
        self._redraw_tree_canvas()
        self.anim_step_var.set(self.trace_index)
        self._update_step_info()
        self.trace_index += 1
        self.anim_timer = self.after(self.anim_speed.get(), self._tick_animation)

    def _on_anim_slider(self, _):
        if not self.trace:
            return
        self._pause_animation()
        idx = int(float(self.anim_step_var.get()))
        idx = max(0, min(idx, len(self.trace) - 1))
        self.trace_index = idx
        self._update_step_info()
        self._redraw_canvas()
        self._redraw_tree_canvas()

    def _draw_step_on_canvas(self, step):
        # Overlay current step information: explored/frontier/current and goal path if present
        if not self.problem:
            return
        bbox = self._world_bounds()
        
        # Draw path from origin to current node for better tracking
        current = step.get("current")
        path = step.get("path", [])
        if path and len(path) >= 2:
            # Highlight the path taken so far
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                if u in self.problem.nodes and v in self.problem.nodes:
                    x1, y1 = self.problem.nodes[u]
                    x2, y2 = self.problem.nodes[v]
                    c1 = self._world_to_canvas(x1, y1, bbox)
                    c2 = self._world_to_canvas(x2, y2, bbox)
                    # Highlight the edge being traversed
                    if i == len(path) - 2:  # Last edge (to current node)
                        self.canvas.create_line(*c1, *c2, fill="#27ae60", width=4, arrow="last", arrowshape=(12, 15, 4))
                    else:
                        self.canvas.create_line(*c1, *c2, fill="#27ae60", width=3)
        
        # Draw final path if goal reached
        if step.get("action") == "goal" and self.anim_result_path and len(self.anim_result_path) >= 2:
            for i in range(len(self.anim_result_path) - 1):
                u, v = self.anim_result_path[i], self.anim_result_path[i + 1]
                if u in self.problem.nodes and v in self.problem.nodes:
                    x1, y1 = self.problem.nodes[u]
                    x2, y2 = self.problem.nodes[v]
                    c1 = self._world_to_canvas(x1, y1, bbox)
                    c2 = self._world_to_canvas(x2, y2, bbox)
                    self.canvas.create_line(*c1, *c2, fill="#2ecc71", width=4)
        
        def draw_nodes(ids, fill, outline, text_color="#ffffff"):
            for nid in ids:
                if nid in self.problem.nodes:
                    x, y = self.problem.nodes[nid]
                    cx, cy = self._world_to_canvas(x, y, bbox)
                    r = 18
                    self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=fill, outline=outline, width=3)
                    self.canvas.create_text(cx, cy, text=str(nid), fill=text_color, font=("Segoe UI", 10, "bold"))

        explored = set(step.get("explored", [])) | set(step.get("explored_forward", []))
        explored_back = set(step.get("explored_backward", []))
        frontier = set(step.get("frontier", [])) | set(step.get("frontier_forward", []))
        frontier_back = set(step.get("frontier_backward", []))
        current = step.get("current")

        # Frontier overlays
        draw_nodes(frontier, fill="#fdd663", outline="#fbbc04", text_color="#202124")
        draw_nodes(frontier_back, fill="#ff8a65", outline="#d84315")
        # Explored overlays
        draw_nodes(explored, fill="#5e97f6", outline="#1a73e8")
        draw_nodes(explored_back, fill="#ba68c8", outline="#8e24aa")
        # Current node - make it very prominent with pulsing effect
        if current in self.problem.nodes:
            x, y = self.problem.nodes[current]
            cx, cy = self._world_to_canvas(x, y, bbox)
            # Outer glow rings (multiple for pulsing effect)
            for r_glow in [30, 26]:
                self.canvas.create_oval(cx - r_glow, cy - r_glow, cx + r_glow, cy + r_glow, 
                                       outline="#f9ab00", width=2, dash=(4, 4))
            # Main node - larger and more prominent
            r = 25
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#f9ab00", outline="#e37400", width=6)
            self.canvas.create_text(cx, cy, text=str(current), fill="#ffffff", font=("Segoe UI", 14, "bold"))
        
        # Draw step counter in top-left corner
        step_num = self.trace_index + 1
        total_steps = len(self.trace)
        step_text = f"Step {step_num}/{total_steps}"
        self.canvas.create_rectangle(10, 10, 120, 40, fill="#2c3e50", outline="#34495e", width=2)
        self.canvas.create_text(65, 25, text=step_text, fill="#ecf0f1", font=("Segoe UI", 11, "bold"))
        
        # Draw action type indicator
        action = step.get("action", "expand")
        action_colors = {
            "expand": "#3498db",
            "goal": "#2ecc71",
        }
        action_color = action_colors.get(action, "#95a5a6")
        action_text = action.upper() if action == "goal" else "Exploring"
        self.canvas.create_rectangle(130, 10, 220, 40, fill=action_color, outline="#34495e", width=2)
        self.canvas.create_text(175, 25, text=action_text, fill="#ffffff", font=("Segoe UI", 10, "bold"))

    def _draw_legend(self):
        if not self.problem:
            return
        # Draw a compact legend in a corner that minimizes overlap with node positions
        w = max(self.canvas.winfo_width(), 1)
        h = max(self.canvas.winfo_height(), 1)
        pad = 10

        # Legend dimensions (slightly smaller for laptops)
        box_w = 200
        row_h = 18
        rows = 8
        box_h = 14 + rows * row_h + 10  # top padding + rows + bottom padding

        # Compute candidate corners: top-right, top-left, bottom-right, bottom-left
        candidates = [
            (w - box_w - pad, pad),
            (pad, pad),
            (w - box_w - pad, h - box_h - pad),
            (pad, h - box_h - pad),
        ]

        # Estimate node canvas positions to avoid covering them
        bbox = self._world_bounds()
        nodes_xy = []
        if self.problem and self.problem.nodes:
            for nid, (x, y) in self.problem.nodes.items():
                cx, cy = self._world_to_canvas(x, y, bbox)
                nodes_xy.append((cx, cy))

        def overlaps(x0, y0):
            x1 = x0 + box_w
            y1 = y0 + box_h
            # consider a radius around node labels
            node_r = 20
            for cx, cy in nodes_xy:
                if (x0 - node_r) <= cx <= (x1 + node_r) and (y0 - node_r) <= cy <= (y1 + node_r):
                    return True
            return False

        # Pick first non-overlapping position, or default to top-right
        x0, y0 = candidates[0]
        for cand in candidates:
            if not overlaps(*cand):
                x0, y0 = cand
                break

        x1 = x0 + box_w
        y1 = y0 + box_h

        # background
        self.canvas.create_rectangle(x0, y0, x1, y1, fill="#ffffff", outline="#cccccc")

        def item(y, color_fill, color_outline, label, is_line=False):
            cx = x0 + 16
            cy = y
            if is_line:
                self.canvas.create_line(cx - 12, cy, cx + 12, cy, fill=color_fill, width=3)
            else:
                self.canvas.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill=color_fill, outline=color_outline, width=2)
            self.canvas.create_text(cx + 22, cy, text=label, anchor="w", fill="#202124", font=("Segoe UI", 9))

        y = y0 + 14
        item(y, "#34a853", "#0f9d58", "Start")
        y += row_h
        item(y, "#ea4335", "#c5221f", "Goal")
        y += row_h
        item(y, "#fdd663", "#fbbc04", "Frontier")
        y += row_h
        item(y, "#5e97f6", "#1a73e8", "Explored")
        y += row_h
        item(y, "#f9ab00", "#e37400", "Current")
        y += row_h
        item(y, "#34a853", "#34a853", "Path", is_line=True)
        y += row_h
        item(y, "#ff8a65", "#d84315", "Frontier (back)")
        y += row_h
        item(y, "#ba68c8", "#8e24aa", "Explored (back)")
    
    def _redraw_tree_canvas(self):
        """Draw the search tree structure."""
        self.tree_canvas.delete("all")
        
        if not self.problem:
            self.tree_canvas.create_text(
                self.tree_canvas.winfo_width() // 2,
                self.tree_canvas.winfo_height() // 2,
                text="Load a test case to see search tree",
                fill="#999",
                font=("Segoe UI", 12, "italic"),
            )
            return
        
        # Get animation state if available
        explored = set()
        frontier = set()
        current = None
        
        if self.trace and 0 <= self.trace_index < len(self.trace):
            step = self.trace[self.trace_index]
            explored = set(step.get("explored", [])) | set(step.get("explored_forward", []))
            frontier = set(step.get("frontier", [])) | set(step.get("frontier_forward", []))
            current = step.get("current")
        
        # Build complete tree from graph using BFS from origin
        origin = self.problem.origin
        visited = {origin}
        tree_edges = []
        node_parents = {origin: None}
        queue = [origin]
        
        while queue:
            parent = queue.pop(0)
            neighbors = self.problem.get_neighbors(parent)
            neighbors.sort(key=lambda x: x[0])
            
            for child, _ in neighbors:
                if child not in visited:
                    visited.add(child)
                    node_parents[child] = parent
                    tree_edges.append((parent, child))
                    queue.append(child)
        
        # Calculate depths
        node_depths = {}
        
        def calc_depth(node):
            if node in node_depths:
                return node_depths[node]
            parent = node_parents.get(node)
            if parent is None:
                node_depths[node] = 0
            else:
                node_depths[node] = calc_depth(parent) + 1
            return node_depths[node]
        
        for node in visited:
            calc_depth(node)
        
        # Group by depth
        levels = {}
        for node, depth in node_depths.items():
            if depth not in levels:
                levels[depth] = []
            levels[depth].append(node)
        
        # Sort nodes at each level
        for depth in levels:
            levels[depth].sort()
        
        # Calculate positions
        canvas_w = max(400, self.tree_canvas.winfo_width())
        canvas_h = max(400, self.tree_canvas.winfo_height())
        
        max_depth = max(levels.keys()) if levels else 0
        v_spacing = min(80, max(50, (canvas_h - 80) // (max_depth + 1))) if max_depth > 0 else 80
        
        node_positions = {}
        for depth, nodes in levels.items():
            y = 40 + depth * v_spacing
            count = len(nodes)
            if count == 1:
                node_positions[nodes[0]] = (canvas_w // 2, y)
            else:
                spacing = min(canvas_w // (count + 1), 120)
                start_x = (canvas_w - (count - 1) * spacing) // 2
                for i, node in enumerate(nodes):
                    x = start_x + i * spacing
                    node_positions[node] = (x, y)
        
        # Draw edges
        for parent, child in tree_edges:
            if parent in node_positions and child in node_positions:
                px, py = node_positions[parent]
                cx, cy = node_positions[child]
                self.tree_canvas.create_line(px, py, cx, cy, fill="#d0d0d0", width=1.5,
                                           arrow="last", arrowshape=(6, 8, 2), smooth=True)
        
        # Draw nodes - color based on animation state
        for node, (x, y) in node_positions.items():
            r = 14
            
            # Determine color based on animation state
            if current and node == current:
                fill, outline = "#f9ab00", "#e37400"  # Current (orange)
                text_color = "#ffffff"
            elif node in explored:
                fill, outline = "#5e97f6", "#1a73e8"  # Explored (blue)
                text_color = "#ffffff"
            elif node in frontier:
                fill, outline = "#fdd663", "#fbbc04"  # Frontier (yellow)
                text_color = "#202124"
            elif node == self.problem.origin:
                fill, outline = "#27ae60", "#229954"  # Start (green)
                text_color = "#ffffff"
            elif node in self.problem.destinations:
                fill, outline = "#e74c3c", "#c0392b"  # Goal (red)
                text_color = "#ffffff"
            else:
                fill, outline = "#e8eaed", "#bdc3c7"  # Regular (light gray)
                text_color = "#34495e"
            
            self.tree_canvas.create_oval(x - r, y - r, x + r, y + r, fill=fill, outline=outline, width=2)
            self.tree_canvas.create_text(x, y, text=str(node), fill=text_color, font=("Segoe UI", 9, "bold"))
    
    def _export_csv(self):
        if not self.results:
            messagebox.showinfo("No results", "Run algorithms first.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], title="Export results to CSV")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("Algorithm,Goal,Cost,PathLen,Nodes,Time(ms)\n")
                for name, r in self.results.items():
                    goal = r["goal"] if r["goal"] is not None else "None"
                    cost = r["cost"] if r["cost"] is not None else ""
                    path_len = len(r["path"]) if r["path"] else 0
                    f.write(f"{name},{goal},{cost},{path_len},{r['nodes']},{r['time_ms']:.3f}\n")
            messagebox.showinfo("Exported", f"Saved results to {path}")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    def _set_status(self, text):
        self.status.configure(text=text)

    def _on_close(self):
        # Signal background work to stop and exit cleanly
        try:
            self._stop_flag.set()
            if self._run_thread and self._run_thread.is_alive():
                # Give it a short moment to stop
                self._run_thread.join(timeout=0.5)
        except Exception:
            pass
        try:
            self._pause_animation()
            self.destroy()
        finally:
            # Ensure process termination even if threads linger
            os._exit(0)


def main():
    app = SearchGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
