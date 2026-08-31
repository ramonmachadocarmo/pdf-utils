# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [1.1.0] - 2026-08-31

### Added
- XML reader: upload an `.xml` file directly and view it as a formatted, paginated PDF (tag tree with attributes and text), same viewer/edit/export pipeline as PDFs.
- PDF merging: combine multiple uploaded PDFs into a single output file.
- Automatic cleanup of job storage (`storage/uploads`, `storage/outputs`) older than 24h, run on app startup.

### Fixed
- XML reader no longer hangs converting documents with very large single text nodes (e.g. embedded X.509/CRL data in digitally signed XML like NF-e or diploma files); oversized text is now truncated in the rendered PDF.

### Security
- Cap PDF uploads at 200 MB — `/api/upload` now returns `413` above the limit instead of buffering an unbounded file.
- `annotate`/`rotate`/`convert` no longer echo internal exception text to API responses; failures are logged server-side and return a generic message.
- XML parsing uses `defusedxml` to guard against XXE and entity-expansion attacks.

## [1.0.0] - 2026-08-26

### Added
- Local PDF reader: page-by-page preview with thumbnails, zoom/pan, text search, rotate, night mode, focus view.
- Editing tools: pen, highlight, text, signature, stamp (Approved / Paid / Date), undo, save edits, download.
- Conversion to PNG, JPEG, WEBP, and DOCX.
- UI available in English, Portuguese (BR), and Spanish, with browser language auto-detection.
- Native Windows desktop app (pywebview), standalone `.exe` build (PyInstaller), and Windows installer (Inno Setup).
- In-app update check against GitHub Releases.
