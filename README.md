# PDF Specialist

PDF Specialist is a collection of local-first tools for reviewing, annotating, and combining PDF documents.

## Included tools

| Tool | Best for | Runtime |
|---|---|---|
| [PDF Annotator PRO](#pdf-annotator-pro) | Previewing PDFs and adding vector annotations | Python desktop app |
| [Atlas PDF Merger](./pdf-merger-bookmarks/README.md) | Reordering and merging PDFs with real bookmarks | Standalone browser app |

## Atlas PDF Merger

Atlas PDF Merger v2.0.0 combines PDFs entirely inside the browser. It creates editable Unicode file bookmarks and can preserve existing source outlines as nested bookmarks.

### Quick start

1. Download [`pdf_merger_bookmarks_v2.0.0.html`](./pdf-merger-bookmarks/dist/pdf_merger_bookmarks_v2.0.0.html).
2. Open the HTML file in a current desktop browser.
3. Add PDFs, arrange their order, edit bookmark titles, and select **Merge and download**.

The production app is a single offline HTML file. It requires no server, account, installation, or network connection, and uploaded PDFs never leave the device.

Key features:

- Real PDF outline objects with clickable destinations
- Unicode bookmark titles, including Korean and other non-Latin text
- Preservation of nested source bookmarks
- First-page thumbnails, page totals, file sizes, and bookmark counts
- Drag ordering and accessible move controls
- Responsive desktop and mobile layouts
- Fully offline runtime with no external requests

See the [merger documentation](./pdf-merger-bookmarks/README.md), [QA report](./pdf-merger-bookmarks/QA_REPORT.md), and [third-party notices](./pdf-merger-bookmarks/THIRD_PARTY_NOTICES.md).

## PDF Annotator PRO

PDF Annotator PRO is a Tkinter and PyMuPDF desktop application for high-fidelity PDF preview and annotation.

Features include:

- Pen, highlighter, rectangle, ellipse, triangle, and text-comment tools
- Undo and redo with multi-page annotation state
- Page navigation, direct page lookup, zoom controls, and text search
- Dark interface with custom scrollbars and live tool status
- Native vector PDF output with transparency support

### Installation

Use Python 3.8 or newer:

```bash
pip install -r requirements.txt
python pdf_annotator.py
```

### Keyboard shortcuts

| Action | Shortcut |
|---|---|
| Open folder | `Ctrl + O` |
| Save PDF | `Ctrl + S` |
| Undo | `Ctrl + Z` |
| Redo | `Ctrl + Y` |
| Zoom in | `Ctrl + +` or `Ctrl + =` |
| Zoom out | `Ctrl + -` |
| Previous page | `PageUp` or `Left Arrow` |
| Next page | `PageDown` or `Right Arrow` |
| Reset state | `Escape` |

## Repository structure

```text
PDF_SPECIALIST/
|- pdf_annotator.py
|- requirements.txt
|- pdf-merger-bookmarks/
|  |- dist/
|  |- src/
|  |- scripts/
|  |- tests/
|  `- README.md
`- README.md
```

Both applications process PDF data locally. Atlas PDF Merger is browser-based, while PDF Annotator PRO is a Python desktop application.
