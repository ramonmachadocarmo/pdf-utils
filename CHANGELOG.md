# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Security
- Cap PDF uploads at 200 MB — `/api/upload` now returns `413` above the limit instead of buffering an unbounded file.
- `annotate`/`rotate`/`convert` no longer echo internal exception text to API responses; failures are logged server-side and return a generic message.

### Added
- Automatic cleanup of job storage (`storage/uploads`, `storage/outputs`) older than 24h, run on app startup.

## [1.0.0] - 2026-08-26

### Added
- Local PDF reader: page-by-page preview with thumbnails, zoom/pan, text search, rotate, night mode, focus view.
- Editing tools: pen, highlight, text, signature, stamp (Approved / Paid / Date), undo, save edits, download.
- Conversion to PNG, JPEG, WEBP, and DOCX.
- UI available in English, Portuguese (BR), and Spanish, with browser language auto-detection.
- Native Windows desktop app (pywebview), standalone `.exe` build (PyInstaller), and Windows installer (Inno Setup).
- In-app update check against GitHub Releases.
