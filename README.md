# PDF Annotator PRO

A modern, high-fidelity PDF annotation and preview application built in Python using **Tkinter** and **PyMuPDF**. Featuring scroll-aware coordinate precision, multi-page state preservation, text search integration, keyboard shortcuts, and full vector PDF output generation.

---

## Key Features

- **Advanced Drawing Tools**:
  - **Pen**: Freehand sketching.
  - **Highlighter**: Semi-transparent yellow/color highlights.
  - **Shapes**: Draw vector rectangles, circles (ovals), and triangles.
  - **Text Commenting**: Place text bubbles directly onto the PDF page.
  - **Color Picker**: Change stroke and shape colors dynamically with a live color indicator block.
- **State Preservation**:
  - **Session Annotations**: Drawings and shapes are normalized to standard coordinates, preserving them across canvas zooms, resizing, and page switches.
  - **Undo & Redo**: Manage mistakes easily with complete stroke-level undo/redo operations.
- **Smart Navigation**:
  - Prev/Next page buttons, page-turn hotkeys, and direct page number lookup.
  - **Text Search**: Search the document for matching text phrases, cycle through hits, and center the viewport exactly on search matches.
- **Modern Dark Theme**:
  - Stylish dark-mode UI inspired by Catppuccin Mocha.
  - Flat hover-animated buttons and clear active-tool highlighting.
  - Custom scrollbars on both the file navigator and canvas panels.
  - Live status bar displaying zoom level and tool state.
- **High-Fidelity Output**:
  - Saves annotations back into a new PDF as native vector graphic shapes (rectangles, ovals, triangles, lines) and PDF text fields with true transparency settings.

---

## Keyboard Shortcuts

The application registers global hotkeys designed to bypass entry forms to prevent typing conflicts:

| Action | Shortcut |
|---|---|
| **Open Folder** | `Ctrl + O` |
| **Save PDF** | `Ctrl + S` |
| **Undo Action** | `Ctrl + Z` |
| **Redo Action** | `Ctrl + Y` |
| **Zoom In** | `Ctrl + +` (or `Ctrl + =`) |
| **Zoom Out** | `Ctrl + -` |
| **Previous Page** | `PageUp` (or `Left Arrow`) |
| **Next Page** | `PageDown` (or `Right Arrow`) |
| **Reset State** | `Escape` |

---

## Installation & Setup

### 1. Requirements
Ensure you have Python 3.8+ installed along with the dependencies listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

*Dependencies include:*
- `pymupdf` (for PDF manipulation)
- `pillow` (for canvas image scaling)

### 2. Launching the App
Run the python script from the root directory:
```bash
python pdf_annotator.py
```
