import os, io
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

        # ---------- PDF STATE ----------
        self.folder = None
        self.files = []
        self.doc = None
        self.page_i = 0
        self.zoom = 1.25

        # ---------- TOOL STATE ----------
        self.tool = "pen"
        self.color = "#ff0000"
        self.start = None
        self.current = None

        # ---------- GRID ----------
        self.grid_size = 20
        self.snap_enabled = True

        # ---------- NAVIGATION ----------
        self.hand_mode = False
        self.pan_start = None

        # ---------- UNDO / REDO ----------
        self.undo_stack = []
        self.redo_stack = []

        self.build()

        # Emergency unlock
        self.bind("<Escape>", lambda e: self.reset_state())

    # =========================================================
    # CORE STABILITY FIX — SINGLE SOURCE OF TRUTH
    # =========================================================
    def reset_state(self):
        # Cancel drawing
        self.start = None
        self.current = None

        # Cancel panning
        self.pan_start = None
        self.hand_mode = False

        # Remove temp objects
        self.canvas.delete("temp")

        # Clear undo/redo (per-document session)
        self.undo_stack.clear()
        self.redo_stack.clear()

        # ✅ CORRECT Tkinter focus handling
        try:
            self.list.focus_set()
        except Exception:
            self.focus_set()

    # =========================================================
    # UI
    # =========================================================
    def build(self):
        bar = tk.Frame(self)
        bar.pack(fill="x")

        tk.Button(bar, text="Open", command=self.open_folder).pack(side="left")
        tk.Button(bar, text="Save", command=self.save_pdf).pack(side="left")
        tk.Button(bar, text="Undo", command=self.undo).pack(side="left")
        tk.Button(bar, text="Redo", command=self.redo).pack(side="left")
        tk.Button(bar, text="Fit Width", command=self.fit).pack(side="left")
        tk.Button(bar, text="Hand", command=self.toggle_hand).pack(side="left")
        tk.Button(bar, text="Snap ON/OFF", command=self.toggle_snap).pack(side="left")

        for t in ["pen", "highlighter", "rect", "oval", "triangle", "text"]:
            tk.Button(bar, text=t, command=lambda x=t: self.set_tool(x)).pack(side="left")

        tk.Button(bar, text="Color", command=self.pick_color).pack(side="left")

        pan = tk.PanedWindow(self, orient="horizontal")
        pan.pack(fill="both", expand=True)

        self.list = tk.Listbox(pan, width=30)
        self.list.bind("<<ListboxSelect>>", self.sel)
        pan.add(self.list)

        self.canvas = tk.Canvas(pan, bg="#444")
        pan.add(self.canvas)

        self.canvas.bind("<Button-1>", self.down)
        self.canvas.bind("<B1-Motion>", self.move)
        self.canvas.bind("<ButtonRelease-1>", self.up)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_scroll)

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

    def sel(self, e):
        if self.start is not None:
            return  # block switching mid-draw

        if self.list.curselection():
            self.open_pdf(self.list.curselection()[0])

    def open_pdf(self, i):
        self.reset_state()   # ✅ HARD RESET BEFORE SWITCH

        if self.doc:
            self.doc.close()

        self.doc = fitz.open(self.files[i])
        self.page_i = 0
        self.render()

    def render(self):
        page = self.doc.load_page(self.page_i)
        pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)
        self.canvas.config(scrollregion=(0, 0, img.width, img.height))

    def fit(self):
        page = self.doc.load_page(self.page_i)
        w = self.canvas.winfo_width() or 800
        self.zoom = w / page.rect.width
        self.render()

    # =========================================================
    # TOOLS
    # =========================================================
    def set_tool(self, t):
        self.reset_state()
        self.tool = t

    def toggle_hand(self):
        self.reset_state()
        self.hand_mode = True

    def toggle_snap(self):
        self.snap_enabled = not self.snap_enabled

    def pick_color(self):
        c = colorchooser.askcolor(self.color)[1]
        if c:
            self.color = c

    def snap(self, x, y):
        if not self.snap_enabled:
            return x, y
        g = self.grid_size
        return round(x / g) * g, round(y / g) * g

    # =========================================================
    # NAVIGATION
    # =========================================================
    def on_ctrl_scroll(self, e):
        self.zoom *= 1.1 if e.delta > 0 else 0.9
        self.zoom = max(0.2, min(self.zoom, 5))
        self.render()

    def on_mousewheel(self, e):
        self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # =========================================================
    # DRAWING
    # =========================================================
    def down(self, e):
        if self.hand_mode:
            self.pan_start = (e.x, e.y)
            return

        x, y = self.snap(e.x, e.y)
        self.start = (x, y)

        if self.tool == "text":
            txt = simpledialog.askstring("Text", "Enter comment")
            if txt:
                item = self.canvas.create_text(x, y, text=txt, fill=self.color)
                self.undo_stack.append(item)

    def move(self, e):
        if self.hand_mode and self.pan_start:
            dx = self.pan_start[0] - e.x
            dy = self.pan_start[1] - e.y
            self.canvas.xview_scroll(int(dx), "units")
            self.canvas.yview_scroll(int(dy), "units")
            self.pan_start = (e.x, e.y)
            return

        if not self.start:
            return

        x0, y0 = self.start
        x1, y1 = self.snap(e.x, e.y)

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
            item = self.canvas.create_line(
                x0, y0, x1, y1, fill=self.color, width=w
            )
            self.undo_stack.append(item)
            self.start = (x1, y1)

    def up(self, e):
        if self.hand_mode:
            self.pan_start = None
            return

        if self.current:
            coords = self.canvas.coords(self.current)
            self.canvas.delete("temp")

            if self.tool == "rect":
                item = self.canvas.create_rectangle(*coords, outline=self.color)
            elif self.tool == "oval":
                item = self.canvas.create_oval(*coords, outline=self.color)
            elif self.tool == "triangle":
                item = self.canvas.create_polygon(*coords, outline=self.color, fill="")

            self.undo_stack.append(item)

        self.start = None
        self.current = None

    # =========================================================
    # UNDO / REDO
    # =========================================================
    def undo(self):
        if not self.undo_stack:
            return
        item = self.undo_stack.pop()
        self.canvas.itemconfigure(item, state="hidden")
        self.redo_stack.append(item)

    def redo(self):
        if not self.redo_stack:
            return
        item = self.redo_stack.pop()
        self.canvas.itemconfigure(item, state="normal")
        self.undo_stack.append(item)

    # =========================================================
    # SAVE
    # =========================================================
    
    def save_pdf(self):
        if not self.doc:
            return
        dst_pdf = src_pdf.with_name(src_pdf.stem + "_annotated.pdf")

        doc = fitz.open(src_pdf)
        page = doc.load_page(self.page_i)

        scale = 1 / self.zoom

        for item in self.undo_stack:
            if self.canvas.itemcget(item, "state") == "hidden":
                continue

            item_type = self.canvas.type(item)
            coords = self.canvas.coords(item)
            color = self.canvas.itemcget(item, "fill") or self.canvas.itemcget(item, "outline") or "#ff0000"

            # convert hex to RGB
            r = int(color[1:3], 16) / 255
            g = int(color[3:5], 16) / 255
            b = int(color[5:7], 16) / 255

            if item_type == "line":
                x0, y0, x1, y1 = [c * scale for c in coords]
                page.draw_line(
                    fitz.Point(x0, y0),
                    fitz.Point(x1, y1),
                    color=(r, g, b),
                    width=2
                )

            elif item_type in ("rectangle", "oval", "polygon"):
                pts = [(coords[i] * scale, coords[i+1] * scale) for i in range(0, len(coords), 2)]
                page.draw_polyline(
                    pts + [pts[0]],
                    color=(r, g, b),
                    width=2
                )

            elif item_type == "text":
                x, y = coords
                text = self.canvas.itemcget(item, "text")
                page.insert_text(
                    fitz.Point(x * scale, y * scale),
                    text,
                    fontsize=12,
                    color=(r, g, b)
                )

        doc.save(dst_pdf)
        messagebox.showinfo("Saved", f"Saved {dst_pdf}")



App().mainloop()
