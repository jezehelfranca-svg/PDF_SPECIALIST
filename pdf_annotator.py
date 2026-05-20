import os
import io
import tkinter as tk
from tkinter import filedialog, simpledialog, colorchooser, messagebox
from pathlib import Path
import fitz
from PIL import Image, ImageTk


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Annotator PRO (Stable)")
        self.geometry("1300x850")

        # ---------- DESIGN SYSTEM (Catppuccin Mocha themed) ----------
        self.bg_main = "#1e1e2e"         # Base background
        self.bg_panel = "#181825"        # Sidebar/Toolbar background
        self.bg_btn = "#313244"          # Default button color
        self.bg_btn_hover = "#45475a"    # Button hover color
        self.bg_btn_active = "#89b4fa"   # Selected tool/accent color
        self.fg_main = "#cdd6f4"         # Main text color
        self.fg_dark = "#11111b"         # Dark text color for light backgrounds
        self.accent = "#89b4fa"          # Soft blue accent
        self.accent_green = "#a6e3a1"    # Soft green accent for Snap ON

        self.config(bg=self.bg_main)

        # ---------- PDF STATE ----------
        self.folder = None
        self.files = []
        self.doc = None
        self.page_i = 0
        self.zoom = 1.25
        self.current_file = None
        self.current_file_index = None

        # ---------- SEARCH STATE ----------
        self.search_results = []
        self.search_result_i = -1

        # ---------- TOOL STATE ----------
        self.tool = "pen"
        self.color = "#ff0000"
        self.start = None
        self.current = None
        self.current_stroke = []

        # ---------- GRID ----------
        self.grid_size = 20
        self.snap_enabled = True

        # ---------- NAVIGATION ----------
        self.hand_mode = False
        self.pan_start = None

        # ---------- UNDO / REDO ----------
        self.undo_stack = []
        self.redo_stack = []

        # ---------- SESSION ANNOTATIONS DATABASE ----------
        # Key: page_index (int), Value: list of actions (each action is a list of item dicts)
        self.annotations_by_page = {}
        self.is_dirty = False

        self.tool_buttons = {}
        self.build()

        # Keyboard Bindings for Shortcuts
        self.bind("<Control-o>", lambda e: self.open_folder())
        self.bind("<Control-O>", lambda e: self.open_folder())
        self.bind("<Control-s>", lambda e: self.save_pdf())
        self.bind("<Control-S>", lambda e: self.save_pdf())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-Z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())
        self.bind("<Control-Y>", lambda e: self.redo())
        self.bind("<Control-plus>", lambda e: self.zoom_in())
        self.bind("<Control-equal>", lambda e: self.zoom_in())
        self.bind("<Control-minus>", lambda e: self.zoom_out())
        
        self.bind("<Prior>", self.on_page_prior)
        self.bind("<Next>", self.on_page_next)
        self.bind("<Left>", self.on_page_left)
        self.bind("<Right>", self.on_page_right)

        # Emergency unlock
        self.bind("<Escape>", lambda e: self.reset_state())
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # =========================================================
    # CORE STABILITY FIX — SINGLE SOURCE OF TRUTH
    # =========================================================
    def reset_state(self):
        # Cancel drawing
        self.start = None
        self.current = None
        self.current_stroke.clear()

        # Cancel panning
        self.pan_start = None
        if self.tool != "hand":
            self.hand_mode = False

        # Remove temp objects
        self.canvas.delete("temp")

        # Clear current undo/redo (only reset stack when loading page or new document)
        self.undo_stack.clear()
        self.redo_stack.clear()

        # Update buttons
        self.update_tool_buttons()

        # Correct Tkinter focus handling
        try:
            self.list.focus_set()
        except Exception:
            self.focus_set()

    # =========================================================
    # UI BUILD
    # =========================================================
    def build(self):
        # Top Toolbar Panel
        toolbar = tk.Frame(self, bg=self.bg_panel)
        toolbar.pack(fill="x", side="top")

        bar_top = tk.Frame(toolbar, bg=self.bg_panel, pady=4)
        bar_top.pack(fill="x")

        bar_bottom = tk.Frame(toolbar, bg=self.bg_panel, pady=4)
        bar_bottom.pack(fill="x")

        # Helper to create buttons with modern styles and hover animations
        def btn(parent, text, command, bg=self.bg_btn, fg=self.fg_main, hover_bg=self.bg_btn_hover, padx=8, pady=4):
            b = tk.Button(
                parent, text=text, command=command,
                bg=bg, fg=fg, activebackground=hover_bg, activeforeground=fg,
                font=("Segoe UI", 10), bd=0, relief="flat", padx=padx, pady=pady, cursor="hand2"
            )
            b.bind("<Enter>", lambda e: b.config(bg=hover_bg) if b.cget("state") != tk.DISABLED and b.cget("bg") != self.bg_btn_active else None)
            b.bind("<Leave>", lambda e: b.config(bg=bg) if b.cget("state") != tk.DISABLED and b.cget("bg") != self.bg_btn_active else None)
            return b

        # TOP ROW: File Operations, Edit, Zoom
        btn(bar_top, "📁 Open Folder", self.open_folder).pack(side="left", padx=5)
        btn(bar_top, "💾 Save", self.save_pdf).pack(side="left", padx=5)
        
        tk.Frame(bar_top, width=2, bg=self.bg_btn, height=25).pack(side="left", padx=8)

        btn(bar_top, "↩ Undo", self.undo).pack(side="left", padx=3)
        btn(bar_top, "↪ Redo", self.redo).pack(side="left", padx=3)
        
        tk.Frame(bar_top, width=2, bg=self.bg_btn, height=25).pack(side="left", padx=8)

        btn(bar_top, "🔍 Fit Width", self.fit).pack(side="left", padx=3)
        
        self.snap_btn = btn(bar_top, "Snap: ON", self.toggle_snap, bg=self.accent_green, fg=self.fg_dark, hover_bg=self.accent_green)
        self.snap_btn.pack(side="left", padx=3)

        # BOTTOM ROW: Tools, Color, Navigation, Lookup, Search
        tools = [
            ("🖐 Hand", "hand"),
            ("✏ Pen", "pen"),
            ("🖊 Highlighter", "highlighter"),
            ("⬜ Rect", "rect"),
            ("⭕ Oval", "oval"),
            ("▲ Triangle", "triangle"),
            ("🔤 Text", "text")
        ]

        for label, t in tools:
            b = btn(bar_bottom, label, lambda x=t: self.set_tool(x))
            b.pack(side="left", padx=3)
            self.tool_buttons[t] = b

        tk.Frame(bar_bottom, width=2, bg=self.bg_btn, height=25).pack(side="left", padx=8)

        # Color picker button and indicator
        color_container = tk.Frame(bar_bottom, bg=self.bg_panel)
        color_container.pack(side="left", padx=3)
        
        btn(color_container, "🎨 Color", self.pick_color).pack(side="left")
        self.color_indicator = tk.Frame(color_container, bg=self.color, width=18, height=18, cursor="hand2")
        self.color_indicator.pack(side="left", padx=5)
        self.color_indicator.bind("<Button-1>", lambda e: self.pick_color())

        tk.Frame(bar_bottom, width=2, bg=self.bg_btn, height=25).pack(side="left", padx=8)

        # Page navigation
        btn(bar_bottom, "◀", self.prev_page).pack(side="left", padx=1)
        self.page_label = tk.Label(bar_bottom, text="Page 0 of 0", fg=self.fg_main, bg=self.bg_panel, font=("Segoe UI", 10, "bold"))
        self.page_label.pack(side="left", padx=5)
        btn(bar_bottom, "▶", self.next_page).pack(side="left", padx=1)

        # Page lookup
        tk.Label(bar_bottom, text="Go:", fg=self.fg_main, bg=self.bg_panel, font=("Segoe UI", 9)).pack(side="left", padx=5)
        self.page_entry = tk.Entry(bar_bottom, width=5, bg=self.bg_btn, fg=self.fg_main, bd=0, insertbackground=self.fg_main, font=("Segoe UI", 10))
        self.page_entry.pack(side="left", padx=2)
        self.page_entry.bind("<Return>", lambda e: self.goto_page())

        tk.Frame(bar_bottom, width=2, bg=self.bg_btn, height=25).pack(side="left", padx=8)

        # Search
        tk.Label(bar_bottom, text="Search:", fg=self.fg_main, bg=self.bg_panel, font=("Segoe UI", 9)).pack(side="left", padx=5)
        self.search_entry = tk.Entry(bar_bottom, width=15, bg=self.bg_btn, fg=self.fg_main, bd=0, insertbackground=self.fg_main, font=("Segoe UI", 10))
        self.search_entry.pack(side="left", padx=2)
        self.search_entry.bind("<Return>", lambda e: self.search_pdf())

        btn(bar_bottom, "Find", self.search_pdf).pack(side="left", padx=3)
        btn(bar_bottom, "↑", self.prev_search).pack(side="left", padx=1)
        btn(bar_bottom, "↓", self.next_search).pack(side="left", padx=1)

        # Main Area Split Window
        pan = tk.PanedWindow(self, orient="horizontal", bg=self.bg_main, bd=0, sashwidth=4, sashpad=0)
        pan.pack(fill="both", expand=True)

        # Left panel (File list box with header)
        left_panel = tk.Frame(pan, bg=self.bg_panel)
        pan.add(left_panel)

        list_header = tk.Label(
            left_panel, text="DOCUMENTS", font=("Segoe UI", 9, "bold"), 
            bg=self.bg_panel, fg=self.accent, pady=8
        )
        list_header.pack(fill="x")

        # Scrollbars for Listbox
        list_scroll = tk.Scrollbar(left_panel, orient="vertical")
        
        self.list = tk.Listbox(
            left_panel, bg=self.bg_panel, fg=self.fg_main, 
            selectbackground=self.accent, selectforeground=self.fg_dark,
            font=("Segoe UI", 10), bd=0, highlightthickness=0,
            activestyle="none", yscrollcommand=list_scroll.set
        )
        list_scroll.config(command=self.list.yview)
        
        list_scroll.pack(side="right", fill="y")
        self.list.pack(fill="both", expand=True)
        self.list.bind("<<ListboxSelect>>", self.select_file)

        # Right Panel (Canvas with scrollbars)
        canvas_container = tk.Frame(pan, bg=self.bg_main)
        pan.add(canvas_container)

        hbar = tk.Scrollbar(canvas_container, orient="horizontal")
        vbar = tk.Scrollbar(canvas_container, orient="vertical")
        
        self.canvas = tk.Canvas(
            canvas_container, bg="#11111b", bd=0, highlightthickness=0,
            xscrollcommand=hbar.set, yscrollcommand=vbar.set
        )
        
        hbar.config(command=self.canvas.xview)
        vbar.config(command=self.canvas.yview)

        hbar.pack(side="bottom", fill="x")
        vbar.pack(side="right", fill="y")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self.down)
        self.canvas.bind("<B1-Motion>", self.move)
        self.canvas.bind("<ButtonRelease-1>", self.up)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_scroll)

        # Status Bar at bottom
        self.status_bar = tk.Frame(self, bg=self.bg_panel, height=25)
        self.status_bar.pack(side="bottom", fill="x")
        
        self.status_label = tk.Label(
            self.status_bar, text="Ready", bg=self.bg_panel, fg=self.fg_main,
            font=("Segoe UI", 9)
        )
        self.status_label.pack(side="left", padx=10)
        
        self.zoom_label = tk.Label(
            self.status_bar, text="Zoom: 125%", bg=self.bg_panel, fg=self.fg_main,
            font=("Segoe UI", 9)
        )
        self.zoom_label.pack(side="right", padx=10)

        # Set default active tool color highlight
        self.update_tool_buttons()

    # =========================================================
    # PDF HANDLING
    # =========================================================
    def open_folder(self):
        p = filedialog.askdirectory()
        if not p:
            return

        self.folder = Path(p)
        self.files = list(self.folder.glob("*.pdf"))

        self.list.delete(0, "end")
        for f in self.files:
            self.list.insert("end", f.name)

        if self.files:
            self.list.selection_set(0)
            self.open_pdf(0)

    def select_file(self, e):
        if not self.list.curselection():
            return
        idx = self.list.curselection()[0]
        if idx == self.current_file_index:
            return

        res = self.prompt_save_if_needed()
        if res is None:
            # User cancelled switching
            self.list.selection_clear(0, "end")
            if self.current_file_index is not None:
                self.list.selection_set(self.current_file_index)
            return

        self.open_pdf(idx)

    def open_pdf(self, i):
        self.reset_state()   # ✅ HARD RESET BEFORE SWITCH

        if self.doc:
            self.doc.close()

        self.current_file_index = i
        self.current_file = self.files[i]
        self.doc = fitz.open(self.current_file)
        self.page_i = 0
        self.annotations_by_page = {}
        self.is_dirty = False
        
        # Reset search
        self.search_results = []
        self.search_result_i = -1

        self.status_label.config(text=f"Loaded: {self.current_file.name}")
        self.render()
        self.update_page_label()

    def render(self):
        if not self.doc:
            return
        page = self.doc.load_page(self.page_i)
        pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.config(scrollregion=(0, 0, img.width, img.height))
        self.update_zoom_label()
        
        # Render search highlights if they exist
        self.render_search()

    def fit(self):
        if not self.doc:
            return
        self.save_current_page_annotations()
        page = self.doc.load_page(self.page_i)
        w = self.canvas.winfo_width() or 800
        # Account for scrollbar widths (approx 25px)
        w = max(200, w - 25)
        self.zoom = w / page.rect.width
        self.render()
        self.load_page_annotations()

    # =========================================================
    # TOOLS
    # =========================================================
    def set_tool(self, t):
        self.start = None
        self.current = None
        self.current_stroke.clear()
        self.pan_start = None
        
        self.tool = t
        if t == "hand":
            self.hand_mode = True
        else:
            self.hand_mode = False
        
        self.update_tool_buttons()
        self.status_label.config(text=f"Tool: {t.capitalize()}")

    def update_tool_buttons(self):
        for name, btn in self.tool_buttons.items():
            if name == self.tool:
                btn.config(bg=self.bg_btn_active, fg=self.fg_dark)
            else:
                btn.config(bg=self.bg_btn, fg=self.fg_main)

    def toggle_snap(self):
        self.snap_enabled = not self.snap_enabled
        if self.snap_enabled:
            self.snap_btn.config(text="Snap: ON", bg=self.accent_green, fg=self.fg_dark)
        else:
            self.snap_btn.config(text="Snap: OFF", bg=self.bg_btn, fg=self.fg_main)

    def pick_color(self):
        c = colorchooser.askcolor(self.color)[1]
        if c:
            self.color = c
            self.color_indicator.config(bg=c)

    def snap(self, x, y):
        if not self.snap_enabled:
            return x, y
        g = self.grid_size
        return round(x / g) * g, round(y / g) * g

    # =========================================================
    # PAGE NAVIGATION
    # =========================================================
    def next_page(self):
        if not self.doc:
            return
        if self.page_i < len(self.doc) - 1:
            self.save_current_page_annotations()
            self.page_i += 1
            self.render()
            self.load_page_annotations()
            self.update_page_label()

    def prev_page(self):
        if not self.doc:
            return
        if self.page_i > 0:
            self.save_current_page_annotations()
            self.page_i -= 1
            self.render()
            self.load_page_annotations()
            self.update_page_label()

    def goto_page(self):
        if not self.doc:
            return
        try:
            p = int(self.page_entry.get()) - 1
            if 0 <= p < len(self.doc):
                self.save_current_page_annotations()
                self.page_i = p
                self.render()
                self.load_page_annotations()
                self.update_page_label()
        except:
            pass

    def update_page_label(self):
        if self.doc:
            self.page_label.config(text=f"{self.page_i + 1}/{len(self.doc)}")
        else:
            self.page_label.config(text="0/0")

    # =========================================================
    # SEARCH
    # =========================================================
    def search_pdf(self, e=None):
        q = self.search_entry.get()
        if not q or not self.doc:
            return
        self.search_results = []

        for i in range(len(self.doc)):
            for r in self.doc[i].search_for(q):
                self.search_results.append((i, r))

        if self.search_results:
            self.search_result_i = 0
            self.jump_search()
        else:
            self.search_result_i = -1
            self.status_label.config(text=f"No results for: '{q}'")
            self.render()

    def jump_search(self):
        p, r = self.search_results[self.search_result_i]
        self.save_current_page_annotations()
        self.page_i = p
        self.render()
        self.load_page_annotations()
        self.update_page_label()
        self.status_label.config(text=f"Match {self.search_result_i + 1} of {len(self.search_results)}")

        # Center search result in viewport
        cw = self.canvas.winfo_width() or 800
        ch = self.canvas.winfo_height() or 600
        
        target_x = ((r.x0 + r.x1) / 2) * self.zoom
        target_y = ((r.y0 + r.y1) / 2) * self.zoom
        
        page = self.doc.load_page(self.page_i)
        total_w = page.rect.width * self.zoom
        total_h = page.rect.height * self.zoom
        
        frac_x = max(0.0, (target_x - cw / 2) / total_w)
        frac_y = max(0.0, (target_y - ch / 2) / total_h)
        
        self.canvas.xview_moveto(frac_x)
        self.canvas.yview_moveto(frac_y)

    def next_search(self):
        if not self.search_results:
            return
        self.search_result_i = (self.search_result_i + 1) % len(self.search_results)
        self.jump_search()

    def prev_search(self):
        if not self.search_results:
            return
        self.search_result_i = (self.search_result_i - 1) % len(self.search_results)
        self.jump_search()

    def render_search(self):
        if not self.search_results:
            return

        for i, (p, r) in enumerate(self.search_results):
            if p != self.page_i:
                continue

            x0, y0 = r.x0 * self.zoom, r.y0 * self.zoom
            x1, y1 = r.x1 * self.zoom, r.y1 * self.zoom

            color = "#ff9e3b" if i == self.search_result_i else "#ffd15c"
            
            self.canvas.create_rectangle(
                x0, y0, x1, y1, outline=color, width=3, tags="search_highlight"
            )

    # =========================================================
    # NAVIGATION / ZOOM ACTIONS
    # =========================================================
    def update_zoom_label(self):
        self.zoom_label.config(text=f"Zoom: {int(self.zoom * 100)}%")

    def zoom_in(self):
        if not self.doc:
            return
        self.save_current_page_annotations()
        self.zoom = min(5.0, self.zoom * 1.1)
        self.render()
        self.load_page_annotations()

    def zoom_out(self):
        if not self.doc:
            return
        self.save_current_page_annotations()
        self.zoom = max(0.2, self.zoom * 0.9)
        self.render()
        self.load_page_annotations()

    def on_ctrl_scroll(self, e):
        if e.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def on_mousewheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # =========================================================
    # KEYBOARD NAVIGATION BYPASS CHECKS
    # =========================================================
    def check_focus_bypass(self):
        return isinstance(self.focus_get(), tk.Entry)

    def on_page_prior(self, e):
        if self.check_focus_bypass():
            return
        self.prev_page()
        return "break"

    def on_page_next(self, e):
        if self.check_focus_bypass():
            return
        self.next_page()
        return "break"

    def on_page_left(self, e):
        if self.check_focus_bypass():
            return
        self.prev_page()
        return "break"

    def on_page_right(self, e):
        if self.check_focus_bypass():
            return
        self.next_page()
        return "break"

    # =========================================================
    # DRAWING ACTIONS (COORDINATE SCROLL CORRECTION & GROUPS)
    # =========================================================
    def down(self, e):
        if not self.doc:
            return
            
        cx = self.canvas.canvasx(e.x)
        cy = self.canvas.canvasy(e.y)

        if self.hand_mode:
            self.pan_start = (e.x, e.y)
            return

        x, y = self.snap(cx, cy)
        self.start = (x, y)
        self.current_stroke.clear()

        if self.tool == "text":
            txt = simpledialog.askstring("Text", "Enter comment:")
            if txt:
                item = self.canvas.create_text(x, y, text=txt, fill=self.color, font=("Segoe UI", int(12 * self.zoom)))
                self.undo_stack.append([item])
                self.redo_stack.clear()
                self.is_dirty = True

    def move(self, e):
        if not self.doc:
            return
            
        if self.hand_mode and self.pan_start:
            dx = self.pan_start[0] - e.x
            dy = self.pan_start[1] - e.y
            self.canvas.xview_scroll(int(dx), "units")
            self.canvas.yview_scroll(int(dy), "units")
            self.pan_start = (e.x, e.y)
            return

        if not self.start:
            return

        cx = self.canvas.canvasx(e.x)
        cy = self.canvas.canvasy(e.y)

        x0, y0 = self.start
        x1, y1 = self.snap(cx, cy)

        self.canvas.delete("temp")

        if self.tool == "rect":
            self.current = self.canvas.create_rectangle(
                x0, y0, x1, y1, outline=self.color, tags="temp"
            )

        elif self.tool == "oval":
            self.current = self.canvas.create_oval(
                x0, y0, x1, y1, outline=self.color, tags="temp"
            )

        elif self.tool == "triangle":
            mid_x = (x0 + x1) / 2
            self.current = self.canvas.create_polygon(
                mid_x, y0, x0, y1, x1, y1,
                outline=self.color, fill="", tags="temp"
            )

        elif self.tool in ["pen", "highlighter"]:
            w = 6 if self.tool == "highlighter" else 2
            tags = ("highlighter",) if self.tool == "highlighter" else ("pen",)
            item = self.canvas.create_line(
                x0, y0, x1, y1, fill=self.color, width=w, tags=tags
            )
            self.current_stroke.append(item)
            self.start = (x1, y1)

    def up(self, e):
        if self.hand_mode:
            self.pan_start = None
            return

        # Handle shape creation on release
        if self.current:
            coords = self.canvas.coords(self.current)
            self.canvas.delete("temp")

            if self.tool == "rect":
                item = self.canvas.create_rectangle(*coords, outline=self.color, width=2)
            elif self.tool == "oval":
                item = self.canvas.create_oval(*coords, outline=self.color, width=2)
            elif self.tool == "triangle":
                item = self.canvas.create_polygon(*coords, outline=self.color, fill="", width=2)

            self.undo_stack.append([item])
            self.redo_stack.clear()
            self.is_dirty = True

        # Handle stroke completion
        elif self.current_stroke:
            self.undo_stack.append(list(self.current_stroke))
            self.redo_stack.clear()
            self.current_stroke.clear()
            self.is_dirty = True

        self.start = None
        self.current = None

    # =========================================================
    # UNDO / REDO
    # =========================================================
    def undo(self):
        if not self.undo_stack:
            return
        action = self.undo_stack.pop()
        for item in action:
            self.canvas.itemconfigure(item, state="hidden")
        self.redo_stack.append(action)
        self.is_dirty = True

    def redo(self):
        if not self.redo_stack:
            return
        action = self.redo_stack.pop()
        for item in action:
            self.canvas.itemconfigure(item, state="normal")
        self.undo_stack.append(action)
        self.is_dirty = True

    # =========================================================
    # SESSION SERIALIZATION
    # =========================================================
    def get_current_annotations_normalized(self):
        serialized = []
        scale = 1.0 / self.zoom
        for action in self.undo_stack:
            serialized_action = []
            for item in action:
                if self.canvas.itemcget(item, "state") == "hidden":
                    continue
                item_type = self.canvas.type(item)
                coords = self.canvas.coords(item)
                tags = self.canvas.gettags(item)
                
                normalized_coords = [c * scale for c in coords]
                
                color = self.canvas.itemcget(item, "fill") or self.canvas.itemcget(item, "outline") or "#ff0000"
                width = 1.0
                if item_type in ("line", "rectangle", "oval", "polygon"):
                    try:
                        width = float(self.canvas.itemcget(item, "width") or 1.0) * scale
                    except Exception:
                        width = 1.0 * scale
                
                text = ""
                if item_type == "text":
                    text = self.canvas.itemcget(item, "text")
                
                serialized_action.append({
                    "type": item_type,
                    "coords": normalized_coords,
                    "color": color,
                    "width": width,
                    "tags": tags,
                    "text": text
                })
            if serialized_action:
                serialized.append(serialized_action)
        return serialized

    def save_current_page_annotations(self):
        if self.doc is not None:
            self.annotations_by_page[self.page_i] = self.get_current_annotations_normalized()

    def load_page_annotations(self):
        if self.doc is None:
            return
        serialized = self.annotations_by_page.get(self.page_i, [])
        self.undo_stack.clear()
        self.redo_stack.clear()
        
        zoom = self.zoom
        
        for action_data in serialized:
            action_items = []
            for item_data in action_data:
                t = item_data["type"]
                coords = item_data["coords"]
                color = item_data["color"]
                width = item_data["width"]
                tags = item_data["tags"]
                text = item_data["text"]
                
                scaled_coords = [c * zoom for c in coords]
                scaled_width = max(1.0, width * zoom)
                
                if t == "line":
                    item = self.canvas.create_line(*scaled_coords, fill=color, width=scaled_width, tags=tags)
                elif t == "rectangle":
                    item = self.canvas.create_rectangle(*scaled_coords, outline=color, width=scaled_width, tags=tags)
                elif t == "oval":
                    item = self.canvas.create_oval(*scaled_coords, outline=color, width=scaled_width, tags=tags)
                elif t == "polygon":
                    item = self.canvas.create_polygon(*scaled_coords, outline=color, fill="", width=scaled_width, tags=tags)
                elif t == "text":
                    item = self.canvas.create_text(*scaled_coords, text=text, fill=color, tags=tags)
                    font_size = max(6, int(12 * zoom))
                    self.canvas.itemconfigure(item, font=("Segoe UI", font_size))
                else:
                    continue
                action_items.append(item)
            if action_items:
                self.undo_stack.append(action_items)

    # =========================================================
    # SAVE TO PDF
    # =========================================================
    def save_pdf(self):
        if not self.doc or not self.current_file:
            return
        
        # Save current page session annotations first
        self.save_current_page_annotations()

        dst_pdf = self.current_file.with_name(self.current_file.stem + "_annotated.pdf")

        # Open the source file freshly to write annotations
        doc = fitz.open(self.current_file)
        
        # Iterate over all pages that contain annotations
        for page_num, actions in self.annotations_by_page.items():
            if page_num >= len(doc):
                continue
            page = doc.load_page(page_num)
            
            for action in actions:
                for item_data in action:
                    item_type = item_data["type"]
                    coords = item_data["coords"]
                    color = item_data["color"]
                    width = item_data["width"]
                    tags = item_data["tags"]
                    text = item_data["text"]
                    
                    try:
                        r = int(color[1:3], 16) / 255
                        g = int(color[3:5], 16) / 255
                        b = int(color[5:7], 16) / 255
                    except Exception:
                        r, g, b = 1.0, 0.0, 0.0
                    
                    stroke_opacity = 0.5 if "highlighter" in tags else 1.0
                    
                    if item_type == "line":
                        scaled_pts = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
                        if len(scaled_pts) > 2:
                            page.draw_polyline(
                                scaled_pts,
                                color=(r, g, b),
                                width=width,
                                stroke_opacity=stroke_opacity
                            )
                        elif len(scaled_pts) == 2:
                            page.draw_line(
                                fitz.Point(scaled_pts[0]),
                                fitz.Point(scaled_pts[1]),
                                color=(r, g, b),
                                width=width,
                                stroke_opacity=stroke_opacity
                            )
                    
                    elif item_type == "rectangle":
                        x0, y0, x1, y1 = coords
                        rect = fitz.Rect(x0, y0, x1, y1)
                        page.draw_rect(
                            rect,
                            color=(r, g, b),
                            width=width,
                            stroke_opacity=stroke_opacity
                        )
                        
                    elif item_type == "oval":
                        x0, y0, x1, y1 = coords
                        rect = fitz.Rect(x0, y0, x1, y1)
                        page.draw_oval(
                            rect,
                            color=(r, g, b),
                            width=width,
                            stroke_opacity=stroke_opacity
                        )
                        
                    elif item_type == "polygon":
                        scaled_pts = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
                        page.draw_polyline(
                            scaled_pts,
                            color=(r, g, b),
                            width=width,
                            closePath=True,
                            stroke_opacity=stroke_opacity
                        )
                        
                    elif item_type == "text":
                        x, y = coords
                        page.insert_text(
                            fitz.Point(x, y),
                            text,
                            fontsize=12,
                            color=(r, g, b)
                        )
        
        try:
            doc.save(dst_pdf)
            doc.close()
            self.is_dirty = False
            self.status_label.config(text=f"Saved annotated PDF to: {dst_pdf.name}")
            messagebox.showinfo("Saved", f"Saved annotated PDF successfully as:\n{dst_pdf.name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PDF: {e}")

    # =========================================================
    # CLOSING HANDLERS
    # =========================================================
    def prompt_save_if_needed(self):
        if self.doc and self.is_dirty:
            has_annots = any(self.annotations_by_page.values()) or len(self.undo_stack) > 0
            if has_annots:
                res = messagebox.askyesnocancel(
                    "Unsaved Changes",
                    f"You have unsaved annotations in '{self.current_file.name}'.\nDo you want to save them?"
                )
                if res is True:
                    self.save_pdf()
                return res
        return True

    def on_close(self):
        self.save_current_page_annotations()
        res = self.prompt_save_if_needed()
        if res is not None:
            self.destroy()


if __name__ == "__main__":
    App().mainloop()