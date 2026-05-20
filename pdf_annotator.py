import tkinter as tk
from tkinter import filedialog, simpledialog, colorchooser, messagebox
from pathlib import Path
import fitz
from PIL import Image, ImageTk


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Annotator PRO (Full UI)")
        self.geometry("1300x850")

        # ---------- THEME ----------
        self.bg_main = "#1e1e2e"
        self.bg_panel = "#181825"
        self.bg_btn = "#313244"
        self.fg_main = "#cdd6f4"

        self.config(bg=self.bg_main)

        # ---------- STATE ----------
        self.folder = None
        self.files = []
        self.doc = None
        self.page_i = 0
        self.zoom = 1.2

        # Search
        self.search_results = []
        self.search_result_i = -1

        # Draw
        self.color = "#ff0000"
        self.start = None

        self.build()

    # ===============================
    # UI BUILD
    # ===============================
    def build(self):

        # ---------- TWO-LINE TOOLBAR ----------
        toolbar = tk.Frame(self, bg=self.bg_panel)
        toolbar.pack(fill="x")

        bar_top = tk.Frame(toolbar, bg=self.bg_panel)
        bar_top.pack(fill="x")

        bar_bottom = tk.Frame(toolbar, bg=self.bg_panel)
        bar_bottom.pack(fill="x")

        def btn(parent, text, cmd):
            return tk.Button(parent, text=text, command=cmd,
                             bg=self.bg_btn, fg=self.fg_main,
                             bd=0, padx=8, pady=4)

        # TOP ROW
        btn(bar_top, "📁 Open Folder", self.open_folder).pack(side="left", padx=3)
        btn(bar_top, "💾 Save", self.save_pdf).pack(side="left", padx=3)
        btn(bar_top, "↩ Undo", self.undo).pack(side="left", padx=3)
        btn(bar_top, "↪ Redo", self.redo).pack(side="left", padx=3)
        btn(bar_top, "🔍 Fit", self.fit).pack(side="left", padx=3)

        # BOTTOM ROW
        btn(bar_bottom, "🖐 Hand", lambda: None).pack(side="left")
        btn(bar_bottom, "✏ Pen", lambda: None).pack(side="left")

        tk.Button(bar_bottom, text="🎨 Color", command=self.pick_color).pack(side="left")

        # Page Navigation
        btn(bar_bottom, "◀", self.prev_page).pack(side="left")
        self.page_label = tk.Label(bar_bottom, text="Page 0", fg=self.fg_main, bg=self.bg_panel)
        self.page_label.pack(side="left")
        btn(bar_bottom, "▶", self.next_page).pack(side="left")

        # Page lookup
        tk.Label(bar_bottom, text="Go:", fg=self.fg_main, bg=self.bg_panel).pack(side="left")
        self.page_entry = tk.Entry(bar_bottom, width=5)
        self.page_entry.pack(side="left")
        self.page_entry.bind("<Return>", lambda e: self.goto_page())

        # Search
        tk.Label(bar_bottom, text="Search:", fg=self.fg_main, bg=self.bg_panel).pack(side="left")
        self.search_entry = tk.Entry(bar_bottom, width=15)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<Return>", lambda e: self.search_pdf())

        btn(bar_bottom, "Find", self.search_pdf).pack(side="left")
        btn(bar_bottom, "↑", self.prev_search).pack(side="left")
        btn(bar_bottom, "↓", self.next_search).pack(side="left")

        # ---------- MAIN SPLIT ----------
        pan = tk.PanedWindow(self, orient="horizontal", bg=self.bg_main)
        pan.pack(fill="both", expand=True)

        # LEFT: FILE LIST
        left = tk.Frame(pan, bg=self.bg_panel)
        pan.add(left)

        self.list = tk.Listbox(left, bg=self.bg_panel, fg=self.fg_main)
        self.list.pack(fill="both", expand=True)
        self.list.bind("<<ListboxSelect>>", self.select_file)

        # RIGHT: CANVAS
        right = tk.Frame(pan, bg=self.bg_main)
        pan.add(right)

        self.canvas = tk.Canvas(right, bg="#000")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<Button-1>", self.down)
        self.canvas.bind("<B1-Motion>", self.move)

    # ===============================
    # FILE MANAGEMENT
    # ===============================
    def open_folder(self):
        path = filedialog.askdirectory()
        if not path:
            return

        self.folder = Path(path)
        self.files = list(self.folder.glob("*.pdf"))

        self.list.delete(0, "end")
        for f in self.files:
            self.list.insert("end", f.name)

        if self.files:
            self.open_pdf(0)

    def select_file(self, e):
        if not self.list.curselection():
            return
        self.open_pdf(self.list.curselection()[0])

    def open_pdf(self, i):
        self.doc = fitz.open(self.files[i])
        self.page_i = 0
        self.render()

    # ===============================
    # RENDER
    # ===============================
    def render(self):
        page = self.doc.load_page(self.page_i)
        pix = page.get_pixmap(matrix=fitz.Matrix(self.zoom, self.zoom))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.page_label.config(text=f"{self.page_i+1}/{len(self.doc)}")
        self.render_search()

    # ===============================
    # NAVIGATION
    # ===============================
    def next_page(self):
        if self.page_i < len(self.doc)-1:
            self.page_i += 1
            self.render()

    def prev_page(self):
        if self.page_i > 0:
            self.page_i -= 1
            self.render()

    def goto_page(self):
        try:
            p = int(self.page_entry.get()) - 1
            if 0 <= p < len(self.doc):
                self.page_i = p
                self.render()
        except:
            pass

    # ===============================
    # SEARCH (EXACT NAVIGATION)
    # ===============================
    def search_pdf(self):
        q = self.search_entry.get()
        self.search_results = []

        for i in range(len(self.doc)):
            for r in self.doc[i].search_for(q):
                self.search_results.append((i, r))

        if self.search_results:
            self.search_result_i = 0
            self.jump_search()

    def jump_search(self):
        p, r = self.search_results[self.search_result_i]
        self.page_i = p
        self.render()

        self.canvas.xview_moveto((r.x0 * self.zoom) / 2000)
        self.canvas.yview_moveto((r.y0 * self.zoom) / 2000)

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

            color = "orange" if i == self.search_result_i else "yellow"

            self.canvas.create_rectangle(x0, y0, x1, y1, outline=color, width=2)

    # ===============================
    # DRAW
    # ===============================
    def down(self, e):
        self.start = (e.x, e.y)

    def move(self, e):
        if not self.start:
            return
        x0, y0 = self.start
        self.canvas.create_line(x0, y0, e.x, e.y, fill=self.color)
        self.start = (e.x, e.y)

    def pick_color(self):
        c = colorchooser.askcolor()[1]
        if c:
            self.color = c

    def undo(self): pass
    def redo(self): pass
    def save_pdf(self): pass
    def fit(self): pass


if __name__ == "__main__":
    App().mainloop()