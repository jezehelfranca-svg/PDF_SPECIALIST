# Atlas PDF Merger

Atlas PDF Merger v2.0.0 is a private, offline-first browser app for combining PDFs into one document with real outline bookmarks.

## Use the app

1. Open `dist/pdf_merger_bookmarks_v2.0.0.html` in a current desktop browser.
2. Drop PDF files into the workspace or choose them from disk.
3. Drag rows, or use the up and down buttons, to set the page order.
4. Edit the bookmark title for each source file if needed.
5. Choose whether to preserve nested source bookmarks and open the bookmark panel.
6. Select **Merge and download**.

No server, account, installation, or network connection is required by the built app. PDF contents stay inside the browser.

## What v2.0.0 includes

- A single portable offline HTML release
- Real indirect PDF outline objects that save correctly
- Unicode bookmark titles, including Korean and other non-Latin text
- One editable top-level bookmark for every source file
- Preservation of internal source outline bookmarks as nested children
- First-page thumbnails, page counts, file sizes, and bookmark counts
- Repeat-safe drag ordering plus keyboard-accessible move buttons
- Clear validation for invalid, empty, and password-protected PDFs
- Responsive desktop and mobile layouts
- No external network requests at runtime

## Limitations

- Password-protected PDFs must be unlocked before merging.
- Source outline items that do not point to an internal page are skipped.
- Some PDF readers ignore the request to open the bookmark panel automatically, but the bookmarks remain in the file.
- Processing is memory-based. Very large inputs may exceed the browser's available memory.

## Development

Requirements: Node.js 22+, npm, Python 3 with `reportlab` and `pypdf`, and Chrome or Edge for the end-to-end test.

```powershell
npm install
npm test
```

Useful commands:

```powershell
npm run dev
npm run build
npm run test:unit
npm run test:e2e
```

The production build is created in `dist/` with a matching SHA-256 checksum.

## Project layout

- `src/main.js` - application UI, PDF inspection, ordering, and merge flow
- `src/pdf/bookmarks.js` - valid indirect outline tree writer
- `src/styles.css` - responsive visual system
- `tests/` - structural and browser tests
- `scripts/` - fixtures, PDF verification, and release packaging
- `dist/` - portable release artifact

See `QA_REPORT.md` for the completed verification results and `THIRD_PARTY_NOTICES.md` for bundled library licenses.
