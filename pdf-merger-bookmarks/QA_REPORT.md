# Atlas PDF Merger v2.0.0 QA report

Verification completed on 2026-07-14.

## Result

PASS

## Automated checks

- Bookmark unit tests: 2 passed, 0 failed.
- Nested outlines save without recursive object errors.
- Catalog `Outlines`, `First`, `Last`, `Parent`, `Prev`, and `Next` relationships use indirect references.
- Unicode titles round-trip as PDF hexadecimal text strings.
- Empty outline input remains a clean no-op.
- Browser test completed with zero runtime console errors.
- Browser test completed with zero external network requests.
- Repeated reordering produced the requested Beta, Alpha output order.
- Mobile viewport check found no horizontal overflow.
- Dependency audit reported 0 vulnerabilities after updating to Vite 7.3.6.

## Merged PDF checks

The end-to-end test merged a two-page Unicode Beta source and a one-page Alpha source.

- Output page count: 3
- Output order: Beta page 1, Beta page 2, Alpha page 1
- Top-level bookmark order: Unicode Beta, Alpha
- Nested Beta outline: preserved
- Nested destination pages: 1 and 2
- PDF version: 1.7
- Page size: A4
- Encryption: none
- JavaScript: none
- PDF parser result: valid

## Visual checks

- Desktop app layout: pass
- Mobile app layout: pass
- First-page thumbnails: pass
- Bookmark title fields: pass
- Export controls and status messaging: pass
- Rendered merged pages: pass
- Clipped or overlapping PDF content: none observed

## Release

- File: `dist/pdf_merger_bookmarks_v2.0.0.html`
- Format: standalone offline HTML
- SHA-256: see `dist/pdf_merger_bookmarks_v2.0.0.html.sha256`
