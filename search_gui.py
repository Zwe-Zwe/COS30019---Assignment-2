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
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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
        self.title("AI Search Visualizer — Compare Algorithms")
        self.geometry("1400x900")
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

        # Selection state
        self.selected_algos = {name: tk.BooleanVar(value=name in ("A*", "BFS")) for name in ALGO_FUNCS}

        self._build_layout()
        self._populate_test_files()

        # Ensure hard exit on window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- Layout ----------
    def _build_layout(self):
        # Narrower left pane, give most space to the graph/table on the right
        LEFT_WIDTH = 380
        self.columnconfigure(0, weight=0, minsize=LEFT_WIDTH)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # Left control panel
        left = ttk.Frame(self, padding=10)
        left.grid(row=0, column=0, sticky="ns")
        # Keep left panel from expanding beyond intended width
        left.grid_propagate(False)

        # File chooser
        file_grp = ttk.LabelFrame(left, text="Test Case")
        file_grp.pack(fill="x", pady=(0, 10))

        self.file_var = tk.StringVar()
        # Narrower combo to prevent left pane from growing too wide
        self.file_combo = ttk.Combobox(file_grp, textvariable=self.file_var, state="readonly", width=32)
        self.file_combo.pack(side="left", padx=(8, 4), pady=8)
        self.file_combo.bind("<<ComboboxSelected>>", lambda e: self._load_problem())

        ttk.Button(file_grp, text="Browse", command=self._browse_file).pack(side="left", padx=(4, 8), pady=8)

        self.file_info = ttk.Label(file_grp, text="No file loaded", foreground="#555")
        self.file_info.pack(fill="x", padx=8, pady=(0, 8))

        # Algorithm selection
        algo_grp = ttk.LabelFrame(left, text="Algorithms")
        algo_grp.pack(fill="x", pady=(0, 10))

        for name in ALGO_FUNCS:
            row = ttk.Frame(algo_grp)
            row.pack(fill="x", padx=6, pady=2)
            ttk.Checkbutton(row, text=name, variable=self.selected_algos[name]).pack(side="left")
            # Wrap long help text to keep left panel compact
            ttk.Label(row, text=ALGO_HELP[name], foreground="#666", wraplength=260, justify="left").pack(side="left", padx=6)

        opt_row = ttk.Frame(algo_grp)
        opt_row.pack(fill="x", padx=6, pady=(6, 4))
        ttk.Checkbutton(opt_row, text="Show edge costs", variable=self.draw_edge_costs, command=self._redraw_canvas).pack(side="left")
        ttk.Checkbutton(opt_row, text="Show legend", variable=self.show_legend, command=self._redraw_canvas).pack(side="left", padx=(10, 0))

        btn_row = ttk.Frame(algo_grp)
        btn_row.pack(fill="x", padx=6, pady=(4, 8))
        ttk.Button(btn_row, text="Run Selected", command=self._run_selected).pack(side="left", expand=True, fill="x")
        ttk.Button(btn_row, text="Run All", command=self._run_all).pack(side="left", padx=6, expand=True, fill="x")

        # Animation controls
        anim_grp = ttk.LabelFrame(left, text="Animation")
        anim_grp.pack(fill="x", pady=(0, 10))

        anim_top = ttk.Frame(anim_grp)
        anim_top.pack(fill="x", padx=6, pady=(6, 4))
        ttk.Label(anim_top, text="Algorithm:").pack(side="left")
        algo_names = list(ALGO_FUNCS.keys())
        self.anim_algo_combo = ttk.Combobox(anim_top, textvariable=self.anim_algo, values=algo_names, state="readonly", width=8)
        self.anim_algo_combo.pack(side="left", padx=(6, 0))
        ttk.Button(anim_top, text="Run + Animate", command=self._run_animated).pack(side="left", padx=(10, 0))

        anim_mid = ttk.Frame(anim_grp)
        anim_mid.pack(fill="x", padx=6, pady=4)
        ttk.Button(anim_mid, text="Play", command=self._play_animation).pack(side="left")
        ttk.Button(anim_mid, text="Pause", command=self._pause_animation).pack(side="left", padx=6)
        ttk.Button(anim_mid, text="Reset", command=self._reset_animation).pack(side="left")
        ttk.Label(anim_mid, text="Speed").pack(side="left", padx=(10, 4))
        self.anim_speed_scale = ttk.Scale(anim_mid, from_=50, to=1500, orient="horizontal",
                                          command=lambda v: self.anim_speed.set(int(float(v))))
        self.anim_speed_scale.set(self.anim_speed.get())
        self.anim_speed_scale.pack(side="left", fill="x", expand=True)

        anim_bot = ttk.Frame(anim_grp)
        anim_bot.pack(fill="x", padx=6, pady=(4, 8))
        ttk.Label(anim_bot, text="Step:").pack(side="left")
        self.anim_step_var = tk.IntVar(value=0)
        self.anim_step_slider = ttk.Scale(anim_bot, from_=0, to=0, orient="horizontal",
                                          variable=self.anim_step_var, command=self._on_anim_slider)
        self.anim_step_slider.configure(state="disabled")
        self.anim_step_slider.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # Comparison summary
        self.summary_grp = ttk.LabelFrame(left, text="Comparison")
        self.summary_grp.pack(fill="both", expand=True)

        self.summary_text = tk.Text(self.summary_grp, height=14, wrap="word")
        self.summary_text.pack(fill="both", expand=True, padx=6, pady=6)
        self.summary_text.insert("1.0", "Run algorithms to see per-metric winners here.")
        self.summary_text.configure(state="disabled")

        export_row = ttk.Frame(left)
        export_row.pack(fill="x", pady=(8, 0))
        ttk.Button(export_row, text="Export Results (CSV)", command=self._export_csv).pack(side="left", fill="x", expand=True)

        # Right: canvas + table
        right = ttk.Frame(self, padding=(0, 10, 10, 10))
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(0, weight=1)
        right.rowconfigure(1, weight=0)
        right.columnconfigure(0, weight=1)

        # Canvas area
        canvas_grp = ttk.LabelFrame(right, text="Graph Preview")
        canvas_grp.grid(row=0, column=0, sticky="nsew")

        self.canvas = tk.Canvas(canvas_grp, background="#ffffff", height=500)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._redraw_canvas())

        # Results table
        table_grp = ttk.LabelFrame(right, text="Results (click to visualize a path)")
        table_grp.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        cols = ("Algorithm", "Goal", "Cost", "PathLen", "Path", "Nodes", "Time(ms)", "Trace")
        self.table = ttk.Treeview(table_grp, columns=cols, show="headings", height=12)
        col_widths = {"Algorithm": 90, "Goal": 60, "Cost": 60, "PathLen": 70, "Path": 200, "Nodes": 70, "Time(ms)": 80, "Trace": 60}
        for c in cols:
            self.table.heading(c, text=c)
            self.table.column(c, anchor="center" if c != "Path" else "w", width=col_widths.get(c, 110))
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self._on_table_select)

        # Status bar
        self.status = ttk.Label(self, text="Ready", relief="sunken", anchor="w")
        self.status.grid(row=1, column=0, columnspan=2, sticky="ew")

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
            self.file_info.configure(text=f"Loaded {os.path.basename(path)} — Nodes: {n_nodes}, Edges: {n_edges}, Origin: {self.problem.origin}, Goals: {', '.join(map(str, self.problem.destinations))}")
            self.results.clear()
            self._refresh_table()
            self.current_algo_to_draw = None
            # reset animation state
            self._reset_animation(clear_only=True)
            self._redraw_canvas()
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

        # Draw edges (with arrows and optional costs)
        for (u, v), cost in self.problem.edges.items():
            if u not in self.problem.nodes or v not in self.problem.nodes:
                continue
            x1, y1 = self.problem.nodes[u]
            x2, y2 = self.problem.nodes[v]
            c1 = self._world_to_canvas(x1, y1, bbox)
            c2 = self._world_to_canvas(x2, y2, bbox)
            self.canvas.create_line(*c1, *c2, fill="#9aa0a6", width=2, arrow="last", arrowshape=(10, 12, 4))
            if self.draw_edge_costs.get():
                # Show cost label: numeric only, positioned on edge with smart offset
                dx = c2[0] - c1[0]
                dy = c2[1] - c1[1]
                length = (dx*dx + dy*dy) ** 0.5 or 1.0
                # Position at midpoint along edge
                t = 0.5
                px = c1[0] + dx * t
                py = c1[1] + dy * t
                # Perpendicular offset to avoid overlapping the line
                nx = -dy / length
                ny = dx / length
                # Offset to one side based on edge direction for consistency
                side = 1 if u < v else -1
                off = 10 * side
                lx = px + nx * off
                ly = py + ny * off
                # Draw numeric cost only (minimal clutter)
                text_id = self.canvas.create_text(lx, ly, text=str(cost), fill="#202124", font=("Consolas", 9))
                bx1, by1, bx2, by2 = self.canvas.bbox(text_id)
                pad = 2
                rect_id = self.canvas.create_rectangle(bx1 - pad, by1 - pad, bx2 + pad, by2 + pad, fill="#fff", outline="")
                self.canvas.tag_raise(text_id, rect_id)

        # Draw selected path (under nodes) when not animating
        if self.current_algo_to_draw and self.current_algo_to_draw in self.results and not self.trace:
            path = self.results[self.current_algo_to_draw].get("path") or []
            if len(path) >= 2:
                for i in range(len(path) - 1):
                    u, v = path[i], path[i + 1]
                    if u in self.problem.nodes and v in self.problem.nodes:
                        x1, y1 = self.problem.nodes[u]
                        x2, y2 = self.problem.nodes[v]
                        c1 = self._world_to_canvas(x1, y1, bbox)
                        c2 = self._world_to_canvas(x2, y2, bbox)
                        # Thinner path to avoid occluding labels
                        self.canvas.create_line(*c1, *c2, fill="#34a853", width=3)

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

        # Legend overlay
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
            for name in algo_list:
                if self._stop_flag.is_set():
                    break
                fn = ALGO_FUNCS[name]
                t0 = time.perf_counter()
                result = fn(self.problem, observer=None)
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
            # Append via Tk thread for safety
            self.after(0, lambda s=snap: self._append_trace_step(s))

        def worker():
            fn = ALGO_FUNCS[algo]
            t0 = time.perf_counter()
            result = fn(self.problem, observer=observer)
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
            
            self.after(0, self._on_animation_ready)

        self._stop_flag.clear()
        self._run_thread = threading.Thread(target=worker, daemon=True)
        self._run_thread.start()

    def _append_trace_step(self, step):
        self.trace.append(step)
        # Update slider range
        if len(self.trace) == 1:
            self.anim_step_slider.configure(state="normal")
        self.anim_step_slider.configure(to=max(0, len(self.trace) - 1))
        # Draw first step immediately
        if len(self.trace) == 1:
            self.trace_index = 0
            self._redraw_canvas()

    def _on_animation_ready(self):
        total = len(self.trace)
        self._set_status(f"Animation ready: {total} steps. Press Play to start.")

    def _play_animation(self):
        if not self.trace:
            messagebox.showinfo("No trace", "Run + Animate first.")
            return
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
        self._redraw_canvas()

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
        self.anim_step_var.set(self.trace_index)
        self.trace_index += 1
        self.anim_timer = self.after(self.anim_speed.get(), self._tick_animation)

    def _on_anim_slider(self, _):
        if not self.trace:
            return
        self._pause_animation()
        idx = int(float(self.anim_step_var.get()))
        idx = max(0, min(idx, len(self.trace) - 1))
        self.trace_index = idx
        self._redraw_canvas()

    def _draw_step_on_canvas(self, step):
        # Overlay current step information: explored/frontier/current and goal path if present
        if not self.problem:
            return
        bbox = self._world_bounds()
        # Draw final path first (under overlays)
        if step.get("action") == "goal" and self.anim_result_path and len(self.anim_result_path) >= 2:
            for i in range(len(self.anim_result_path) - 1):
                u, v = self.anim_result_path[i], self.anim_result_path[i + 1]
                if u in self.problem.nodes and v in self.problem.nodes:
                    x1, y1 = self.problem.nodes[u]
                    x2, y2 = self.problem.nodes[v]
                    c1 = self._world_to_canvas(x1, y1, bbox)
                    c2 = self._world_to_canvas(x2, y2, bbox)
                    self.canvas.create_line(*c1, *c2, fill="#34a853", width=3)
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
        # Current
        if current in self.problem.nodes:
            x, y = self.problem.nodes[current]
            cx, cy = self._world_to_canvas(x, y, bbox)
            r = 22
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#f9ab00", outline="#e37400", width=4)
            self.canvas.create_text(cx, cy, text=str(current), fill="#ffffff", font=("Segoe UI", 11, "bold"))

    def _draw_legend(self):
        if not self.show_legend.get():
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
